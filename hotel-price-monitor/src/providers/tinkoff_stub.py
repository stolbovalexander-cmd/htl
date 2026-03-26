"""Stub for Tinkoff Travel integration.

In a real implementation this would either:
  - Call an official API (if available), or
  - Use headless Selenium to scrape search results from
    https://www.tinkoff.ru/travel/hotels/

For now this is a placeholder showing the expected structure.
"""

from __future__ import annotations

from src.core.models import Offer
from src.db.models import HotelWatch


class TinkoffTravelProvider:
    """Stub: Tinkoff Travel price provider."""

    @property
    def name(self) -> str:
        return "Tinkoff Travel"

    async def get_prices(self, hotel_watch: HotelWatch) -> list[Offer]:
        """TODO: implement real scraping / API call.

        Pseudocode:
        1. Build search URL with city, dates, guests, rooms.
        2. Fetch page via httpx or Selenium.
        3. Parse JSON/HTML to extract offers.
        4. Map each result to Offer(provider=ProviderName.TINKOFF, ...).
        """
        _ = hotel_watch  # unused in stub
        return []


class OstrovokProvider:
    """Stub: Ostrovok price provider."""

    @property
    def name(self) -> str:
        return "Ostrovok"

    async def get_prices(self, hotel_watch: HotelWatch) -> list[Offer]:
        """TODO: implement Ostrovok API/scraping.

        Ostrovok has a B2B API (https://docs.ostrovok.ru/).
        1. Authenticate with API key.
        2. Search hotel by name/id + dates.
        3. Parse response and map to Offer(provider=ProviderName.OSTROVOK, ...).
        """
        _ = hotel_watch
        return []


class OtelloProvider:
    """Stub: Otello price provider."""

    @property
    def name(self) -> str:
        return "Otello"

    async def get_prices(self, hotel_watch: HotelWatch) -> list[Offer]:
        """TODO: implement Otello integration.

        Otello (otello.ru) — likely requires scraping:
        1. Build search URL.
        2. Fetch and parse results.
        3. Map to Offer(provider=ProviderName.OTELLO, ...).
        """
        _ = hotel_watch
        return []


class TripComProvider:
    """Stub: Trip.com price provider."""

    @property
    def name(self) -> str:
        return "Trip.com"

    async def get_prices(self, hotel_watch: HotelWatch) -> list[Offer]:
        """TODO: implement Trip.com integration.

        Trip.com has an affiliate API.
        1. Authenticate.
        2. Search for hotel by name + dates.
        3. Map results to Offer(provider=ProviderName.TRIP, ...).
        """
        _ = hotel_watch
        return []
