"""Bot factory — creates and configures the aiogram Bot + Dispatcher."""

from __future__ import annotations

import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.bot.handlers import router


def create_bot(token: str) -> Bot:
    """Create a Telegram Bot instance with Tor proxy support."""
    
    # Проверяем .env на наличие прокси (по умолчанию Tor Browser)
    proxy_url = os.getenv("PROXY_URL", "socks5://127.0.0.1:9150")
    
    # Если прокси указан, настраиваем Tor Browser (порт 9150)
    if proxy_url.startswith("socks5://"):
        print(f"🔥 Используем Tor прокси: {proxy_url}")
        
        # ✅ ПРАВИЛЬНАЯ настройка для aiogram 3.x + SOCKS5
        session = AiohttpSession(
            proxy=proxy_url  # <-- ТОЛЬКО proxy параметр!
        )
        
        return Bot(
            token=token,
            session=session,
            default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
        )
    
    # Без прокси (для VPS/нормального интернета)
    print("🌐 Используем прямое подключение")
    return Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )


def create_dispatcher(session_factory: async_sessionmaker[AsyncSession]) -> Dispatcher:
    """Create and wire the Dispatcher with all routers."""
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    dp["session_factory"] = session_factory
    return dp
