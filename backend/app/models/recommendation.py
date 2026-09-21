import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    card_id: Mapped[str] = mapped_column(
        ForeignKey("cards.id", ondelete="CASCADE"), nullable=False
    )

    # Scoring breakdown
    final_score: Mapped[float] = mapped_column(Float, default=0.0)             # 0–1 composite
    spending_match_score: Mapped[float] = mapped_column(Float, default=0.0)
    goal_match_score: Mapped[float] = mapped_column(Float, default=0.0)
    reward_value_score: Mapped[float] = mapped_column(Float, default=0.0)
    eligibility_score: Mapped[float] = mapped_column(Float, default=0.0)
    fee_affordability_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Financial estimates
    estimated_annual_rewards: Mapped[float] = mapped_column(Float, default=0.0)  # INR
    net_annual_benefit: Mapped[float] = mapped_column(Float, default=0.0)        # INR (after fee)

    # Rank in this recommendation run (1 = best)
    rank: Mapped[int] = mapped_column(Integer, default=1)

    # Explainability — stored as JSON lists
    positive_reasons: Mapped[str] = mapped_column(Text, default="[]")   # why recommended
    negative_reasons: Mapped[str] = mapped_column(Text, default="[]")   # caveats / why others skipped

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped["User"] = relationship(back_populates="recommendations")
    card: Mapped["Card"] = relationship(back_populates="recommendations")
