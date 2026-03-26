"""Bot factory — creates and configures the aiogram Bot + Dispatcher."""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.handlers import router


def create_bot(token: str) -> Bot:
    """Create a Telegram Bot instance."""
    return Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )


def create_dispatcher(session_factory: async_sessionmaker[AsyncSession]) -> Dispatcher:
    """Create and wire the Dispatcher with all routers."""
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    # Store session factory so handlers can access it via bot context
    dp["session_factory"] = session_factory
    return dp
