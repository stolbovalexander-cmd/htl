"""Base interface for price providers."""

from __future__ import annotations

from typing import Protocol

from src.core.models import Offer
from src.db.models import HotelWatch


class PriceProvider(Protocol):
    """Interface that every price provider must implement."""

    @property
    def name(self) -> str:
        """Human-readable provider name."""
        ...

    async def get_prices(self, hotel_watch: HotelWatch) -> list[Offer]:
        """Fetch available offers for a given hotel watch."""
        ...
