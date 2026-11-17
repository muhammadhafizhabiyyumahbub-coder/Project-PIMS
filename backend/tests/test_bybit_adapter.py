"Seam 5: Bybit adapter normalization with mocked HTTP, and normalization validation."
from datetime import datetime, timezone

import httpx
import pytest

from app.data.normalization.normalize import NormalizationError, normalize_kline
from app.data.providers.crypto.bybit import TIMEFRAME_TO_BYBIT_INTERVAL, BybitProvider
from app.data.providers.schemas import RawKline

HOURLY_MS = 3600_000


def bybit_payload(rows):
    """rows: list of [start_ms, o, h, l, c, volume, turnover], oldest-first."""
    return {"retCode": 0, "retMsg": "OK", "result": {"list": list(reversed(rows))}}


def make_transport(payload, captured: dict):
    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


def test_fetch_klines_normalizes_and_orders_oldest_first():
    rows = [
        [1000 * HOURLY_MS, "100", "110", "95", "105", "10", "1050"],
        [1001 * HOURLY_MS, "105", "120", "104", "118", "12", "1340"],
    ]
    captured = {}
    provider = BybitProvider(transport=make_transport(bybit_payload(rows), captured))
    klines = provider.fetch_klines("BTCUSDT", "1h", 2)

    assert captured["url"].startswith("https://api.bybit.com/v5/market/kline")
    assert "symbol=BTCUSDT" in captured["url"]
    assert "interval=60" in captured["url"]
    assert len(klines) == 2
    # oldest-first output despite newest-first provider payload
    assert klines[0].open_time == datetime.fromtimestamp(1000 * HOURLY_MS / 1000, tz=timezone.utc)
    assert klines[0].close_time == klines[0].open_time + __import__("datetime").timedelta(hours=1)
    assert klines[0].close_price == 105.0
    assert klines[1].high_price == 120.0
    assert klines[1].quote_volume == 1340.0


def test_bybit_error_raised():
    captured = {}
    payload = {"retCode": 10001, "retMsg": "params error", "result": {"list": []}}
    provider = BybitProvider(transport=make_transport(payload, captured))
    with pytest.raises(RuntimeError, match="params error"):
        provider.fetch_klines("BAD", "1h", 2)


def test_unsupported_timeframe_rejected():
    provider = BybitProvider(transport=make_transport(bybit_payload([]), {}))
    with pytest.raises(ValueError, match="Unsupported timeframe"):
        provider.fetch_klines("BTCUSDT", "37m", 2)
    assert TIMEFRAME_TO_BYBIT_INTERVAL["1h"] == "60"


def test_normalization_rejects_inconsistent_ohlc():
    base = {
        "open_time": datetime(2026, 1, 1, tzinfo=timezone.utc),
        "close_time": datetime(2026, 1, 1, 1, tzinfo=timezone.utc),
        "open_price": 100.0,
        "high_price": 110.0,
        "low_price": 95.0,
        "close_price": 105.0,
        "volume": 10.0,
        "quote_volume": 1050.0,
    }
    assert normalize_kline(RawKline(**base))["open_price"] == 100.0

    bad_high = base | {"high_price": 90.0}
    with pytest.raises(NormalizationError, match="inconsistent OHLC"):
        normalize_kline(RawKline(**bad_high))

    negative = base | {"volume": -1.0}
    with pytest.raises(NormalizationError, match="negative volume"):
        normalize_kline(RawKline(**negative))

    zero = base | {"close_price": 0.0}
    with pytest.raises(NormalizationError, match="positive"):
        normalize_kline(RawKline(**zero))
