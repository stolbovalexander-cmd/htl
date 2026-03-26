"""Database repository layer — CRUD operations for all entities."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import BookingBaseline, HotelWatch, ProviderName, UserSettings


class HotelWatchRepo:
    """CRUD for HotelWatch."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, watch: HotelWatch) -> HotelWatch:
        self._session.add(watch)
        await self._session.flush()
        await self._session.refresh(watch)
        return watch

    async def get_by_id(self, watch_id: int) -> HotelWatch | None:
        return await self._session.get(HotelWatch, watch_id)

    async def list_by_user(self, user_id: int, active_only: bool = True) -> Sequence[HotelWatch]:
        stmt = select(HotelWatch).where(HotelWatch.user_id == user_id)
        if active_only:
            stmt = stmt.where(HotelWatch.is_active.is_(True))
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_all_active(self) -> Sequence[HotelWatch]:
        stmt = select(HotelWatch).where(HotelWatch.is_active.is_(True))
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def deactivate(self, watch_id: int) -> bool:
        watch = await self.get_by_id(watch_id)
        if watch is None:
            return False
        watch.is_active = False
        await self._session.flush()
        return True


class BookingBaselineRepo:
    """CRUD for BookingBaseline."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, baseline: BookingBaseline) -> BookingBaseline:
        self._session.add(baseline)
        await self._session.flush()
        await self._session.refresh(baseline)
        return baseline

    async def get_by_watch_id(self, watch_id: int) -> BookingBaseline | None:
        stmt = select(BookingBaseline).where(BookingBaseline.hotel_watch_id == watch_id)
        result = await self._session.execute(stmt)
        return result.scalars().first()

    async def update(
        self,
        baseline_id: int,
        *,
        provider: ProviderName | None = None,
        price_rub: float | None = None,
        cashback_percent: float | None = None,
        cashback_rub: float | None = None,
        effective_price_rub: float | None = None,
    ) -> BookingBaseline | None:
        baseline = await self._session.get(BookingBaseline, baseline_id)
        if baseline is None:
            return None
        if provider is not None:
            baseline.provider = provider
        if price_rub is not None:
            baseline.price_rub = price_rub
        if cashback_percent is not None:
            baseline.cashback_percent = cashback_percent
        if cashback_rub is not None:
            baseline.cashback_rub = cashback_rub
        if effective_price_rub is not None:
            baseline.effective_price_rub = effective_price_rub
        await self._session.flush()
        return baseline


class UserSettingsRepo:
    """CRUD for UserSettings."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, user_id: int) -> UserSettings:
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        result = await self._session.execute(stmt)
        settings = result.scalars().first()
        if settings is None:
            settings = UserSettings(user_id=user_id)
            self._session.add(settings)
            await self._session.flush()
            await self._session.refresh(settings)
        return settings

    async def update(
        self,
        user_id: int,
        *,
        tinkoff_cashback_percent: float | None = None,
        ostrovok_points_rate: float | None = None,
        otello_promo_percent: float | None = None,
        trip_cashback_percent: float | None = None,
        min_diff_rub: float | None = None,
        min_diff_percent: float | None = None,
        check_interval_hours: int | None = None,
    ) -> UserSettings:
        settings = await self.get_or_create(user_id)
        if tinkoff_cashback_percent is not None:
            settings.tinkoff_cashback_percent = tinkoff_cashback_percent
        if ostrovok_points_rate is not None:
            settings.ostrovok_points_rate = ostrovok_points_rate
        if otello_promo_percent is not None:
            settings.otello_promo_percent = otello_promo_percent
        if trip_cashback_percent is not None:
            settings.trip_cashback_percent = trip_cashback_percent
        if min_diff_rub is not None:
            settings.min_diff_rub = min_diff_rub
        if min_diff_percent is not None:
            settings.min_diff_percent = min_diff_percent
        if check_interval_hours is not None:
            settings.check_interval_hours = check_interval_hours
        await self._session.flush()
        return settings
