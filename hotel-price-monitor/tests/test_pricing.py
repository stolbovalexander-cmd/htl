"""Tests for domain pricing logic and notification triggers."""

from __future__ import annotations

from datetime import date

import pytest

from src.core.models import (
    BreakfastOption,
    Offer,
    OfferConditions,
    PaymentType,
    ProviderName,
)
from src.core.pricing import (
    compute_cashback_rub,
    compute_diff,
    compute_effective_price,
    enrich_offer,
    find_best_offer,
    matches_conditions,
    should_notify,
)
from src.db.models import BookingBaseline, HotelWatch, UserSettings
from src.db.models import BreakfastOption as DBBreakfast
from src.db.models import PaymentType as DBPayment
from src.db.models import ProviderName as DBProvider

# ── Helpers ────────────────────────────────────────────────────────────────


def _make_settings(
    tinkoff: float = 5.0,
    ostrovok: float = 1.0,
    otello: float = 15.0,
    trip: float = 0.0,
    min_rub: float = 500.0,
    min_pct: float = 5.0,
) -> UserSettings:
    return UserSettings(
        user_id=123,
        tinkoff_cashback_percent=tinkoff,
        ostrovok_cashback_percent=ostrovok,
        otello_promo_percent=otello,
        trip_cashback_percent=trip,
        min_diff_rub=min_rub,
        min_diff_percent=min_pct,
        check_interval_hours=6,
    )


def _make_baseline(
    price: float = 10000.0,
    cb_pct: float = 5.0,
    provider: DBProvider = DBProvider.TINKOFF,
) -> BookingBaseline:
    cb_rub = compute_cashback_rub(price, cb_pct)
    eff = compute_effective_price(price, cb_rub)
    return BookingBaseline(
        id=1,
        hotel_watch_id=1,
        provider=provider,
        price_rub=price,
        currency="RUB",
        exchange_rate=1.0,
        cashback_percent=cb_pct,
        cashback_rub=cb_rub,
        effective_price_rub=eff,
    )


def _make_watch(
    free_cancel: bool = False,
    breakfast: DBBreakfast = DBBreakfast.ANY,
    payment: DBPayment = DBPayment.ANY,
) -> HotelWatch:
    return HotelWatch(
        id=1,
        user_id=123,
        city="Moscow",
        hotel_name="Test Hotel",
        checkin_date=date(2026, 7, 1),
        checkout_date=date(2026, 7, 5),
        guests_count=2,
        rooms_count=1,
        free_cancellation=free_cancel,
        breakfast_included=breakfast,
        payment_type=payment,
        is_active=True,
    )


def _make_offer(
    provider: ProviderName = ProviderName.TRIP,
    price: float = 8000.0,
    free_cancel: bool = True,
    breakfast: BreakfastOption = BreakfastOption.YES,
    payment: PaymentType = PaymentType.ONLINE,
) -> Offer:
    return Offer(
        provider=provider,
        price_rub=price,
        raw_currency="RUB",
        raw_price=price,
        conditions=OfferConditions(
            free_cancellation=free_cancel,
            breakfast_included=breakfast,
            payment_type=payment,
        ),
    )


# ── Tests ──────────────────────────────────────────────────────────────────


class TestComputeCashbackRub:
    def test_basic(self) -> None:
        assert compute_cashback_rub(10000, 5) == 500.0

    def test_zero_percent(self) -> None:
        assert compute_cashback_rub(10000, 0) == 0.0

    def test_rounding(self) -> None:
        assert compute_cashback_rub(9999, 3.33) == 332.97


class TestComputeEffectivePrice:
    def test_basic(self) -> None:
        assert compute_effective_price(10000, 500) == 9500.0

    def test_zero_cashback(self) -> None:
        assert compute_effective_price(10000, 0) == 10000.0


class TestEnrichOffer:
    def test_tinkoff_cashback(self) -> None:
        settings = _make_settings(tinkoff=10.0)
        offer = _make_offer(provider=ProviderName.TINKOFF, price=10000)
        enriched = enrich_offer(offer, settings)
        assert enriched.cashback_percent == 10.0
        assert enriched.cashback_rub == 1000.0
        assert enriched.effective_price_rub == 9000.0

    def test_otello_promo(self) -> None:
        settings = _make_settings(otello=15.0)
        offer = _make_offer(provider=ProviderName.OTELLO, price=20000)
        enriched = enrich_offer(offer, settings)
        assert enriched.cashback_percent == 15.0
        assert enriched.cashback_rub == 3000.0
        assert enriched.effective_price_rub == 17000.0


