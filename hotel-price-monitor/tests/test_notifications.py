"""Tests for notification message formatting."""

from __future__ import annotations

from datetime import date

from src.core.models import Offer, PriceDiff, ProviderName
from src.core.notifications import format_notification
from src.db.models import BookingBaseline, HotelWatch
from src.db.models import ProviderName as DBProvider


def _make_watch() -> HotelWatch:
    return HotelWatch(
        id=1,
        user_id=123,
        city="Сочи",
        hotel_name="Grand Hotel",
        checkin_date=date(2026, 8, 1),
        checkout_date=date(2026, 8, 5),
        guests_count=2,
        rooms_count=1,
    )


def _make_baseline() -> BookingBaseline:
    return BookingBaseline(
        id=1,
        hotel_watch_id=1,
        provider=DBProvider.TINKOFF,
        price_rub=50000,
        cashback_percent=5.0,
        cashback_rub=2500,
        effective_price_rub=47500,
    )


def test_format_contains_key_info() -> None:
    watch = _make_watch()
    baseline = _make_baseline()
    offer = Offer(
        provider=ProviderName.OSTROVOK,
        price_rub=42000,
        cashback_percent=10,
        cashback_rub=4200,
        effective_price_rub=37800,
    )
    diff = PriceDiff(
        baseline_effective=47500,
        offer_effective=37800,
        diff_rub=9700,
        diff_percent=20.42,
        offer=offer,
    )
    msg = format_notification(watch, baseline, diff)
    assert "Grand Hotel" in msg
    assert "Сочи" in msg
    assert "TINKOFF" in msg
    assert "OSTROVOK" in msg
    assert "9,700" in msg or "9 700" in msg
    assert "перебронируй" in msg
