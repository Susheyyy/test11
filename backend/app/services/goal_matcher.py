"""
Layer 4 — Goal Matcher

Maps user financial goals to scoring weight vectors.
Each goal shifts the emphasis of the final composite score.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class WeightVector:
    """
    Weights must sum to 1.0.
    Components:
        spending_match  — how well the card's reward categories align with user's top spends
        goal_match      — how well the card's tags/perks match the user's stated goals
        reward_value    — estimated net annual benefit (normalized)
        eligibility     — how comfortably the user clears the eligibility bar
        fee_affordability — inverse penalty for high annual fee relative to income
    """
    spending_match: float = 0.30
    goal_match: float = 0.20
    reward_value: float = 0.25
    eligibility: float = 0.15
    fee_affordability: float = 0.10


# Goal → weight adjustments (deltas from default)
# Positive = increase that dimension's weight, negative = decrease
_GOAL_WEIGHT_ADJUSTMENTS: Dict[str, Dict[str, float]] = {
    "cashback": {
        "reward_value": +0.10,
        "fee_affordability": +0.05,
        "goal_match": +0.05,
        "spending_match": -0.10,
        "eligibility": -0.10,
    },
    "travel": {
        "goal_match": +0.15,
        "spending_match": +0.05,
        "reward_value": +0.05,
        "eligibility": -0.15,
        "fee_affordability": -0.10,
    },
    "airline_miles": {
        "goal_match": +0.20,
        "reward_value": +0.05,
        "eligibility": -0.15,
        "fee_affordability": -0.10,
        "spending_match": 0.0,
    },
    "hotel_rewards": {
        "goal_match": +0.15,
        "reward_value": +0.05,
        "eligibility": -0.10,
        "fee_affordability": -0.10,
        "spending_match": 0.0,
    },
    "fuel_savings": {
        "spending_match": +0.15,
        "reward_value": +0.10,
        "goal_match": 0.0,
        "eligibility": -0.15,
        "fee_affordability": -0.10,
    },
    "dining_benefits": {
        "spending_match": +0.15,
        "reward_value": +0.05,
        "goal_match": +0.05,
        "eligibility": -0.15,
        "fee_affordability": -0.10,
    },
    "shopping_rewards": {
        "spending_match": +0.15,
        "reward_value": +0.05,
        "goal_match": +0.05,
        "eligibility": -0.15,
        "fee_affordability": -0.10,
    },
    "building_credit": {
        "eligibility": +0.20,
        "fee_affordability": +0.15,
        "reward_value": -0.15,
        "goal_match": +0.05,
        "spending_match": -0.25,
    },
    "low_annual_fee": {
        "fee_affordability": +0.20,
        "eligibility": +0.10,
        "reward_value": -0.10,
        "goal_match": 0.0,
        "spending_match": -0.20,
    },
    "premium_luxury": {
        "goal_match": +0.25,
        "eligibility": -0.15,
        "reward_value": +0.05,
        "fee_affordability": -0.20,
        "spending_match": +0.05,
    },
    "balance_transfer": {
        "fee_affordability": +0.20,
        "eligibility": +0.15,
        "reward_value": -0.20,
        "goal_match": +0.05,
        "spending_match": -0.20,
    },
    "emi_benefits": {
        "fee_affordability": +0.15,
        "eligibility": +0.10,
        "goal_match": +0.10,
        "reward_value": -0.15,
        "spending_match": -0.20,
    },
}

# Tags used for goal_match scoring — which card tags signal alignment with a goal
GOAL_CARD_TAGS: Dict[str, List[str]] = {
    "cashback": ["cashback", "zero_fee"],
    "travel": ["travel", "airline_miles", "premium"],
    "airline_miles": ["airline_miles", "travel", "premium"],
    "hotel_rewards": ["travel", "premium", "luxury"],
    "fuel_savings": ["fuel"],
    "dining_benefits": ["dining"],
    "shopping_rewards": ["shopping", "online"],
    "building_credit": ["building_credit", "zero_fee"],
    "low_annual_fee": ["zero_fee", "building_credit"],
    "premium_luxury": ["premium", "luxury", "travel"],
    "balance_transfer": ["zero_fee"],
    "emi_benefits": ["cashback", "shopping"],
}


def compute_weights(goals: List[str]) -> WeightVector:
    """
    Blends weight adjustments from all user goals and returns a
    normalized WeightVector.
    """
    base = WeightVector()
    wdict = {
        "spending_match": base.spending_match,
        "goal_match": base.goal_match,
        "reward_value": base.reward_value,
        "eligibility": base.eligibility,
        "fee_affordability": base.fee_affordability,
    }

    if not goals:
        return base

    # Average adjustments across all selected goals
    for goal in goals:
        adjustments = _GOAL_WEIGHT_ADJUSTMENTS.get(goal, {})
        for key, delta in adjustments.items():
            wdict[key] += delta / len(goals)

    # Clamp to [0.01, 0.70] then re-normalize to sum = 1.0
    for key in wdict:
        wdict[key] = max(0.01, min(0.70, wdict[key]))

    total = sum(wdict.values())
    wdict = {k: v / total for k, v in wdict.items()}

    return WeightVector(**wdict)


def score_goal_match(card_tags: List[str], goals: List[str]) -> float:
    """
    Returns a 0.0–1.0 score based on how many of the user's goals
    are supported by the card's tags.
    """
    if not goals:
        return 0.5

    matched = 0
    for goal in goals:
        relevant_tags = GOAL_CARD_TAGS.get(goal, [])
        if any(tag in card_tags for tag in relevant_tags):
            matched += 1

    return matched / len(goals)
