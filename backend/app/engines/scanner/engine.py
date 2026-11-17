"Market Scanner Engine - deterministic eligibility, scoring, ranking (pure functions)."

MIN_CANDLES = 60
MIN_QUOTE_VOLUME_24H = 1_000_000.0  # USDT
MOMENTUM_WEIGHT = 0.4
TREND_WEIGHT = 0.4
LIQUIDITY_WEIGHT = 0.2


def _percentile_rank(values: list[float], value: float) -> float:
    """Deterministic percentile within the current run. Neutral 50.0 for singletons."""
    n = len(values)
    if n <= 1:
        return 50.0
    below = sum(1 for v in values if v < value)
    return below / (n - 1) * 100


def _metrics(candles: list[dict]) -> dict | None:
    if len(candles) < MIN_CANDLES:
        return None
    closes = [float(c["close"]) for c in candles]
    last = closes[-1]
    close_24h_ago = closes[-25] if len(closes) >= 25 else closes[0]
    momentum_24h = last / close_24h_ago - 1
    sma_20 = sum(closes[-20:]) / 20
    sma_50 = sum(closes[-50:]) / 50
    trend_strength = (sma_20 - sma_50) / sma_50
    quote_volume_24h = 0.0
    for c in candles[-24:]:
        qv = c.get("quote_volume")
        if qv is None and c.get("volume") is not None:
            # Yahoo provides base-asset volume only; derive quote volume.
            qv = float(c["close"]) * float(c["volume"])
        quote_volume_24h += float(qv or 0)
    return {
        "last_close": last,
        "momentum_24h": momentum_24h,
        "trend_strength": trend_strength,
        "quote_volume_24h": quote_volume_24h,
    }


def evaluate_universe(symbol_candles: dict[str, list[dict]]) -> list[dict]:
    """Evaluate all instruments, return eligible candidates scored 0-100, ranked."""
    metrics: dict[str, dict] = {}
    for symbol, candles in symbol_candles.items():
        m = _metrics(candles)
        if m is not None:
            metrics[symbol] = m

    eligible: list[str] = []
    for symbol, m in metrics.items():
        rules = {
            "MIN_CANDLES": True,
            "MIN_QUOTE_VOLUME_24H": m["quote_volume_24h"] >= MIN_QUOTE_VOLUME_24H,
        }
        if all(rules.values()):
            eligible.append(symbol)
            metrics[symbol]["matched_rules"] = rules

    momentum_values = [metrics[s]["momentum_24h"] for s in eligible]
    trend_values = [metrics[s]["trend_strength"] for s in eligible]
    liquidity_values = [metrics[s]["quote_volume_24h"] for s in eligible]

    results = []
    for symbol in eligible:
        m = metrics[symbol]
        score = (
            MOMENTUM_WEIGHT * _percentile_rank(momentum_values, m["momentum_24h"])
            + TREND_WEIGHT * _percentile_rank(trend_values, m["trend_strength"])
            + LIQUIDITY_WEIGHT * _percentile_rank(liquidity_values, m["quote_volume_24h"])
        )
        results.append(
            {
                "symbol": symbol,
                "score": round(score, 10),
                "matched_rules": m["matched_rules"],
                "metric_snapshot": {
                    "last_close": m["last_close"],
                    "momentum_24h": round(m["momentum_24h"], 10),
                    "trend_strength": round(m["trend_strength"], 10),
                    "quote_volume_24h": round(m["quote_volume_24h"], 2),
                    "weights": {
                        "momentum": MOMENTUM_WEIGHT,
                        "trend": TREND_WEIGHT,
                        "liquidity": LIQUIDITY_WEIGHT,
                    },
                },
            }
        )

    results.sort(key=lambda r: r["score"], reverse=True)
    for rank, result in enumerate(results, start=1):
        result["rank"] = rank
    return results
