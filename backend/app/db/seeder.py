"""
DB seeder — loads card_catalog.json into the cards table on first run.
Called automatically at app startup.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.card import Card
from app.core.logging import logger

_CATALOG_PATH = Path(__file__).parent.parent.parent / "data" / "card_catalog.json"


async def seed_cards(db: AsyncSession) -> None:
    """Insert cards from card_catalog.json if the cards table is empty."""
    result = await db.execute(select(Card).limit(1))
    if result.scalar_one_or_none():
        logger.info("Card catalog already seeded — skipping.")
        return

    with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    cards_data = data.get("cards", [])
    count = 0

    for entry in cards_data:
        card = Card(
            name=entry["name"],
            issuer=entry["issuer"],
            network=entry.get("network", "Visa"),
            annual_fee=entry.get("annual_fee", 0),
            joining_fee=entry.get("joining_fee", 0),
            annual_fee_waiver_spend=entry.get("annual_fee_waiver_spend", 0),
            min_credit_score=entry.get("min_credit_score", 650),
            min_monthly_income=entry.get("min_monthly_income", 20000),
            cashback_rates=json.dumps(entry.get("cashback_rates", {})),
            reward_points_rate=json.dumps(entry.get("reward_points_rate", {})),
            point_value=entry.get("point_value", 0),
            welcome_bonus_value=entry.get("welcome_bonus_value", 0),
            welcome_bonus_description=entry.get("welcome_bonus_description", ""),
            perks=json.dumps(entry.get("perks", [])),
            card_type_tags=",".join(entry.get("card_type_tags", [])),
            fuel_surcharge_waiver=entry.get("fuel_surcharge_waiver", False),
            interest_rate_monthly=entry.get("interest_rate_monthly", 3.5),
            is_active=True,
        )
        db.add(card)
        count += 1

    await db.commit()
    logger.info(f"Seeded {count} cards into the database.")
