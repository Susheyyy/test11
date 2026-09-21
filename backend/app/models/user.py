import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    # Relationships
    profile: Mapped[Optional["UserProfile"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    spending_profiles: Mapped[List["SpendingProfile"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    goals: Mapped[Optional["UserGoal"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"


class UserProfile(Base):
    """Extended financial profile — 1-to-1 with User."""

    __tablename__ = "user_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    age: Mapped[Optional[int]] = mapped_column(Integer)
    monthly_income: Mapped[Optional[float]] = mapped_column(Float)           # INR
    employment_type: Mapped[Optional[str]] = mapped_column(
        Enum("salaried", "self_employed", "student", "retired", "other", name="employment_type_enum"),
    )
    credit_score: Mapped[Optional[int]] = mapped_column(Integer)             # 300–900
    existing_cards: Mapped[Optional[str]] = mapped_column(Text)              # JSON list of card names
    monthly_savings: Mapped[Optional[float]] = mapped_column(Float)
    current_loans_emi: Mapped[Optional[float]] = mapped_column(Float)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    user: Mapped["User"] = relationship(back_populates="profile")


class SpendingProfile(Base):
    """Monthly spending breakdown by category."""

    __tablename__ = "spending_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Monthly spend amounts in INR
    food_dining: Mapped[float] = mapped_column(Float, default=0.0)
    shopping: Mapped[float] = mapped_column(Float, default=0.0)
    travel: Mapped[float] = mapped_column(Float, default=0.0)
    fuel: Mapped[float] = mapped_column(Float, default=0.0)
    groceries: Mapped[float] = mapped_column(Float, default=0.0)
    utilities: Mapped[float] = mapped_column(Float, default=0.0)
    entertainment: Mapped[float] = mapped_column(Float, default=0.0)
    others: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    user: Mapped["User"] = relationship(back_populates="spending_profiles")

    @property
    def total(self) -> float:
        return (
            self.food_dining
            + self.shopping
            + self.travel
            + self.fuel
            + self.groceries
            + self.utilities
            + self.entertainment
            + self.others
        )


class UserGoal(Base):
    """Financial goals — 1-to-1 with User (stored as comma-separated enum values)."""

    __tablename__ = "user_goals"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    goals: Mapped[str] = mapped_column(Text, default="")  # comma-separated goal keys
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    user: Mapped["User"] = relationship(back_populates="goals")
