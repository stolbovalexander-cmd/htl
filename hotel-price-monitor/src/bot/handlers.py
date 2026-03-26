"""Telegram bot command handlers (aiogram 3.x)."""

from __future__ import annotations

from datetime import date, datetime

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.pricing import compute_cashback_rub, compute_effective_price
from src.db.models import (
    BookingBaseline,
    BreakfastOption,
    HotelWatch,
    PaymentType,
    ProviderName,
)
from src.db.repository import BookingBaselineRepo, HotelWatchRepo, UserSettingsRepo

router = Router()


# ── FSM states for /add wizard ────────────────────────────────────────────


class AddWatchFSM(StatesGroup):
    city = State()
    hotel_name = State()
    checkin_date = State()
    checkout_date = State()
    guests_count = State()
    rooms_count = State()
    free_cancellation = State()
    breakfast = State()
    payment = State()
    booking_provider = State()
    booking_price = State()
    booking_cashback = State()


class SettingsFSM(StatesGroup):
    field = State()
    value = State()


# ── Helpers ────────────────────────────────────────────────────────────────


def _get_session_factory(message: Message) -> async_sessionmaker[AsyncSession]:
    """Retrieve the session factory stored in bot context data."""
    factory: async_sessionmaker[AsyncSession] = message.bot.session_factory  # type: ignore[union-attr]
    return factory


def _parse_date(text: str) -> date | None:
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
    return None


# ── /start ─────────────────────────────────────────────────────────────────


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    factory = _get_session_factory(message)
    async with factory() as session:
        repo = UserSettingsRepo(session)
        await repo.get_or_create(user_id)
        await session.commit()

    await message.answer(
        "👋 Привет! Я бот для мониторинга цен на отели.\n\n"
        "Команды:\n"
        "/add — добавить отель для мониторинга\n"
        "/list — список отслеживаемых отелей\n"
        "/watch <id> — подробности\n"
        "/remove <id> — удалить\n"
        "/settings — настройки кешбэка и уведомлений\n"
    )


# ── /add wizard ────────────────────────────────────────────────────────────


@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext) -> None:
    await state.set_state(AddWatchFSM.city)
    await message.answer("🏙 Введите город:")


@router.message(AddWatchFSM.city)
async def on_city(message: Message, state: FSMContext) -> None:
    await state.update_data(city=message.text)
    await state.set_state(AddWatchFSM.hotel_name)
    await message.answer("🏨 Введите название отеля:")


@router.message(AddWatchFSM.hotel_name)
async def on_hotel_name(message: Message, state: FSMContext) -> None:
    await state.update_data(hotel_name=message.text)
    await state.set_state(AddWatchFSM.checkin_date)
    await message.answer("📅 Введите дату заезда (YYYY-MM-DD):")


@router.message(AddWatchFSM.checkin_date)
async def on_checkin(message: Message, state: FSMContext) -> None:
    d = _parse_date(message.text or "")
    if d is None:
        await message.answer("⚠️ Неверный формат. Попробуйте: YYYY-MM-DD")
        return
    await state.update_data(checkin_date=d.isoformat())
    await state.set_state(AddWatchFSM.checkout_date)
    await message.answer("📅 Введите дату выезда (YYYY-MM-DD):")


@router.message(AddWatchFSM.checkout_date)
async def on_checkout(message: Message, state: FSMContext) -> None:
    d = _parse_date(message.text or "")
    if d is None:
        await message.answer("⚠️ Неверный формат. Попробуйте: YYYY-MM-DD")
        return
    await state.update_data(checkout_date=d.isoformat())
    await state.set_state(AddWatchFSM.guests_count)
    await message.answer("👥 Количество гостей:")


@router.message(AddWatchFSM.guests_count)
async def on_guests(message: Message, state: FSMContext) -> None:
    try:
        val = int(message.text or "1")
    except ValueError:
        await message.answer("⚠️ Введите число.")
        return
    await state.update_data(guests_count=val)
    await state.set_state(AddWatchFSM.rooms_count)
    await message.answer("🚪 Количество номеров:")


@router.message(AddWatchFSM.rooms_count)
async def on_rooms(message: Message, state: FSMContext) -> None:
    try:
        val = int(message.text or "1")
    except ValueError:
        await message.answer("⚠️ Введите число.")
        return
    await state.update_data(rooms_count=val)
    await state.set_state(AddWatchFSM.free_cancellation)
    await message.answer("🔄 Нужна бесплатная отмена? (да/нет):")


