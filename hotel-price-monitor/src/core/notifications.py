"""Notification message formatting."""

from __future__ import annotations

from src.core.models import PriceDiff
from src.db.models import BookingBaseline, HotelWatch


def format_notification(watch: HotelWatch, baseline: BookingBaseline, diff: PriceDiff) -> str:
    """Build a human-readable Telegram notification message."""
    offer = diff.offer
    lines: list[str] = [
        f"🏨 *{watch.hotel_name}* ({watch.city})",
        f"📅 {watch.checkin_date} — {watch.checkout_date}",
        "",
        "📌 *Текущая бронь:*",
        f"  Площадка: {baseline.provider.value}",
        f"  Цена: {baseline.price_rub:,.0f} ₽",
        f"  Кешбэк: {baseline.cashback_rub:,.0f} ₽ ({baseline.cashback_percent}%)",
        f"  Эффективная цена: {baseline.effective_price_rub:,.0f} ₽",
        "",
        "💰 *Лучшее найденное предложение:*",
        f"  Площадка: {offer.provider.value}",
        f"  Цена: {offer.price_rub:,.0f} ₽",
        f"  Кешбэк: {offer.cashback_rub:,.0f} ₽ ({offer.cashback_percent}%)",
        f"  Эффективная цена: {offer.effective_price_rub:,.0f} ₽",
        "",
        f"✅ Сейчас выгоднее на *{diff.diff_rub:,.0f} ₽* ({diff.diff_percent:.1f}%).",
        "Проверь условия и, если ок, перебронируй.",
    ]
    return "\n".join(lines)
