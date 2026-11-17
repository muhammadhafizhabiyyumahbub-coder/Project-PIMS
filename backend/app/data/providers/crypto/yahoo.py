"Yahoo Finance chart adapter (crypto pairs and stocks, REST public)."
from datetime import datetime, timedelta, timezone

import httpx

from app.data.providers.schemas import RawKline

_HEADERS = {"User-Agent": "Mozilla/5.0 (PIMS market data client)"}


class YahooProvider:
    provider_code = "YAHOO"
    feed_type = "REST_PUBLIC"
    currency = "USD"

    def __init__(
        self, base_url: str = "https://query1.finance.yahoo.com", transport=None
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(transport=transport)

    def fetch_klines(self, instrument: str, timeframe: str, limit: int) -> list[RawKline]:
        interval, bar_seconds = self._timeframe(timeframe)
        # Request enough history for `limit` candles, then trim.
        range_needed = self._range_for(limit, bar_seconds)
        response = self._client.get(
            f"{self.base_url}/v8/finance/chart/{instrument}",
            params={"interval": interval, "range": range_needed},
            headers=_HEADERS,
            timeout=30.0,
        )
        response.raise_for_status()
        payload = response.json()
        error = payload.get("chart", {}).get("error")
        if error:
            raise RuntimeError(f"Yahoo API error: {error.get('description') or error.get('code')}")
        result = payload["chart"]["result"][0]
        timestamps = result.get("timestamp") or []
        quote = result["indicators"]["quote"][0]
        klines: list[RawKline] = []
        for i, start_s in enumerate(timestamps):
            opens, highs, lows, closes, volumes = (
                quote.get("open"),
                quote.get("high"),
                quote.get("low"),
                quote.get("close"),
                quote.get("volume"),
            )
            o, h, l, c = opens[i], highs[i], lows[i], closes[i]
            if None in (o, h, l, c):
                continue  # gap candle with no quotes
            start = datetime.fromtimestamp(start_s, tz=timezone.utc)
            klines.append(
                RawKline(
                    open_time=start,
                    close_time=start + timedelta(seconds=bar_seconds),
                    open_price=float(o),
                    high_price=float(h),
                    low_price=float(l),
                    close_price=float(c),
                    volume=float(volumes[i]) if volumes[i] is not None else None,
                    quote_volume=None,
                )
            )
        return klines[-limit:]

    @staticmethod
    def _timeframe(timeframe: str) -> tuple[str, int]:
        mapping = {"1h": ("1h", 3600), "4h": ("1h", 3600), "1d": ("1d", 86400)}
        if timeframe not in mapping:
            raise ValueError(f"Unsupported timeframe for Yahoo adapter: {timeframe}")
        return mapping[timeframe]

    @staticmethod
    def _range_for(limit: int, bar_seconds: int) -> str:
        hours = limit * bar_seconds / 3600
        if hours <= 730:
            return "30d" if hours > 24 else "7d"
        return "1y"
