import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Card(Base):
    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuer: Mapped[str] = mapped_column(String(100), nullable=False)
    network: Mapped[str] = mapped_column(String(50), default="Visa")

    annual_fee: Mapped[float] = mapped_column(Float, default=0.0)       
    joining_fee: Mapped[float] = mapped_column(Float, default=0.0)       
    annual_fee_waiver_spend: Mapped[float] = mapped_column(Float, default=0.0)  

    min_credit_score: Mapped[int] = mapped_column(Integer, default=650)
    min_monthly_income: Mapped[float] = mapped_column(Float, default=20000.0)  

    cashback_rates: Mapped[str] = mapped_column(Text, default="{}")       
    reward_points_rate: Mapped[str] = mapped_column(Text, default="{}")    
    point_value: Mapped[float] = mapped_column(Float, default=0.0)          

    welcome_bonus_value: Mapped[float] = mapped_column(Float, default=0.0)
    welcome_bonus_description: Mapped[str] = mapped_column(Text, default="")

    perks: Mapped[str] = mapped_column(Text, default="[]")

    card_type_tags: Mapped[str] = mapped_column(Text, default="")

    interest_rate_monthly: Mapped[float] = mapped_column(Float, default=3.5) 

    fuel_surcharge_waiver: Mapped[bool] = mapped_column(Boolean, default=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    recommendations: Mapped[List["Recommendation"]] = relationship(back_populates="card")

    def __repr__(self) -> str:
        return f"<Card id={self.id} name={self.name} issuer={self.issuer}>"
