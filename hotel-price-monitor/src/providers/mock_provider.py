"""Mock provider that generates random offers for development / testing."""

from __future__ import annotations

import random

from src.core.models import BreakfastOption, Offer, OfferConditions, PaymentType, ProviderName
from src.db.models import HotelWatch


class MockProvider:
    """Returns randomised offers so the full pipeline can be tested."""

    def __init__(self, provider: ProviderName = ProviderName.TRIP) -> None:
        self._provider = provider

    @property
    def name(self) -> str:
        return f"Mock({self._provider.value})"

    async def get_prices(self, hotel_watch: HotelWatch) -> list[Offer]:
        """Generate 1-3 random offers."""
        count = random.randint(1, 3)
        nights = (hotel_watch.checkout_date - hotel_watch.checkin_date).days
        if nights <= 0:
            nights = 1
        offers: list[Offer] = []
        for _ in range(count):
            price_per_night = random.uniform(2000, 15000)
            total = round(price_per_night * nights * hotel_watch.rooms_count, 2)
            conditions = OfferConditions(
                free_cancellation=random.choice([True, False]),
                breakfast_included=random.choice(list(BreakfastOption)),
                payment_type=random.choice(list(PaymentType)),
            )
            offers.append(
                Offer(
                    provider=self._provider,
                    price_rub=total,
                    raw_currency="RUB",
                    raw_price=total,
                    conditions=conditions,
                )
            )
        return offers
