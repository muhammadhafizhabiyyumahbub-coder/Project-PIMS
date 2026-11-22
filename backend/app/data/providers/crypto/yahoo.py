"Yahoo Finance chart adapter (crypto pairs and stocks, REST public)."
import time
import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Any

import httpx

from app.data.providers.schemas import RawKline

_HEADERS = {"User-Agent": "Mozilla/5.0 (PIMS market data client)"}
logger = logging.getLogger(__name__)

def with_retry(
    func: Callable[..., Any],
    retries: int = 3,
    backoff_factor: float = 0.5,
    retry_codes: list[int] = [429, 500, 502, 503, 504],
) -> Any:
    """Execute function with exponential backoff on specified HTTP codes."""
    for attempt in range(retries):
        try:
            return func()
        except httpx.HTTPStatusError as e:
            if e.response.status_code in retry_codes and attempt < retries - 1:
                sleep_time = backoff_factor * (2**attempt)
                logger.warning(
                    f"Retry {attempt + 1}/{retries} for status {e.response.status_code} "
                    f"after {sleep_time}s"
                )
                time.sleep(sleep_time)
                continue
            raise e
    return func()

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
        """Backwards-compatible contract: candles only (see base.py)."""
        klines, _currency = self.fetch_klines_with_meta(instrument, timeframe, limit)
        return klines

    def fetch_klines_with_meta(
        self, instrument: str, timeframe: str, limit: int
    ) -> tuple[list[RawKline], str]:
        """Candles plus the currency the provider reported (USD for Yahoo crypto)."""
        interval, bar_seconds = self._timeframe(timeframe)
        range_needed = self._range_for(limit, bar_seconds)
        
        def _request():
            response = self._client.get(
                f"{self.base_url}/v8/finance/chart/{instrument}",
                params={"interval": interval, "range": range_needed},
                headers=_HEADERS,
                timeout=30.0,
            )
            response.raise_for_status()
            return response

        response = with_retry(_request)
        payload = response.json()
        error = payload.get("chart", {}).get("error")
        if error:
            raise RuntimeError(f"Yahoo API error: {error.get('description') or error.get('code')}")
        result = payload["chart"]["result"][0]
        meta = result.get("meta", {})
        currency = meta.get("currency", "USD")
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
                continue
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
        return klines[-limit:], currency

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
