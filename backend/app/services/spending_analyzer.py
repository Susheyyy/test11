"""
Layer 2 — Spending Analyzer

Converts raw monthly spend amounts into a normalized percentage breakdown
and identifies the user's dominant spend categories.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple

SPEND_CATEGORIES: List[str] = [
    "food_dining",
    "shopping",
    "travel",
    "fuel",
    "groceries",
    "utilities",
    "entertainment",
    "others",
]

# Human-readable labels for explainability output
CATEGORY_LABELS: Dict[str, str] = {
    "food_dining": "Food & Dining",
    "shopping": "Shopping",
    "travel": "Travel",
    "fuel": "Fuel",
    "groceries": "Groceries",
    "utilities": "Utilities",
    "entertainment": "Entertainment",
    "others": "Other spends",
}


@dataclass
class SpendingAnalysis:
    raw: Dict[str, float]           # monthly INR per category
    percentages: Dict[str, float]   # 0.0–1.0 per category
    total_monthly: float
    total_annual: float
    top_categories: List[Tuple[str, float]]  # sorted (category, pct) top-3


def analyze_spending(spend: Dict[str, float]) -> SpendingAnalysis:
    """
    Args:
        spend: dict of {category: monthly_amount_inr}
    Returns:
        SpendingAnalysis with percentages and top categories
    """
    # Ensure all categories present, default to 0
    raw = {cat: float(spend.get(cat, 0.0)) for cat in SPEND_CATEGORIES}
    total = sum(raw.values())

    if total == 0:
        pcts = {cat: 0.0 for cat in SPEND_CATEGORIES}
    else:
        pcts = {cat: raw[cat] / total for cat in SPEND_CATEGORIES}

    # Top 3 non-zero categories
    top = sorted(
        [(cat, pct) for cat, pct in pcts.items() if pct > 0],
        key=lambda x: x[1],
        reverse=True,
    )[:3]

    return SpendingAnalysis(
        raw=raw,
        percentages=pcts,
        total_monthly=total,
        total_annual=total * 12,
        top_categories=top,
    )


def spending_summary_text(analysis: SpendingAnalysis) -> str:
    """Returns a human-readable summary for explainability."""
    if not analysis.top_categories:
        return "No spending data provided."
    parts = [
        f"{CATEGORY_LABELS[cat]} ({pct * 100:.0f}%)"
        for cat, pct in analysis.top_categories
    ]
    return "Your top spending categories are: " + ", ".join(parts) + "."
