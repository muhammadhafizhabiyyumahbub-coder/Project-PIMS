"Bybit v5 REST market data adapter (public endpoints only)."
import time
from datetime import datetime, timezone

import httpx

from app.data.providers.schemas import RawKline

TIMEFRAME_TO_BYBIT_INTERVAL = {"1h": "60", "4h": "240", "1d": "D"}


class BybitProvider:
    provider_code = "BYBIT"
    feed_type = "REST_PUBLIC"

    def __init__(self, base_url: str = "https://api.bybit.com", transport=None) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(transport=transport)

    def fetch_klines(self, instrument: str, timeframe: str, limit: int) -> list[RawKline]:
        if timeframe not in TIMEFRAME_TO_BYBIT_INTERVAL:
            raise ValueError(f"Unsupported timeframe for Bybit adapter: {timeframe}")
        interval = TIMEFRAME_TO_BYBIT_INTERVAL[timeframe]
        response = self._client.get(
            f"{self.base_url}/v5/market/kline",
            params={
                "category": "spot",
                "symbol": instrument,
                "interval": interval,
                "limit": min(limit, 1000),
            },
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("retCode") != 0:
            raise RuntimeError(f"Bybit API error {payload.get('retCode')}: {payload.get('retMsg')}")
        rows = payload["result"]["list"]
        # Bybit returns newest-first; normalize to oldest-first.
        oldest_first = list(reversed(rows))
        klines: list[RawKline] = []
        for row in oldest_first:
            start_ms, open_, high, low, close, volume, turnover = row[:7]
            klines.append(
                RawKline(
                    open_time=datetime.fromtimestamp(int(start_ms) / 1000, tz=timezone.utc),
                    close_time=datetime.fromtimestamp(
                        int(start_ms) / 1000 + interval_seconds(interval), tz=timezone.utc
                    ),
                    open_price=float(open_),
                    high_price=float(high),
                    low_price=float(low),
                    close_price=float(close),
                    volume=float(volume) if volume else None,
                    quote_volume=float(turnover) if turnover else None,
                )
            )
        return klines


def interval_seconds(interval: str) -> int:
    if interval == "D":
        return 86400
    return int(interval) * 60