class TestMatchesConditions:
    def test_any_passes_all(self) -> None:
        watch = _make_watch()
        offer = _make_offer()
        assert matches_conditions(offer, watch) is True

    def test_free_cancel_required_but_missing(self) -> None:
        watch = _make_watch(free_cancel=True)
        offer = _make_offer(free_cancel=False)
        assert matches_conditions(offer, watch) is False

    def test_free_cancel_required_and_present(self) -> None:
        watch = _make_watch(free_cancel=True)
        offer = _make_offer(free_cancel=True)
        assert matches_conditions(offer, watch) is True

    def test_breakfast_yes_required(self) -> None:
        watch = _make_watch(breakfast=DBBreakfast.YES)
        offer_no = _make_offer(breakfast=BreakfastOption.NO)
        assert matches_conditions(offer_no, watch) is False

    def test_payment_online_required(self) -> None:
        watch = _make_watch(payment=DBPayment.ONLINE)
        offer_site = _make_offer(payment=PaymentType.ON_SITE)
        assert matches_conditions(offer_site, watch) is False


class TestComputeDiff:
    def test_cheaper_offer(self) -> None:
        baseline = _make_baseline(price=10000, cb_pct=5)  # eff = 9500
        offer = _make_offer(price=8000)
        offer = Offer(
            provider=offer.provider,
            price_rub=offer.price_rub,
            conditions=offer.conditions,
            cashback_percent=0,
            cashback_rub=0,
            effective_price_rub=8000,
        )
        diff = compute_diff(baseline, offer)
        assert diff.diff_rub == 1500.0
        assert diff.diff_percent == pytest.approx(15.79, abs=0.01)

    def test_more_expensive(self) -> None:
        baseline = _make_baseline(price=10000, cb_pct=5)  # eff = 9500
        offer = Offer(
            provider=ProviderName.TRIP,
            price_rub=11000,
            effective_price_rub=11000,
        )
        diff = compute_diff(baseline, offer)
        assert diff.diff_rub == -1500.0


class TestShouldNotify:
    def test_above_both_thresholds(self) -> None:
        from src.core.models import PriceDiff

        settings = _make_settings(min_rub=500, min_pct=5)
        diff = PriceDiff(
            baseline_effective=10000,
            offer_effective=9000,
            diff_rub=1000,
            diff_percent=10.0,
            offer=_make_offer(),
        )
        assert should_notify(diff, settings) is True

    def test_below_both_thresholds(self) -> None:
        from src.core.models import PriceDiff

        settings = _make_settings(min_rub=500, min_pct=5)
        diff = PriceDiff(
            baseline_effective=10000,
            offer_effective=9800,
            diff_rub=200,
            diff_percent=2.0,
            offer=_make_offer(),
        )
        assert should_notify(diff, settings) is False

    def test_above_rub_only(self) -> None:
        from src.core.models import PriceDiff

        settings = _make_settings(min_rub=500, min_pct=20)
        diff = PriceDiff(
            baseline_effective=100000,
            offer_effective=99000,
            diff_rub=1000,
            diff_percent=1.0,
            offer=_make_offer(),
        )
        assert should_notify(diff, settings) is True

    def test_negative_diff(self) -> None:
        from src.core.models import PriceDiff

        settings = _make_settings()
        diff = PriceDiff(
            baseline_effective=10000,
            offer_effective=11000,
            diff_rub=-1000,
            diff_percent=-10.0,
            offer=_make_offer(),
        )
        assert should_notify(diff, settings) is False


class TestFindBestOffer:
    def test_finds_cheapest(self) -> None:
        watch = _make_watch()
        baseline = _make_baseline(price=15000, cb_pct=5)  # eff = 14250
        settings = _make_settings(trip=0, min_rub=500, min_pct=5)
        offers = [
            _make_offer(provider=ProviderName.TRIP, price=12000),
            _make_offer(provider=ProviderName.TRIP, price=10000),
            _make_offer(provider=ProviderName.TRIP, price=14000),
        ]
        result = find_best_offer(offers, watch, baseline, settings)
        assert result is not None
        assert result.offer.price_rub == 10000

    def test_no_qualifying(self) -> None:
        watch = _make_watch()
        baseline = _make_baseline(price=10000, cb_pct=0)  # eff = 10000
        settings = _make_settings(min_rub=500, min_pct=5)
        offers = [_make_offer(price=9900)]
        result = find_best_offer(offers, watch, baseline, settings)
        assert result is None
