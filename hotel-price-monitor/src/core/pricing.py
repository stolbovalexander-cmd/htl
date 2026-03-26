"""Domain logic: effective price calculation and notification trigger."""

from __future__ import annotations

from src.core.models import Offer, OfferConditions, PriceDiff, ProviderName
from src.db.models import BookingBaseline, HotelWatch, UserSettings
from src.db.models import BreakfastOption as DBBreakfastOption
from src.db.models import PaymentType as DBPaymentType


def compute_cashback_rub(price_rub: float, cashback_percent: float) -> float:
    """Compute cashback in rubles from price and percent."""
    return round(price_rub * cashback_percent / 100.0, 2)


def compute_effective_price(price_rub: float, cashback_rub: float) -> float:
    """Compute effective price after subtracting cashback."""
    return round(price_rub - cashback_rub, 2)


def get_provider_cashback_percent(
    provider: ProviderName, settings: UserSettings
) -> float:
    """Return the user's configured cashback percent for a given provider."""
    mapping: dict[ProviderName, float] = {
        ProviderName.TINKOFF: settings.tinkoff_cashback_percent,
        ProviderName.OSTROVOK: settings.ostrovok_cashback_percent,
        ProviderName.OTELLO: settings.otello_promo_percent,
        ProviderName.TRIP: settings.trip_cashback_percent,
        ProviderName.OTHER: 0.0,
    }
    return mapping.get(provider, 0.0)


def enrich_offer(offer: Offer, settings: UserSettings) -> Offer:
    """Fill in cashback and effective price fields for an offer."""
    cb_percent = get_provider_cashback_percent(offer.provider, settings)
    cb_rub = compute_cashback_rub(offer.price_rub, cb_percent)
    eff = compute_effective_price(offer.price_rub, cb_rub)
    return Offer(
        provider=offer.provider,
        price_rub=offer.price_rub,
        raw_currency=offer.raw_currency,
        raw_price=offer.raw_price,
        conditions=offer.conditions,
        cashback_percent=cb_percent,
        cashback_rub=cb_rub,
        effective_price_rub=eff,
    )


def matches_conditions(offer: Offer, watch: HotelWatch) -> bool:
    """Check whether an offer satisfies the watch filter conditions."""
    cond: OfferConditions = offer.conditions

    if watch.free_cancellation and not cond.free_cancellation:
        return False

    if watch.breakfast_included != DBBreakfastOption.ANY:
        if cond.breakfast_included.value not in (watch.breakfast_included.value, "ANY"):
            return False

    if watch.payment_type != DBPaymentType.ANY:
        if cond.payment_type.value not in (watch.payment_type.value, "ANY"):
            return False

    return True


def compute_diff(baseline: BookingBaseline, offer: Offer) -> PriceDiff:
    """Compute the price difference between the baseline and an offer."""
    diff_rub = round(baseline.effective_price_rub - offer.effective_price_rub, 2)
    if baseline.effective_price_rub > 0:
        diff_pct = round(diff_rub / baseline.effective_price_rub * 100.0, 2)
    else:
        diff_pct = 0.0
    return PriceDiff(
        baseline_effective=baseline.effective_price_rub,
        offer_effective=offer.effective_price_rub,
        diff_rub=diff_rub,
        diff_percent=diff_pct,
        offer=offer,
    )


def should_notify(diff: PriceDiff, settings: UserSettings) -> bool:
    """Decide whether a price difference warrants a user notification.

    The user is notified when the new offer is cheaper AND the saving
    meets **at least one** of the two thresholds (absolute or percentage).
    """
    if diff.diff_rub <= 0:
        return False
    return diff.diff_rub >= settings.min_diff_rub or diff.diff_percent >= settings.min_diff_percent


def find_best_offer(
    offers: list[Offer],
    watch: HotelWatch,
    baseline: BookingBaseline,
    settings: UserSettings,
) -> PriceDiff | None:
    """Among all offers, find the best one that warrants notification.

    Returns the PriceDiff for the cheapest qualifying offer, or None.
    """
    enriched: list[Offer] = []
    for o in offers:
        if matches_conditions(o, watch):
            enriched.append(enrich_offer(o, settings))

    if not enriched:
        return None

    best = min(enriched, key=lambda o: o.effective_price_rub)
    diff = compute_diff(baseline, best)
    if should_notify(diff, settings):
        return diff
    return None
