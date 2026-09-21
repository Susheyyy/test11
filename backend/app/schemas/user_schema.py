from __future__ import annotations
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from enum import Enum


class EmploymentType(str, Enum):
    salaried = "salaried"
    self_employed = "self_employed"
    student = "student"
    retired = "retired"
    other = "other"


class GoalType(str, Enum):
    cashback = "cashback"
    travel = "travel"
    airline_miles = "airline_miles"
    hotel_rewards = "hotel_rewards"
    fuel_savings = "fuel_savings"
    dining_benefits = "dining_benefits"
    shopping_rewards = "shopping_rewards"
    building_credit = "building_credit"
    low_annual_fee = "low_annual_fee"
    premium_luxury = "premium_luxury"
    balance_transfer = "balance_transfer"
    emi_benefits = "emi_benefits"


# ── Register / Login ──────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=1)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ── User profile ──────────────────────────────────────────────────────────────
class UserProfileUpdate(BaseModel):
    age: Optional[int] = Field(None, ge=18, le=100)
    monthly_income: Optional[float] = Field(None, ge=0)
    employment_type: Optional[EmploymentType] = None
    credit_score: Optional[int] = Field(None, ge=300, le=900)
    existing_cards: Optional[List[str]] = None
    monthly_savings: Optional[float] = Field(None, ge=0)
    current_loans_emi: Optional[float] = Field(None, ge=0)


class UserProfileOut(BaseModel):
    age: Optional[int] = None
    monthly_income: Optional[float] = None
    employment_type: Optional[EmploymentType] = None
    credit_score: Optional[int] = None
    existing_cards: Optional[List[str]] = None
    monthly_savings: Optional[float] = None
    current_loans_emi: Optional[float] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    is_active: bool
    created_at: datetime
    profile: Optional[UserProfileOut] = None

    model_config = {"from_attributes": True}


# ── Spending ──────────────────────────────────────────────────────────────────
class SpendingProfileCreate(BaseModel):
    food_dining: float = Field(0.0, ge=0)
    shopping: float = Field(0.0, ge=0)
    travel: float = Field(0.0, ge=0)
    fuel: float = Field(0.0, ge=0)
    groceries: float = Field(0.0, ge=0)
    utilities: float = Field(0.0, ge=0)
    entertainment: float = Field(0.0, ge=0)
    others: float = Field(0.0, ge=0)


class SpendingProfileOut(SpendingProfileCreate):
    id: str
    user_id: str
    total: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Goals ─────────────────────────────────────────────────────────────────────
class GoalsUpdate(BaseModel):
    goals: List[GoalType]


class GoalsOut(BaseModel):
    goals: List[GoalType]

    model_config = {"from_attributes": True}
