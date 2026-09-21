import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db.session import get_db
from app.models.card import Card
from app.models.recommendation import Recommendation
from app.models.user import User, UserProfile, SpendingProfile, UserGoal
from app.schemas.recommendation_schema import (
    RecommendationRequest,
    RecommendationResponse,
    RecommendationHistoryItem,
)
from app.schemas.user_schema import GoalType, SpendingProfileCreate
from app.services.recommendation_service import run_recommendation
from app.utils.helpers import get_current_user, get_optional_current_user

router = APIRouter(prefix="/recommendations", tags=["Recommendations"])


async def _load_all_active_cards(db: AsyncSession) -> List[Card]:
    result = await db.execute(select(Card).where(Card.is_active == True))
    return list(result.scalars().all())


@router.post("", response_model=RecommendationResponse)
async def get_recommendations(
    payload: RecommendationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """
    Run the full recommendation pipeline.

    Merges the request payload with the authenticated user's stored profile
    and spending data (if available). Fields explicitly provided in the request
    take precedence.
    """
    # Merge stored profile if user is authenticated
    if current_user:
        profile_result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == current_user.id)
        )
        profile: UserProfile | None = profile_result.scalar_one_or_none()

        if profile:
            if payload.monthly_income is None and profile.monthly_income:
                payload.monthly_income = profile.monthly_income
            if payload.credit_score is None and profile.credit_score:
                payload.credit_score = profile.credit_score
            if payload.employment_type is None and profile.employment_type:
                payload.employment_type = profile.employment_type
            if payload.age is None and profile.age:
                payload.age = profile.age

        # Merge stored spending (only if request spending is all zeros)
        spend_total = sum(payload.spending.model_dump().values())
        if spend_total == 0:
            sp_result = await db.execute(
                select(SpendingProfile)
                .where(SpendingProfile.user_id == current_user.id)
                .order_by(SpendingProfile.updated_at.desc())
            )
            sp = sp_result.scalars().first()
            if sp:
                payload.spending = SpendingProfileCreate(
                    food_dining=sp.food_dining,
                    shopping=sp.shopping,
                    travel=sp.travel,
                    fuel=sp.fuel,
                    groceries=sp.groceries,
                    utilities=sp.utilities,
                    entertainment=sp.entertainment,
                    others=sp.others,
                )

        # Merge stored goals (only if no goals in request)
        if not payload.goals:
            goal_result = await db.execute(
                select(UserGoal).where(UserGoal.user_id == current_user.id)
            )
            goal_obj = goal_result.scalar_one_or_none()
            if goal_obj and goal_obj.goals:
                payload.goals = [GoalType(g) for g in goal_obj.goals.split(",") if g]

    # Load active cards
    all_cards = await _load_all_active_cards(db)
    if not all_cards:
        raise HTTPException(status_code=503, detail="Card catalog is empty. Please seed the database.")

    # Run engine
    response = run_recommendation(payload, all_cards)

    # Persist results for authenticated users
    if current_user:
        # Clear old recommendations for this user
        old = await db.execute(
            select(Recommendation).where(Recommendation.user_id == current_user.id)
        )
        for old_rec in old.scalars().all():
            await db.delete(old_rec)

        for rec in response.recommendations:
            db_rec = Recommendation(
                user_id=current_user.id,
                card_id=rec.card.id,
                final_score=rec.score_breakdown.final,
                spending_match_score=rec.score_breakdown.spending_match,
                goal_match_score=rec.score_breakdown.goal_match,
                reward_value_score=rec.score_breakdown.reward_value,
                eligibility_score=rec.score_breakdown.eligibility,
                fee_affordability_score=rec.score_breakdown.fee_affordability,
                estimated_annual_rewards=rec.estimated_annual_rewards,
                net_annual_benefit=rec.net_annual_benefit,
                rank=rec.rank,
                positive_reasons=json.dumps(rec.positive_reasons),
                negative_reasons=json.dumps(rec.caveats),
            )
            db.add(db_rec)
        await db.flush()

    return response


@router.get("/history", response_model=List[RecommendationHistoryItem])
async def recommendation_history(
    limit: int = Query(10, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns the last N recommendation results for the authenticated user."""
    result = await db.execute(
        select(Recommendation, Card)
        .join(Card, Recommendation.card_id == Card.id)
        .where(Recommendation.user_id == current_user.id)
        .order_by(desc(Recommendation.created_at), Recommendation.rank)
        .limit(limit)
    )
    rows = result.all()

    history = []
    for rec, card in rows:
        history.append(
            RecommendationHistoryItem(
                id=rec.id,
                rank=rec.rank,
                card_name=card.name,
                issuer=card.issuer,
                final_score=rec.final_score,
                net_annual_benefit=rec.net_annual_benefit,
                positive_reasons=json.loads(rec.positive_reasons or "[]"),
                created_at=rec.created_at,
            )
        )
    return history
