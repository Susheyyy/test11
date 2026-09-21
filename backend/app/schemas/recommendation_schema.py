from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.schemas.card_schema import CardOut
from app.schemas.user_schema import SpendingProfileCreate, GoalType


# ── Request ───────────────────────────────────────────────────────────────────
class RecommendationRequest(BaseModel):
    """
    All data needed to run a recommendation. Allows a one-shot call
    without requiring the user to pre-save their profile (handy for demos).
    If the user is authenticated their stored profile is merged with this.
    """
    # Financial profile
    monthly_income: Optional[float] = None
    credit_score: Optional[int] = None
    employment_type: Optional[str] = None
    age: Optional[int] = None

    # Spending (monthly INR)
    spending: SpendingProfileCreate

    # Goals
    goals: List[GoalType]

    # Preferences
    max_annual_fee: Optional[float] = None   # hard cap on annual fee
    top_n: int = 5                           # how many cards to return


# ── Per-card result ───────────────────────────────────────────────────────────
class ScoreBreakdown(BaseModel):
    spending_match: float
    goal_match: float
    reward_value: float
    eligibility: float
    fee_affordability: float
    final: float


class RecommendedCard(BaseModel):
    rank: int
    card: CardOut
    score_breakdown: ScoreBreakdown
    estimated_annual_rewards: float    # INR
    net_annual_benefit: float          # INR (rewards + welcome_bonus - annual_fee)
    positive_reasons: List[str]        # why recommended
    caveats: List[str]                 # minor things to watch


class RejectedCard(BaseModel):
    card_name: str
    issuer: str
    rejection_reasons: List[str]       # why it was filtered out


# ── Full response ─────────────────────────────────────────────────────────────
class RecommendationResponse(BaseModel):
    generated_at: datetime
    user_summary: Dict[str, Any]       # echoes key input data for the UI
    recommendations: List[RecommendedCard]
    rejected_cards: List[RejectedCard]  # for the "why not" explainability panel


class RecommendationHistoryItem(BaseModel):
    id: str
    rank: int
    card_name: str
    issuer: str
    final_score: float
    net_annual_benefit: float
    positive_reasons: List[str]
    created_at: datetime

    model_config = {"from_attributes": True}
