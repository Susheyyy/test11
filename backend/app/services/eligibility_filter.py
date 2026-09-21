"""
Layer 1 — Eligibility Filter

Hard-rules that eliminate cards a user cannot realistically obtain.
Returns (eligible_cards, rejected_cards_with_reasons).
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple

from app.models.card import Card


@dataclass
class EligibilityContext:
    credit_score: int = 0
    monthly_income: float = 0.0
    age: int = 25
    employment_type: str = "salaried"
    max_annual_fee: float | None = None   # user-defined hard cap


@dataclass
class RejectedEntry:
    card: Card
    reasons: List[str] = field(default_factory=list)


def filter_eligible(
    cards: List[Card],
    ctx: EligibilityContext,
) -> Tuple[List[Card], List[RejectedEntry]]:
    """
    Returns:
        eligible   — cards that pass all hard eligibility rules
        rejected   — cards that failed with reasons attached
    """
    eligible: List[Card] = []
    rejected: List[RejectedEntry] = []

    for card in cards:
        reasons: List[str] = []

        # ── Credit score ─────────────────────────────────────────────────────
        if ctx.credit_score and ctx.credit_score < card.min_credit_score:
            reasons.append(
                f"Requires a minimum credit score of {card.min_credit_score} "
                f"(yours: {ctx.credit_score})"
            )

        # ── Income ────────────────────────────────────────────────────────────
        if ctx.monthly_income and ctx.monthly_income < card.min_monthly_income:
            reasons.append(
                f"Requires a minimum monthly income of ₹{card.min_monthly_income:,.0f} "
                f"(yours: ₹{ctx.monthly_income:,.0f})"
            )

        # ── Annual fee cap (user preference as a hard filter) ─────────────────
        if ctx.max_annual_fee is not None and card.annual_fee > ctx.max_annual_fee:
            reasons.append(
                f"Annual fee ₹{card.annual_fee:,.0f} exceeds your maximum of "
                f"₹{ctx.max_annual_fee:,.0f}"
            )

        # ── Student / unemployed income check ─────────────────────────────────
        if ctx.employment_type == "student" and card.min_monthly_income > 20000:
            reasons.append(
                "This card has income requirements that are typically not met by students"
            )

        if reasons:
            rejected.append(RejectedEntry(card=card, reasons=reasons))
        else:
            eligible.append(card)

    return eligible, rejected
