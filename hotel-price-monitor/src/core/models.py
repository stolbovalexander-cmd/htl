"""Domain models (pure data, no ORM dependency)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BreakfastOption(str, Enum):
    YES = "YES"
    NO = "NO"
    ANY = "ANY"


class PaymentType(str, Enum):
    ONLINE = "ONLINE"
    ON_SITE = "ON_SITE"
    ANY = "ANY"


class ProviderName(str, Enum):
    TRIP = "TRIP"
    TINKOFF = "TINKOFF"
    OTELLO = "OTELLO"
    OSTROVOK = "OSTROVOK"
    OTHER = "OTHER"


@dataclass(frozen=True)
class OfferConditions:
    """Conditions attached to a hotel offer."""

    free_cancellation: bool = False
    breakfast_included: BreakfastOption = BreakfastOption.ANY
    payment_type: PaymentType = PaymentType.ANY


@dataclass(frozen=True)
class Offer:
    """A single price offer from a provider."""

    provider: ProviderName
    price_rub: float
    raw_currency: str = "RUB"
    raw_price: float = 0.0
    conditions: OfferConditions = OfferConditions()
    cashback_percent: float = 0.0
    cashback_rub: float = 0.0
    effective_price_rub: float = 0.0


@dataclass(frozen=True)
class PriceDiff:
    """Result of comparing an offer against the baseline."""

    baseline_effective: float
    offer_effective: float
    diff_rub: float
    diff_percent: float
    offer: Offer
