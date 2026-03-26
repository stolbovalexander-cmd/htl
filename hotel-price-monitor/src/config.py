"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from .env file."""

    # Telegram
    bot_token: str = ""

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/hotel_monitor.db"

    # Scheduler
    default_check_interval_hours: int = 6

    # Default cashback rates
    default_tinkoff_cashback_percent: float = 5.0
    default_ostrovok_cashback_percent: float = 10.0
    default_otello_promo_percent: float = 15.0
    default_trip_cashback_percent: float = 0.0

    # Notification thresholds
    default_min_diff_rub: float = 500.0
    default_min_diff_percent: float = 5.0

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


def get_settings() -> Settings:
    """Return application settings singleton."""
    return Settings()
