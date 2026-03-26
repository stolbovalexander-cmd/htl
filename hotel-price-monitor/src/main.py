"""Application entry point — wires all layers together."""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from src.bot.bot import create_bot, create_dispatcher
from src.config import get_settings
from src.core.models import ProviderName
from src.db.engine import build_engine, build_session_factory, init_db
from src.providers.mock_provider import MockProvider
from src.scheduler import check_prices, start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()

    if not settings.bot_token:
        logger.error("BOT_TOKEN is not set. Please configure .env file.")
        sys.exit(1)

    # Ensure data directory exists (for SQLite)
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    # Database
    engine = build_engine(settings)
    await init_db(engine)
    session_factory = build_session_factory(engine)

    # Bot
    bot = create_bot(settings.bot_token)
    # Attach session_factory to bot so handlers can access it
    bot.session_factory = session_factory  # type: ignore[attr-defined]
    dp = create_dispatcher(session_factory)

    # Providers (mock for now)
    providers = [
        MockProvider(ProviderName.TRIP),
        MockProvider(ProviderName.TINKOFF),
        MockProvider(ProviderName.OSTROVOK),
        MockProvider(ProviderName.OTELLO),
    ]

    # Scheduler
    async def send_tg_message(user_id: int, text: str) -> None:
        await bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown")

    _scheduler = start_scheduler(
        session_factory=session_factory,
        providers=providers,  # type: ignore[arg-type]
        send_message=send_tg_message,
        interval_hours=settings.default_check_interval_hours,
    )

    # Attach manual check function so /check handler can call it
    async def _manual_check(uid: int) -> None:
        await check_prices(
            session_factory=session_factory,
            providers=providers,  # type: ignore[arg-type]
            send_message=send_tg_message,
            user_id=uid,
        )

    bot._check_prices_fn = _manual_check  # type: ignore[attr-defined]

    # Start polling
    logger.info("Bot is starting…")
    try:
        await dp.start_polling(bot)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
