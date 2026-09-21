from __future__ import annotations
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class CardOut(BaseModel):
    id: str
    name: str
    issuer: str
    network: str
    annual_fee: float
    joining_fee: float
    annual_fee_waiver_spend: float
    min_credit_score: int
    min_monthly_income: float
    cashback_rates: Dict[str, float]
    reward_points_rate: Dict[str, float]
    point_value: float
    welcome_bonus_value: float
    welcome_bonus_description: str
    perks: List[str]
    card_type_tags: List[str]
    fuel_surcharge_waiver: bool
    interest_rate_monthly: float

    model_config = {"from_attributes": True}