@router.message(AddWatchFSM.free_cancellation)
async def on_cancellation(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().lower()
    await state.update_data(free_cancellation=text in ("да", "yes", "1", "true"))
    await state.set_state(AddWatchFSM.breakfast)
    await message.answer("🍳 Завтрак? (YES / NO / ANY):")


@router.message(AddWatchFSM.breakfast)
async def on_breakfast(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().upper()
    if text not in ("YES", "NO", "ANY"):
        await message.answer("⚠️ Введите YES, NO или ANY.")
        return
    await state.update_data(breakfast=text)
    await state.set_state(AddWatchFSM.payment)
    await message.answer("💳 Тип оплаты? (ONLINE / ON_SITE / ANY):")


@router.message(AddWatchFSM.payment)
async def on_payment(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().upper()
    if text not in ("ONLINE", "ON_SITE", "ANY"):
        await message.answer("⚠️ Введите ONLINE, ON_SITE или ANY.")
        return
    await state.update_data(payment=text)
    await state.set_state(AddWatchFSM.booking_provider)
    await message.answer(
        "📌 Площадка текущей брони?\n"
        "(TRIP / TINKOFF / OTELLO / OSTROVOK / OTHER):"
    )


@router.message(AddWatchFSM.booking_provider)
async def on_provider(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().upper()
    if text not in [p.value for p in ProviderName]:
        await message.answer("⚠️ Выберите: TRIP, TINKOFF, OTELLO, OSTROVOK или OTHER.")
        return
    await state.update_data(booking_provider=text)
    await state.set_state(AddWatchFSM.booking_price)
    await message.answer("💰 Цена текущей брони (в рублях):")


@router.message(AddWatchFSM.booking_price)
async def on_price(message: Message, state: FSMContext) -> None:
    try:
        val = float((message.text or "0").replace(",", ".").replace(" ", ""))
    except ValueError:
        await message.answer("⚠️ Введите число.")
        return
    await state.update_data(booking_price=val)
    await state.set_state(AddWatchFSM.booking_cashback)
    await message.answer("🎁 Кешбэк текущей брони (% — число, например 5):")


@router.message(AddWatchFSM.booking_cashback)
async def on_cashback(message: Message, state: FSMContext) -> None:
    try:
        val = float((message.text or "0").replace(",", ".").replace(" ", ""))
    except ValueError:
        await message.answer("⚠️ Введите число.")
        return

    data = await state.get_data()
    user_id = message.from_user.id if message.from_user else 0
    factory = _get_session_factory(message)

    async with factory() as session:
        watch_repo = HotelWatchRepo(session)
        baseline_repo = BookingBaselineRepo(session)

        watch = HotelWatch(
            user_id=user_id,
            city=data["city"],
            hotel_name=data["hotel_name"],
            checkin_date=date.fromisoformat(data["checkin_date"]),
            checkout_date=date.fromisoformat(data["checkout_date"]),
            guests_count=data["guests_count"],
            rooms_count=data["rooms_count"],
            free_cancellation=data["free_cancellation"],
            breakfast_included=BreakfastOption(data["breakfast"]),
            payment_type=PaymentType(data["payment"]),
        )
        watch = await watch_repo.create(watch)

        price_rub = data["booking_price"]
        cb_pct = val
        cb_rub = compute_cashback_rub(price_rub, cb_pct)
        eff = compute_effective_price(price_rub, cb_rub)

        baseline = BookingBaseline(
            hotel_watch_id=watch.id,
            provider=ProviderName(data["booking_provider"]),
            price_rub=price_rub,
            cashback_percent=cb_pct,
            cashback_rub=cb_rub,
            effective_price_rub=eff,
        )
        await baseline_repo.create(baseline)
        await session.commit()

    await state.clear()
    await message.answer(
        f"✅ Мониторинг добавлен (ID: {watch.id}).\n"
        f"Отель: {watch.hotel_name}, {watch.city}\n"
        f"Даты: {watch.checkin_date} — {watch.checkout_date}\n"
        f"Текущая бронь: {price_rub:,.0f} ₽ → эфф. {eff:,.0f} ₽\n"
        f"Используйте /list для просмотра."
    )


# ── /list ──────────────────────────────────────────────────────────────────


@router.message(Command("list"))
async def cmd_list(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    factory = _get_session_factory(message)

    async with factory() as session:
        repo = HotelWatchRepo(session)
        watches = await repo.list_by_user(user_id)

    if not watches:
        await message.answer("📭 У вас нет активных мониторингов. Используйте /add.")
        return

    lines: list[str] = ["📋 *Ваши мониторинги:*\n"]
    for w in watches:
        eff = w.baseline.effective_price_rub if w.baseline else "—"
        lines.append(
            f"• ID {w.id}: {w.hotel_name} ({w.city})\n"
            f"  {w.checkin_date} — {w.checkout_date}, эфф. цена: {eff} ₽"
        )
    await message.answer("\n".join(lines), parse_mode="Markdown")


# ── /watch <id> ────────────────────────────────────────────────────────────


@router.message(Command("watch"))
async def cmd_watch(message: Message) -> None:
    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /watch <id>")
        return
    watch_id = int(parts[1])
    user_id = message.from_user.id if message.from_user else 0
    factory = _get_session_factory(message)

    async with factory() as session:
        repo = HotelWatchRepo(session)
        w = await repo.get_by_id(watch_id)

    if w is None or w.user_id != user_id:
        await message.answer("❌ Мониторинг не найден.")
        return

    bl = w.baseline
    text = (
        f"🏨 *{w.hotel_name}* ({w.city})\n"
        f"📅 {w.checkin_date} — {w.checkout_date}\n"
        f"👥 Гостей: {w.guests_count}, номеров: {w.rooms_count}\n"
        f"🔄 Бесплатная отмена: {'Да' if w.free_cancellation else 'Нет'}\n"
        f"🍳 Завтрак: {w.breakfast_included.value}\n"
        f"💳 Оплата: {w.payment_type.value}\n"
    )
    if bl:
        text += (
            f"\n📌 *Текущая бронь:*\n"
            f"  Площадка: {bl.provider.value}\n"
            f"  Цена: {bl.price_rub:,.0f} ₽\n"
            f"  Кешбэк: {bl.cashback_rub:,.0f} ₽ ({bl.cashback_percent}%)\n"
            f"  Эффективная: {bl.effective_price_rub:,.0f} ₽"
        )
    await message.answer(text, parse_mode="Markdown")


# ── /remove <id> ───────────────────────────────────────────────────────────


@router.message(Command("remove"))
async def cmd_remove(message: Message) -> None:
    parts = (message.text or "").split()
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Использование: /remove <id>")
        return
    watch_id = int(parts[1])
    user_id = message.from_user.id if message.from_user else 0
    factory = _get_session_factory(message)

    async with factory() as session:
        repo = HotelWatchRepo(session)
        w = await repo.get_by_id(watch_id)
        if w is None or w.user_id != user_id:
            await message.answer("❌ Мониторинг не найден.")
            return
        await repo.deactivate(watch_id)
        await session.commit()

    await message.answer(f"🗑 Мониторинг ID {watch_id} удалён.")


# ── /settings ──────────────────────────────────────────────────────────────


SETTINGS_FIELDS: dict[str, str] = {
    "1": "tinkoff_cashback_percent",
    "2": "ostrovok_points_rate",
    "3": "otello_promo_percent",
    "4": "trip_cashback_percent",
    "5": "min_diff_rub",
    "6": "min_diff_percent",
    "7": "check_interval_hours",
}


@router.message(Command("settings"))
async def cmd_settings(message: Message, state: FSMContext) -> None:
    user_id = message.from_user.id if message.from_user else 0
    factory = _get_session_factory(message)

    async with factory() as session:
        repo = UserSettingsRepo(session)
        s = await repo.get_or_create(user_id)

    text = (
        "⚙️ *Ваши настройки:*\n\n"
        f"1. Tinkoff кешбэк: {s.tinkoff_cashback_percent}%\n"
        f"2. Ostrovok баллы (₽ за 1 балл): {s.ostrovok_points_rate}\n"
        f"3. Otello промо: {s.otello_promo_percent}%\n"
        f"4. Trip.com кешбэк: {s.trip_cashback_percent}%\n"
        f"5. Порог уведомления (₽): {s.min_diff_rub}\n"
        f"6. Порог уведомления (%): {s.min_diff_percent}\n"
        f"7. Частота проверки (ч): {s.check_interval_hours}\n\n"
        "Отправьте номер параметра для изменения (или /cancel):"
    )
    await state.set_state(SettingsFSM.field)
    await message.answer(text, parse_mode="Markdown")


@router.message(SettingsFSM.field)
async def on_settings_field(message: Message, state: FSMContext) -> None:
    choice = (message.text or "").strip()
    if choice not in SETTINGS_FIELDS:
        await message.answer("⚠️ Введите номер от 1 до 7.")
        return
    await state.update_data(settings_field=SETTINGS_FIELDS[choice])
    await state.set_state(SettingsFSM.value)
    await message.answer("Введите новое значение:")


@router.message(SettingsFSM.value)
async def on_settings_value(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    field: str = data["settings_field"]
    try:
        if field == "check_interval_hours":
            val: float | int = int(message.text or "6")
        else:
            val = float((message.text or "0").replace(",", "."))
    except ValueError:
        await message.answer("⚠️ Введите число.")
        return

    user_id = message.from_user.id if message.from_user else 0
    factory = _get_session_factory(message)

    async with factory() as session:
        repo = UserSettingsRepo(session)
        await repo.update(user_id, **{field: val})  # type: ignore[arg-type]
        await session.commit()

    await state.clear()
    await message.answer(f"✅ {field} обновлён: {val}")


# ── /cancel ────────────────────────────────────────────────────────────────


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("❌ Действие отменено.")
