import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User, UserProfile, SpendingProfile, UserGoal
from app.schemas.user_schema import (
    UserOut,
    UserProfileUpdate,
    UserProfileOut,
    SpendingProfileCreate,
    SpendingProfileOut,
    GoalsUpdate,
    GoalsOut,
    GoalType,
)
from app.utils.helpers import get_current_user

router = APIRouter(prefix="/users", tags=["Users"])


# ── Profile ───────────────────────────────────────────────────────────────────

@router.get("/profile", response_model=UserProfileOut)
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not set up yet.")
    # Deserialize existing_cards JSON
    if profile.existing_cards:
        profile.existing_cards = json.loads(profile.existing_cards)
    return profile


@router.put("/profile", response_model=UserProfileOut)
async def upsert_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserProfile).where(UserProfile.user_id == current_user.id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    data = payload.model_dump(exclude_unset=True)
    if "existing_cards" in data and data["existing_cards"] is not None:
        data["existing_cards"] = json.dumps(data["existing_cards"])

    for field, value in data.items():
        setattr(profile, field, value)

    await db.flush()

    # Return deserialized
    if profile.existing_cards:
        profile.existing_cards = json.loads(profile.existing_cards)
    return profile


# ── Spending ──────────────────────────────────────────────────────────────────

@router.get("/spending", response_model=SpendingProfileOut)
async def get_spending(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SpendingProfile)
        .where(SpendingProfile.user_id == current_user.id)
        .order_by(SpendingProfile.updated_at.desc())
    )
    sp = result.scalars().first()
    if not sp:
        raise HTTPException(status_code=404, detail="No spending profile found.")
    return sp


@router.post("/spending", response_model=SpendingProfileOut, status_code=201)
async def upsert_spending(
    payload: SpendingProfileCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Replace most recent record (one active profile per user)
    result = await db.execute(
        select(SpendingProfile)
        .where(SpendingProfile.user_id == current_user.id)
        .order_by(SpendingProfile.updated_at.desc())
    )
    sp = result.scalars().first()

    if sp:
        for field, value in payload.model_dump().items():
            setattr(sp, field, value)
    else:
        sp = SpendingProfile(user_id=current_user.id, **payload.model_dump())
        db.add(sp)

    await db.flush()
    return sp


# ── Goals ─────────────────────────────────────────────────────────────────────

@router.get("/goals", response_model=GoalsOut)
async def get_goals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserGoal).where(UserGoal.user_id == current_user.id)
    )
    goal_obj = result.scalar_one_or_none()
    if not goal_obj or not goal_obj.goals:
        return GoalsOut(goals=[])
    return GoalsOut(goals=[GoalType(g) for g in goal_obj.goals.split(",") if g])


@router.put("/goals", response_model=GoalsOut)
async def upsert_goals(
    payload: GoalsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(UserGoal).where(UserGoal.user_id == current_user.id)
    )
    goal_obj = result.scalar_one_or_none()

    goals_str = ",".join([g.value for g in payload.goals])
    if goal_obj:
        goal_obj.goals = goals_str
    else:
        goal_obj = UserGoal(user_id=current_user.id, goals=goals_str)
        db.add(goal_obj)

    await db.flush()
    return GoalsOut(goals=payload.goals)
