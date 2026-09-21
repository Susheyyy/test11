"""
Layer 5 — Recommendation Service (Orchestrator)

Runs all 5 layers in sequence and produces the final ranked list
with full explainability.

Pipeline:
  1. Eligibility Filter  → eligible cards + rejected list
  2. Spending Analyzer   → normalized spend breakdown
  3. Reward Simulator    → annual reward estimates per card
  4. Goal Matcher        → weight vector + goal-match scores
  5. Composite Scoring   → ranked list with score breakdown
  6. Explainability      → human-readable reasons per card
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.models.card import Card
from app.schemas.card_schema import CardOut
from app.schemas.recommendation_schema import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendedCard,
    RejectedCard,
    ScoreBreakdown,
)
from app.services.eligibility_filter import EligibilityContext, filter_eligible
from app.services.goal_matcher import compute_weights, score_goal_match, GOAL_CARD_TAGS
from app.services.reward_simulator import simulate_rewards, top_earning_categories
from app.services.spending_analyzer import (
    SpendingAnalysis,
    analyze_spending,
    spending_summary_text,
    CATEGORY_LABELS,
)


# ── Scoring helpers ───────────────────────────────────────────────────────────

def _normalize(values: List[float]) -> List[float]:
    """Min-max normalize a list of floats to [0, 1]."""
    mn, mx = min(values), max(values)
    if mx == mn:
        return [0.5] * len(values)
    return [(v - mn) / (mx - mn) for v in values]


def _spending_match_score(card: Card, analysis: SpendingAnalysis) -> float:
    """
    How well does the card's reward categories align with the user's
    top spending categories?

    Score = weighted sum of (category_pct × has_reward_for_category)
    """
    cashback_rates: Dict[str, float] = json.loads(card.cashback_rates or "{}")
    points_rate: Dict[str, float] = json.loads(card.reward_points_rate or "{}")

    score = 0.0
    for category, pct in analysis.percentages.items():
        has_reward = (
            cashback_rates.get(category, 0) > 0
            or points_rate.get(category, 0) > 0
        )
        score += pct * (1.0 if has_reward else 0.0)

    return min(1.0, score)


def _eligibility_score(card: Card, ctx: EligibilityContext) -> float:
    """
    Soft score (0–1) measuring how comfortably the user meets eligibility.
    1.0 = far exceeds requirements, 0.5 = just meets, still eligible.
    """
    scores = []

    if ctx.credit_score and card.min_credit_score > 0:
        # Ratio above minimum (capped at 2x = 1.0)
        ratio = ctx.credit_score / card.min_credit_score
        scores.append(min(1.0, (ratio - 1.0) * 2 + 0.5))

    if ctx.monthly_income and card.min_monthly_income > 0:
        ratio = ctx.monthly_income / card.min_monthly_income
        scores.append(min(1.0, (ratio - 1.0) * 0.5 + 0.5))

    return sum(scores) / len(scores) if scores else 0.7


def _fee_affordability_score(card: Card, monthly_income: float) -> float:
    """
    Annual fee as % of annual income. Lower % → higher score.
    0% = 1.0, 1% = ~0.7, 5%+ = ~0.0
    """
    if monthly_income <= 0:
        return 0.5
    annual_income = monthly_income * 12
    fee_pct = card.annual_fee / annual_income
    # Sigmoid-like decay: score = 1 - min(1, fee_pct * 20)
    return max(0.0, 1.0 - min(1.0, fee_pct * 20))


# ── Explainability ─────────────────────────────────────────────────────────────

def _build_positive_reasons(
    card: Card,
    analysis: SpendingAnalysis,
    goals: List[str],
    sim,
    spend_score: float,
    goal_score: float,
) -> List[str]:
    reasons: List[str] = []

    cashback_rates: Dict[str, float] = json.loads(card.cashback_rates or "{}")
    points_rate: Dict[str, float] = json.loads(card.reward_points_rate or "{}")

    # Top reward category alignment
    top_cat_rewards = top_earning_categories(sim, n=3)
    for cat, inr in top_cat_rewards:
        if inr >= 500:
            label = CATEGORY_LABELS.get(cat, cat)
            rate_info = ""
            if cat in cashback_rates and cashback_rates[cat] > 0:
                rate_info = f" ({cashback_rates[cat]*100:.1f}% cashback)"
            elif cat in points_rate and points_rate[cat] > 0:
                pts = points_rate[cat]
                rate_info = f" ({pts:.0f} pts per ₹100)"
            reasons.append(
                f"Earns strong rewards on {label}{rate_info} — "
                f"your highest-value category"
            )
            break  # Only surface the single most impactful one

    # Net benefit
    if sim.net_annual_benefit > 0:
        reasons.append(
            f"Estimated net annual benefit: ₹{sim.net_annual_benefit:,.0f} "
            f"(rewards ₹{sim.annual_rewards:,.0f} + "
            f"welcome bonus ₹{sim.welcome_bonus_value:,.0f} − "
            f"annual fee ₹{sim.annual_fee:,.0f})"
        )

    # Goal alignment
    card_tags = [t.strip() for t in card.card_type_tags.split(",") if t.strip()]
    matched_goals = []
    for goal in goals:
        relevant_tags = GOAL_CARD_TAGS.get(goal, [])
        if any(tag in card_tags for tag in relevant_tags):
            matched_goals.append(goal.replace("_", " ").title())
    if matched_goals:
        reasons.append(f"Aligns with your goal(s): {', '.join(matched_goals)}")

    # Annual fee waiver possibility
    if card.annual_fee_waiver_spend > 0:
        waiver_monthly = card.annual_fee_waiver_spend / 12
        if analysis.total_monthly >= waiver_monthly * 0.8:
            reasons.append(
                f"Annual fee (₹{card.annual_fee:,.0f}) may be waived — "
                f"you're on track with the ₹{card.annual_fee_waiver_spend:,.0f} spend threshold"
            )
    elif card.annual_fee == 0:
        reasons.append("Lifetime free card — no annual fee ever")

    # Fuel surcharge waiver
    if card.fuel_surcharge_waiver and analysis.raw.get("fuel", 0) > 500:
        reasons.append("Fuel surcharge waiver applicable on your fuel spends")

    # Welcome bonus highlight
    if card.welcome_bonus_value >= 1000:
        reasons.append(
            f"Attractive welcome bonus worth ₹{card.welcome_bonus_value:,.0f}: "
            f"{card.welcome_bonus_description}"
        )

    return reasons[:6]  # Cap to 6 reasons


def _build_caveats(card: Card, ctx: EligibilityContext, sim) -> List[str]:
    caveats: List[str] = []

    if card.annual_fee > 0 and card.annual_fee_waiver_spend == 0:
        caveats.append(f"Annual fee of ₹{card.annual_fee:,.0f} with no waiver option")

    if sim.net_annual_benefit < 0:
        caveats.append(
            f"Annual fee (₹{card.annual_fee:,.0f}) may exceed estimated rewards "
            f"(₹{sim.annual_rewards:,.0f}) based on your current spending"
        )

    if ctx.credit_score and card.min_credit_score > 0:
        gap = card.min_credit_score - ctx.credit_score
        if 0 < gap <= 30:
            caveats.append(
                f"Your credit score ({ctx.credit_score}) is close to but above the "
                f"minimum ({card.min_credit_score}) — approval not guaranteed"
            )

    if card.network == "Amex":
        caveats.append("Amex acceptance is limited at some merchants in India")

    return caveats


# ── Card → CardOut serializer (deserializes JSON fields) ──────────────────────

def _card_to_out(card: Card) -> CardOut:
    return CardOut(
        id=card.id,
        name=card.name,
        issuer=card.issuer,
        network=card.network,
        annual_fee=card.annual_fee,
        joining_fee=card.joining_fee,
        annual_fee_waiver_spend=card.annual_fee_waiver_spend,
        min_credit_score=card.min_credit_score,
        min_monthly_income=card.min_monthly_income,
        cashback_rates=json.loads(card.cashback_rates or "{}"),
        reward_points_rate=json.loads(card.reward_points_rate or "{}"),
        point_value=card.point_value,
        welcome_bonus_value=card.welcome_bonus_value,
        welcome_bonus_description=card.welcome_bonus_description,
        perks=json.loads(card.perks or "[]"),
        card_type_tags=[t.strip() for t in card.card_type_tags.split(",") if t.strip()],
        fuel_surcharge_waiver=card.fuel_surcharge_waiver,
        interest_rate_monthly=card.interest_rate_monthly,
    )


# ── Main orchestrator ──────────────────────────────────────────────────────────

def run_recommendation(
    req: RecommendationRequest,
    all_cards: List[Card],
) -> RecommendationResponse:
    """
    Full recommendation pipeline.

    Args:
        req:       Validated RecommendationRequest from the API
        all_cards: Active cards loaded from DB (seeded from card_catalog.json)

    Returns:
        RecommendationResponse with ranked cards + explainability
    """
    goals = [g.value for g in req.goals]
    spend_dict = req.spending.model_dump()

    # ── Layer 1: Eligibility ──────────────────────────────────────────────────
    ctx = EligibilityContext(
        credit_score=req.credit_score or 0,
        monthly_income=req.monthly_income or 0,
        age=req.age or 25,
        employment_type=req.employment_type or "salaried",
        max_annual_fee=req.max_annual_fee,
    )
    eligible_cards, rejected_entries = filter_eligible(all_cards, ctx)

    # ── Layer 2: Spending Analysis ────────────────────────────────────────────
    analysis: SpendingAnalysis = analyze_spending(spend_dict)

    # ── Layer 3: Reward Simulation ────────────────────────────────────────────
    simulations = {card.id: simulate_rewards(card, analysis) for card in eligible_cards}

    # ── Layer 4: Goal Weights ─────────────────────────────────────────────────
    weights = compute_weights(goals)

    # ── Layer 5: Composite Scoring ────────────────────────────────────────────
    scored: List[Tuple[Card, float, Dict]] = []

    # Collect raw reward values for normalization
    raw_reward_values = [simulations[c.id].net_annual_benefit for c in eligible_cards]

    if raw_reward_values:
        norm_rewards = _normalize(raw_reward_values)
    else:
        norm_rewards = []

    for idx, card in enumerate(eligible_cards):
        sim = simulations[card.id]
        card_tags = [t.strip() for t in card.card_type_tags.split(",") if t.strip()]

        s_spend = _spending_match_score(card, analysis)
        s_goal = score_goal_match(card_tags, goals)
        s_reward = norm_rewards[idx] if norm_rewards else 0.5
        s_elig = _eligibility_score(card, ctx)
        s_fee = _fee_affordability_score(card, ctx.monthly_income)

        final = (
            weights.spending_match * s_spend
            + weights.goal_match * s_goal
            + weights.reward_value * s_reward
            + weights.eligibility * s_elig
            + weights.fee_affordability * s_fee
        )

        scored.append((
            card,
            final,
            {
                "spending_match": round(s_spend, 4),
                "goal_match": round(s_goal, 4),
                "reward_value": round(s_reward, 4),
                "eligibility": round(s_elig, 4),
                "fee_affordability": round(s_fee, 4),
                "final": round(final, 4),
            },
        ))

    # Sort descending by final score
    scored.sort(key=lambda x: x[1], reverse=True)
    top_scored = scored[: req.top_n]

    # ── Build response ────────────────────────────────────────────────────────
    recommendations: List[RecommendedCard] = []
    for rank, (card, final_score, breakdown) in enumerate(top_scored, start=1):
        sim = simulations[card.id]

        positive_reasons = _build_positive_reasons(
            card, analysis, goals, sim,
            breakdown["spending_match"],
            breakdown["goal_match"],
        )
        caveats = _build_caveats(card, ctx, sim)

        recommendations.append(
            RecommendedCard(
                rank=rank,
                card=_card_to_out(card),
                score_breakdown=ScoreBreakdown(**breakdown),
                estimated_annual_rewards=sim.annual_rewards,
                net_annual_benefit=sim.net_annual_benefit,
                positive_reasons=positive_reasons,
                caveats=caveats,
            )
        )

    # Rejected cards for the "why not?" panel
    rejected_out: List[RejectedCard] = [
        RejectedCard(
            card_name=r.card.name,
            issuer=r.card.issuer,
            rejection_reasons=r.reasons,
        )
        for r in rejected_entries
    ]

    user_summary: Dict[str, Any] = {
        "credit_score": req.credit_score,
        "monthly_income": req.monthly_income,
        "total_monthly_spend": analysis.total_monthly,
        "total_annual_spend": analysis.total_annual,
        "top_spend_categories": [
            {"category": CATEGORY_LABELS.get(c, c), "percentage": round(p * 100, 1)}
            for c, p in analysis.top_categories
        ],
        "goals": goals,
        "spending_summary": spending_summary_text(analysis),
    }

    return RecommendationResponse(
        generated_at=datetime.now(timezone.utc),
        user_summary=user_summary,
        recommendations=recommendations,
        rejected_cards=rejected_out,
    )
