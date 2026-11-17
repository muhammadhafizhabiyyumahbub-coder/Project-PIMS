"Provider adapter protocol. Adapters return raw provider payloads only."
from typing import Protocol

from app.data.providers.schemas import RawKline


class MarketDataProvider(Protocol):
    """Adapter interface for market data providers."""

    provider_code: str
    feed_type: str

    def fetch_klines(
        self, instrument: str, timeframe: str, limit: int
    ) -> list[RawKline]:
        """Fetch historical candles for one provider instrument."""
        ...
