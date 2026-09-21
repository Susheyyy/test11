"""
Layer 3 — Reward Simulator

For each eligible card, simulates the estimated annual monetary value
a user would receive based on their actual spending.

Handles both:
  - cashback_rates  (direct % back as cash/statement credit)
  - reward_points_rate + point_value  (points-based rewards)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict

from app.models.card import Card
from app.services.spending_analyzer import SpendingAnalysis, CATEGORY_LABELS
import json


@dataclass
class RewardSimulation:
    card_id: str
    annual_rewards: float          # INR value of all rewards earned
    welcome_bonus_value: float     # one-time bonus (INR)
    annual_fee: float
    net_annual_benefit: float      # annual_rewards + welcome_bonus - annual_fee
    category_breakdown: Dict[str, float]  # INR earned per category/year
    effective_cashback_pct: float  # net_benefit / annual_spend * 100


def simulate_rewards(card: Card, analysis: SpendingAnalysis) -> RewardSimulation:
    """
    Simulates annual reward value for a single card given the user's spending.
    """
    cashback_rates: Dict[str, float] = json.loads(card.cashback_rates or "{}")
    points_rate: Dict[str, float] = json.loads(card.reward_points_rate or "{}")
    point_value: float = card.point_value or 0.0

    category_breakdown: Dict[str, float] = {}
    total_annual_rewards: float = 0.0

    for category, monthly_spend in analysis.raw.items():
        annual_spend = monthly_spend * 12
        reward_inr = 0.0

        # Cashback (direct %)
        if category in cashback_rates and cashback_rates[category] > 0:
            reward_inr = annual_spend * cashback_rates[category]

        # Points-based (points per ₹100 × point_value)
        elif category in points_rate and points_rate[category] > 0:
            points_earned = (annual_spend / 100) * points_rate[category]
            reward_inr = points_earned * point_value

        category_breakdown[category] = round(reward_inr, 2)
        total_annual_rewards += reward_inr

    welcome_bonus = card.welcome_bonus_value or 0.0
    annual_fee = card.annual_fee or 0.0
    net_benefit = total_annual_rewards + welcome_bonus - annual_fee

    effective_pct = (
        (net_benefit / analysis.total_annual * 100)
        if analysis.total_annual > 0
        else 0.0
    )

    return RewardSimulation(
        card_id=card.id,
        annual_rewards=round(total_annual_rewards, 2),
        welcome_bonus_value=welcome_bonus,
        annual_fee=annual_fee,
        net_annual_benefit=round(net_benefit, 2),
        category_breakdown=category_breakdown,
        effective_cashback_pct=round(effective_pct, 2),
    )


def top_earning_categories(sim: RewardSimulation, n: int = 3) -> list[tuple[str, float]]:
    """Returns top-n categories by INR earned (for explainability)."""
    sorted_cats = sorted(
        sim.category_breakdown.items(), key=lambda x: x[1], reverse=True
    )
    return [(cat, val) for cat, val in sorted_cats if val > 0][:n]
