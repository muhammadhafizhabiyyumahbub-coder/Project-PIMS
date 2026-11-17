"Market Regime Engine - rule-based classification (pure functions)."

TREND_BULLISH = "BULLISH"
TREND_BEARISH = "BEARISH"
TREND_SIDEWAYS = "SIDEWAYS"
VOL_HIGH = "HIGH"
VOL_NORMAL = "NORMAL"
VOL_LOW = "LOW"
MOM_BULLISH = "BULLISH"
MOM_BEARISH = "BEARISH"
MOM_NEUTRAL = "NEUTRAL"

# Documented deterministic thresholds for crypto spot, 1h candles.
VOLATILITY_HIGH_THRESHOLD = 0.03  # ATR14 / close
VOLATILITY_LOW_THRESHOLD = 0.01
MOMENTUM_RSI_HIGH = 55.0
MOMENTUM_RSI_LOW = 45.0


def classify(sma_20: float, sma_50: float, last_close: float, rsi_14: float, atr_14: float) -> dict:
    atr_pct = atr_14 / last_close
    if sma_20 > sma_50 and last_close > sma_20:
        trend = TREND_BULLISH
    elif sma_20 < sma_50 and last_close < sma_20:
        trend = TREND_BEARISH
    else:
        trend = TREND_SIDEWAYS

    if atr_pct > VOLATILITY_HIGH_THRESHOLD:
        volatility = VOL_HIGH
    elif atr_pct < VOLATILITY_LOW_THRESHOLD:
        volatility = VOL_LOW
    else:
        volatility = VOL_NORMAL

    if rsi_14 > MOMENTUM_RSI_HIGH:
        momentum = MOM_BULLISH
    elif rsi_14 < MOMENTUM_RSI_LOW:
        momentum = MOM_BEARISH
    else:
        momentum = MOM_NEUTRAL

    # Trend strength heuristic: relative SMA separation as percentage, capped at 100.
    confidence = min(abs(sma_20 - sma_50) / sma_50 * 100 * 10, 100.0)

    return {
        "trend_regime": trend,
        "volatility_regime": volatility,
        "momentum_regime": momentum,
        "confidence_score": round(confidence, 2),
        "atr_pct": round(atr_pct, 6),
    }
