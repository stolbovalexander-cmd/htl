"""Periodic price-check scheduler using APScheduler."""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine, Sequence
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.models import Offer
from src.core.notifications import format_notification
from src.core.pricing import find_best_offer
from src.db.models import HotelWatch
from src.db.repository import HotelWatchRepo, UserSettingsRepo
from src.providers.base import PriceProvider

SendMessageFn = Callable[[int, str], Coroutine[Any, Any, Any]]

logger = logging.getLogger(__name__)


async def check_prices(
    session_factory: async_sessionmaker[AsyncSession],
    providers: list[PriceProvider],
    send_message: SendMessageFn,
    user_id: int | None = None,
) -> None:
    """Run a full price-check cycle for active watches.

    If *user_id* is given, only that user's watches are checked (manual /check).
    Otherwise all active watches are checked (scheduled job).
    """
    async with session_factory() as session:
        watch_repo = HotelWatchRepo(session)
        settings_repo = UserSettingsRepo(session)
        if user_id is not None:
            watches: Sequence[HotelWatch] = await watch_repo.list_by_user(user_id)
        else:
            watches = await watch_repo.list_all_active()

        for watch in watches:
            baseline = watch.baseline
            if baseline is None:
                continue

            settings = await settings_repo.get_or_create(watch.user_id)

            # Collect offers from all providers
            all_offers: list[Offer] = []
            for provider in providers:
                try:
                    offers = await provider.get_prices(watch)
                    all_offers.extend(offers)
                except Exception:
                    logger.exception("Provider %s failed for watch %s", provider.name, watch.id)

            if not all_offers:
                continue

            diff = find_best_offer(all_offers, watch, baseline, settings)
            if diff is not None:
                text = format_notification(watch, baseline, diff)
                try:
                    await send_message(watch.user_id, text)
                except Exception:
                    logger.exception("Failed to send notification to user %s", watch.user_id)



def start_scheduler(
    session_factory: async_sessionmaker[AsyncSession],
    providers: list[PriceProvider],
    send_message: SendMessageFn,
    interval_hours: int = 6,
) -> AsyncIOScheduler:
    """Create and start the APScheduler."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_prices,
        "interval",
        hours=interval_hours,
        args=[session_factory, providers, send_message],
        id="price_check",
        replace_existing=True,
        next_run_time=None,  # Don't run immediately on startup
    )
    scheduler.start()
    logger.info("Scheduler started with interval=%dh", interval_hours)
    return scheduler
