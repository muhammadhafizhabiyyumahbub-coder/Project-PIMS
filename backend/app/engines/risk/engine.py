"Risk Engine - volatility and drawdown metrics (pure functions)."
import math

RISK_HIGH_VOL_THRESHOLD = 0.60  # annualized
RISK_MODERATE_VOL_THRESHOLD = 0.30


def annualized_volatility(closes: list[float]) -> float | None:
    """Std of hourly log returns, annualized for 24/7 crypto markets (8760h)."""
    if len(closes) < 2:
        return None
    returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes))]
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    return math.sqrt(variance) * math.sqrt(8760)


def max_drawdown(closes: list[float]) -> float | None:
    if len(closes) < 2:
        return None
    peak = closes[0]
    max_dd = 0.0
    for price in closes:
        peak = max(peak, price)
        max_dd = max(max_dd, (peak - price) / peak)
    return max_dd


def classify(volatility: float) -> str:
    if volatility > RISK_HIGH_VOL_THRESHOLD:
        return "HIGH"
    if volatility > RISK_MODERATE_VOL_THRESHOLD:
        return "MODERATE"
    return "LOW"


def compute(candles: list[dict]) -> dict:
    if len(candles) < 60:
        return {"calculation_status": "FAILED", "error": "insufficient candles (<60)"}
    closes = [float(c["close"]) for c in candles]
    volatility = annualized_volatility(closes)
    drawdown = max_drawdown(closes)
    if volatility is None or drawdown is None:
        return {"calculation_status": "FAILED", "error": "metric computation failed"}
    return {
        "calculation_status": "COMPLETED",
        "volatility": round(volatility, 10),
        "max_drawdown": round(drawdown, 10),
        "risk_classification": classify(volatility),
    }
