"Technical Analysis Engine - deterministic indicators (pure functions)."
from datetime import datetime


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    gains, losses = 0.0, 0.0
    for i in range(-period, 0):
        diff = closes[i] - closes[i - 1]
        gains += max(diff, 0)
        losses += max(-diff, 0)
    if losses == 0:
        return 100.0
    rs = (gains / period) / (losses / period)
    return 100 - (100 / (1 + rs))


def atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(-period, 0):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1]),
        )
        trs.append(tr)
    return sum(trs) / period


def ema(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    multiplier = 2 / (period + 1)
    ema_value = sum(values[:period]) / period
    for value in values[period:]:
        ema_value = (value - ema_value) * multiplier + ema_value
    return ema_value


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict | None:
    if len(closes) < slow + signal:
        return None
    macd_line = ema(closes, fast) - ema(closes, slow)
    # Signal EMA computed over the MACD line history requires full series;
    # for the current observation a proxy on the close series is avoided by
    # computing the MACD line series explicitly.
    macd_series: list[float] = []
    for i in range(slow - 1, len(closes)):
        window = closes[: i + 1]
        macd_series.append(ema(window, fast) - ema(window, slow))
    signal_line = ema(macd_series, signal)
    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": macd_line - signal_line,
    }


def compute(candles: list[dict], observation_time: datetime) -> dict:
    """Compute all indicators for the slice. candles: oldest-first dicts with
    open_time/close_time/open/high/low/close/volume keys."""
    if len(candles) < 60:
        return {"calculation_status": "FAILED", "error": "insufficient candles (<60)"}
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    sma_20 = sma(closes, 20)
    sma_50 = sma(closes, 50)
    rsi_14 = rsi(closes)
    atr_14 = atr(highs, lows, closes)
    macd_out = macd(closes)
    values = {
        "sma_20": sma_20,
        "sma_50": sma_50,
        "rsi_14": rsi_14,
        "atr_14": atr_14,
        "macd": macd_out,
        "last_close": closes[-1],
    }
    if any(v is None for v in [sma_20, sma_50, rsi_14, atr_14, macd_out]):
        return {"calculation_status": "FAILED", "error": "indicator window too short"}
    return {
        "calculation_status": "COMPLETED",
        "observation_time": observation_time,
        "parameters": {"sma": 20, "sma_slow": 50, "rsi": 14, "atr": 14, "macd": [12, 26, 9]},
        "values": values,
    }
