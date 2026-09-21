import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.card import Card
from app.schemas.card_schema import CardOut
from app.utils.helpers import parse_json_field

router = APIRouter(prefix="/cards", tags=["Cards"])


def _serialize_card(card: Card) -> CardOut:
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
        cashback_rates=parse_json_field(card.cashback_rates, {}),
        reward_points_rate=parse_json_field(card.reward_points_rate, {}),
        point_value=card.point_value,
        welcome_bonus_value=card.welcome_bonus_value,
        welcome_bonus_description=card.welcome_bonus_description,
        perks=parse_json_field(card.perks, []),
        card_type_tags=[t.strip() for t in (card.card_type_tags or "").split(",") if t.strip()],
        fuel_surcharge_waiver=card.fuel_surcharge_waiver,
        interest_rate_monthly=card.interest_rate_monthly,
    )


@router.get("", response_model=List[CardOut])
async def list_cards(
    issuer: Optional[str] = Query(None, description="Filter by issuer name"),
    max_annual_fee: Optional[float] = Query(None, description="Maximum annual fee (INR)"),
    min_credit_score: Optional[int] = Query(None, description="Filter cards you qualify for"),
    card_type: Optional[str] = Query(None, description="Filter by tag e.g. cashback, travel, fuel"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all active cards with optional filters.
    No authentication required — cards are public data.
    """
    stmt = select(Card).where(Card.is_active == True)

    result = await db.execute(stmt)
    cards = result.scalars().all()

    # In-memory filters (catalog is small ~17 cards)
    if issuer:
        cards = [c for c in cards if issuer.lower() in c.issuer.lower()]
    if max_annual_fee is not None:
        cards = [c for c in cards if c.annual_fee <= max_annual_fee]
    if min_credit_score is not None:
        cards = [c for c in cards if c.min_credit_score <= min_credit_score]
    if card_type:
        cards = [
            c for c in cards
            if card_type.lower() in (c.card_type_tags or "").lower()
        ]

    return [_serialize_card(c) for c in cards]


@router.get("/{card_id}", response_model=CardOut)
async def get_card(card_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Card).where(Card.id == card_id, Card.is_active == True))
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found.")
    return _serialize_card(card)
