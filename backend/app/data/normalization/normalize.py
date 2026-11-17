"Convert raw provider payloads into normalized, validated internal records."
from datetime import datetime, timezone
from typing import Any

from app.data.providers.schemas import RawKline


class NormalizationError(ValueError):
    """Raw payload failed OHLCV validation."""


def utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def validate_kline(raw: RawKline) -> RawKline:
    """OHLCV sanity checks. Raises NormalizationError on invalid candles."""
    o, h, l, c = raw.open_price, raw.high_price, raw.low_price, raw.close_price
    if min(o, h, l, c) <= 0:
        raise NormalizationError("prices must be positive")
    if h < max(o, c) or l > min(o, c) or h < l:
        raise NormalizationError("inconsistent OHLC relationships")
    if raw.volume is not None and raw.volume < 0:
        raise NormalizationError("negative volume")
    return raw


def normalize_kline(raw: RawKline) -> dict[str, Any]:
    """Normalized candle dict for persistence, timestamps in UTC."""
    validate_kline(raw)
    return {
        "open_time": utc(raw.open_time),
        "close_time": utc(raw.close_time),
        "open_price": raw.open_price,
        "high_price": raw.high_price,
        "low_price": raw.low_price,
        "close_price": raw.close_price,
        "volume": raw.volume,
        "quote_volume": raw.quote_volume,
        "candle_status": "CLOSED",
    }
