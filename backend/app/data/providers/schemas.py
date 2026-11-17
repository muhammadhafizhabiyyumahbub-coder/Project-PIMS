"Typed raw data payloads returned by provider adapters."
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class RawKline:
    """Raw provider candle before normalization/validation.

    `open_time`/`close_time` may be naive; normalization layer converts to UTC.
    """

    open_time: datetime
    close_time: datetime
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    volume: float | None
    quote_volume: float | None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
