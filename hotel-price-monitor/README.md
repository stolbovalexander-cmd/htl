# Hotel Price Monitor — Telegram Bot

Telegram-бот для мониторинга цен на отели. Отслеживает предложения на нескольких площадках (Trip.com, Тинькофф Путешествия, Отелло, Островок), считает эффективную цену с учётом кешбэка и уведомляет при выгодном снижении.

## Архитектура

```
src/
├── bot/            # Telegram-бот (aiogram 3.x)
│   ├── bot.py      # Фабрика Bot + Dispatcher
│   └── handlers.py # Команды: /start, /add, /list, /watch, /remove, /settings
├── core/           # Доменная логика
│   ├── models.py   # Offer, PriceDiff, OfferConditions
│   ├── pricing.py  # Расчёт эффективной цены, триггер уведомлений
│   └── notifications.py # Форматирование сообщений
├── db/             # Слой данных
│   ├── models.py   # SQLAlchemy ORM: HotelWatch, BookingBaseline, UserSettings
│   ├── engine.py   # Создание engine + init_db
│   └── repository.py # CRUD-репозитории
├── providers/      # Интеграции с площадками
│   ├── base.py     # PriceProvider Protocol
│   ├── mock_provider.py # Mock-провайдер для тестов
│   └── tinkoff_stub.py  # Заглушки: Tinkoff, Ostrovok, Otello, Trip.com
├── config.py       # Настройки из .env (pydantic-settings)
├── scheduler.py    # APScheduler — периодическая проверка цен
└── main.py         # Точка входа
tests/
├── test_pricing.py       # Тесты расчёта цен и триггера уведомлений
└── test_notifications.py # Тесты форматирования сообщений
```

## Быстрый старт

### Требования
- Python 3.11+
- [Poetry](https://python-poetry.org/)

### 1. Клонировать и установить зависимости

```bash
git clone <repo-url>
cd hotel-price-monitor
poetry install
```

### 2. Настроить переменные окружения

```bash
cp .env.example .env
# Отредактируйте .env — укажите BOT_TOKEN
```

### 3. Запустить бота

```bash
poetry run python -m src.main
```

### 4. Запуск через Docker

```bash
cp .env.example .env
# Отредактируйте .env
docker compose up --build
```

## Запуск тестов

```bash
poetry run pytest -v
```

## Типизация и линтинг

```bash
poetry run mypy src/
poetry run ruff check src/
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Регистрация и описание |
| `/add` | Мастер добавления отеля (пошагово) |
| `/list` | Список отслеживаемых отелей |
| `/watch <id>` | Подробности по мониторингу |
| `/remove <id>` | Удалить мониторинг |
| `/settings` | Настройки кешбэка и уведомлений |
| `/cancel` | Отменить текущее действие |

## Подключение реальных провайдеров

В `src/providers/tinkoff_stub.py` находятся заглушки для всех площадок.
Каждая реализует интерфейс `PriceProvider` из `src/providers/base.py`:

```python
class PriceProvider(Protocol):
    name: str
    async def get_prices(self, hotel_watch: HotelWatch) -> list[Offer]: ...
```

Для подключения реального провайдера:
1. Реализуйте `get_prices()` с HTTP-запросами (httpx) или Selenium.
2. Замените `MockProvider` в `src/main.py` на реальную реализацию.

### Примерный план по площадкам

- **Tinkoff Travel**: Нет публичного API → headless Selenium-скрейпинг.
- **Ostrovok**: Есть B2B API (docs.ostrovok.ru) → httpx + API-ключ.
- **Otello**: Нет публичного API → скрейпинг.
- **Trip.com**: Affiliate API → httpx + аутентификация.

## Лицензия

MIT
