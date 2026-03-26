"""SQLAlchemy ORM models for the hotel price monitor."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""


# ── Enums ──────────────────────────────────────────────────────────────────


class BreakfastOption(str, enum.Enum):
    YES = "YES"
    NO = "NO"
    ANY = "ANY"


class PaymentType(str, enum.Enum):
    ONLINE = "ONLINE"
    ON_SITE = "ON_SITE"
    ANY = "ANY"


class ProviderName(str, enum.Enum):
    TRIP = "TRIP"
    TINKOFF = "TINKOFF"
    OTELLO = "OTELLO"
    OSTROVOK = "OSTROVOK"
    OTHER = "OTHER"


# ── Models ─────────────────────────────────────────────────────────────────


class HotelWatch(Base):
    """A hotel booking that the user wants to monitor."""

    __tablename__ = "hotel_watches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    city: Mapped[str] = mapped_column(String(255), nullable=False)
    hotel_name: Mapped[str] = mapped_column(String(255), nullable=False)
    checkin_date: Mapped[date] = mapped_column(nullable=False)
    checkout_date: Mapped[date] = mapped_column(nullable=False)
    guests_count: Mapped[int] = mapped_column(Integer, default=1)
    rooms_count: Mapped[int] = mapped_column(Integer, default=1)

    # Conditions
    free_cancellation: Mapped[bool] = mapped_column(Boolean, default=False)
    breakfast_included: Mapped[BreakfastOption] = mapped_column(
        Enum(BreakfastOption), default=BreakfastOption.ANY
    )
    payment_type: Mapped[PaymentType] = mapped_column(
        Enum(PaymentType), default=PaymentType.ANY
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    # Relationships
    baseline: Mapped[BookingBaseline | None] = relationship(
        "BookingBaseline", back_populates="hotel_watch", uselist=False, lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<HotelWatch(id={self.id}, hotel={self.hotel_name}, "
            f"city={self.city}, {self.checkin_date}..{self.checkout_date})>"
        )


class BookingBaseline(Base):
    """The user's current booking (baseline for price comparison)."""

    __tablename__ = "booking_baselines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hotel_watch_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("hotel_watches.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    provider: Mapped[ProviderName] = mapped_column(Enum(ProviderName), nullable=False)
    price_rub: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="RUB")
    exchange_rate: Mapped[float] = mapped_column(Float, default=1.0)
    cashback_percent: Mapped[float] = mapped_column(Float, default=0.0)
    cashback_rub: Mapped[float] = mapped_column(Float, default=0.0)
    effective_price_rub: Mapped[float] = mapped_column(Float, nullable=False)

    # Relationships
    hotel_watch: Mapped[HotelWatch] = relationship(
        "HotelWatch", back_populates="baseline", lazy="selectin"
    )

    def __repr__(self) -> str:
        return (
            f"<BookingBaseline(id={self.id}, provider={self.provider}, "
            f"price={self.price_rub}, effective={self.effective_price_rub})>"
        )


class UserSettings(Base):
    """Per-user notification and cashback settings."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)

    # Cashback rates
    tinkoff_cashback_percent: Mapped[float] = mapped_column(Float, default=5.0)
    ostrovok_points_rate: Mapped[float] = mapped_column(Float, default=1.0)
    otello_promo_percent: Mapped[float] = mapped_column(Float, default=15.0)
    trip_cashback_percent: Mapped[float] = mapped_column(Float, default=0.0)

    # Notification thresholds
    min_diff_rub: Mapped[float] = mapped_column(Float, default=500.0)
    min_diff_percent: Mapped[float] = mapped_column(Float, default=5.0)

    # Check frequency
    check_interval_hours: Mapped[int] = mapped_column(Integer, default=6)

    def __repr__(self) -> str:
        return f"<UserSettings(user_id={self.user_id})>"
