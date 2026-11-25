"""Correlation engine: pairwise Pearson correlation over portfolio holdings.

Implements `specifications/engines/correlation-engine-spec.md`:
- §4.2  Pearson formula  rho = Cov(X,Y) / (sigma_X * sigma_Y)
- §5.1  Simple returns    R_t = (P_t - P_{t-1}) / P_{t-1}
- §5.2  Log returns       r_t = ln(P_t / P_{t-1})
- §5.3  Return method must be consistent within one run and recorded in metadata.
- §6    Timestamp alignment: common-observation alignment (only timestamps present
         in BOTH return series participate).
- §2.2-E Rolling correlation over a moving observation window.

Deterministic only: reads stored candles (no provider calls, no network).
Does not invent methodology beyond the spec.
"""
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.database.models import Asset
from app.engines.runner import load_candles

MIN_OBSERVATIONS = 2  # need >=2 paired observations for a correlation


@dataclass
class AssetSeries:
    asset_id: object
    symbol: str
    closes: list[float] = field(default_factory=list)
    timestamps: list[datetime] = field(default_factory=list)


def _returns(closes: list[float], method: str) -> list[Optional[float]]:
    """Return series aligned to closes (index i uses P_i and P_{i-1})."""
    out: list[Optional[float]] = [None]
    for i in range(1, len(closes)):
        prev, cur = closes[i - 1], closes[i]
        if prev == 0:
            out.append(None)
            continue
        if method == "LOG":
            if prev <= 0 or cur <= 0:
                out.append(None)
                continue
            out.append(math.log(cur / prev))
        else:  # SIMPLE
            out.append((cur - prev) / prev)
    return out


def _pearson(xs: list[float], ys: list[float]) -> Optional[float]:
    """Pearson correlation (spec §4.2). None if fewer than 2 points or zero variance."""
    n = len(xs)
    if n < MIN_OBSERVATIONS:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = sum((x - mean_x) ** 2 for x in xs)
    den_y = sum((y - mean_y) ** 2 for y in ys)
    den = math.sqrt(den_x * den_y)
    if den == 0:
        return None
    rho = num / den
    # clamp to [-1, 1] (float tolerance)
    return max(-1.0, min(1.0, rho))


def _bucket(ts, timeframe: str = "1h"):
    """Round a timestamp down to the start of its candle bucket so that two
    assets' candles for the same period align even when their exact
    timestamps differ by sub-period offsets (spec §6 common alignment,
    tolerant form). Returns None for None ts."""
    if ts is None:
        return None
    if timeframe == "1d":
        step = timedelta(days=1)
    elif timeframe == "1m":
        step = timedelta(minutes=1)
    else:
        step = timedelta(hours=1)
    epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    ts_utc = ts.astimezone(timezone.utc)
    secs = int((ts_utc - epoch).total_seconds())
    step_secs = int(step.total_seconds())
    return epoch + timedelta(seconds=(secs // step_secs) * step_secs)


def _align_common(series_a: AssetSeries, series_b: AssetSeries,
                  ret_method: str, timeframe: str = "1h") -> tuple[list[float], list[float]]:
    """Common-observation alignment: pair returns only where both assets have a
    non-None return at the same (bucketed) close period (spec §6).
    Returns parallel lists of (return_a, return_b)."""
    rets_a = _returns(series_a.closes, ret_method)
    rets_b = _returns(series_b.closes, ret_method)
    # Build bucket->return maps (last occurrence wins per bucket)
    map_a: dict = {}
    for ts, r in zip(series_a.timestamps, rets_a):
        if r is not None:
            b = _bucket(ts, timeframe)
            if b is not None:
                map_a[b] = r
    map_b: dict = {}
    for ts, r in zip(series_b.timestamps, rets_b):
        if r is not None:
            b = _bucket(ts, timeframe)
            if b is not None:
                map_b[b] = r
    common = sorted(set(map_a) & set(map_b))
    xs = [map_a[t] for t in common]
    ys = [map_b[t] for t in common]
    return xs, ys


def rolling_correlation(xs: list[float], ys: list[float], window: int) -> list[Optional[float]]:
    """Rolling Pearson over a moving window (spec §2.2-E).
    Returns one value per window position (len = len(xs) - window + 1),
    or [] if data insufficient."""
    if window < MIN_OBSERVATIONS or len(xs) < window or len(xs) != len(ys):
        return []
    out: list[Optional[float]] = []
    for i in range(0, len(xs) - window + 1):
        out.append(_pearson(xs[i:i + window], ys[i:i + window]))
    return out


def compute_pair(series_a: AssetSeries, series_b: AssetSeries,
                ret_method: str = "SIMPLE",
                rolling_window: int = 0,
                timeframe: str = "1h") -> dict:
    """Compute one asset pair: overall + optional rolling correlation."""
    xs, ys = _align_common(series_a, series_b, ret_method, timeframe)
    overall = _pearson(xs, ys)
    result: dict = {
        "asset_a_symbol": series_a.symbol,
        "asset_b_symbol": series_b.symbol,
        "observation_count": len(xs),
        "correlation": overall,
        "return_method": ret_method,
        "calculation_status": "COMPLETED" if overall is not None else "INSUFFICIENT_DATA",
    }
    if overall is None:
        result["reason"] = f"fewer than {MIN_OBSERVATIONS} common observations"
    if rolling_window > 0 and overall is not None:
        rolls = rolling_correlation(xs, ys, rolling_window)
        result["rolling"] = [None if r is None else round(r, 10) for r in rolls]
        result["rolling_window"] = rolling_window
    return result


def build_series(session, asset: Asset, timeframe: str, limit: int = 300) -> AssetSeries:
    """Load closes + timestamps for one asset (deterministic, stored candles)."""
    candles = load_candles(session, asset.id, timeframe, limit=limit)
    closes = [c["close"] for c in candles]
    # timestamps aligned to closes (use close_time, fallback open_time)
    ts = [c.get("close_time") or c.get("open_time") for c in candles]
    ts_typed: list[datetime] = [t for t in ts if t is not None]
    return AssetSeries(asset_id=asset.id, symbol=asset.symbol,
                       closes=closes[: len(ts_typed)] if all(t is not None for t in ts) else closes,
                       timestamps=ts_typed)


def correlation_matrix(series_list: list[AssetSeries],
                       ret_method: str = "SIMPLE",
                       rolling_window: int = 0,
                       timeframe: str = "1h") -> list[dict]:
    """All pairwise correlations (i<j). Deterministic, no network."""
    results: list[dict] = []
    for i in range(len(series_list)):
        for j in range(i + 1, len(series_list)):
            results.append(compute_pair(series_list[i], series_list[j],
                                       ret_method=ret_method,
                                       rolling_window=rolling_window,
                                       timeframe=timeframe))
    return results


def run_correlation_for_portfolio(
    session,
    portfolio_id,
    holdings: list,
    timeframe: str = "1d",
    ret_method: str = "SIMPLE",
    rolling_window: int = 0,
    limit: int = 300,
) -> dict:
    """Compute + persist pairwise correlation for a portfolio's holdings.

    Returns a structured result dict (correlation_matrix + status). Persists to
    `analytics_runs` (engine_type CORRELATION) + `correlation_results` following
    the runner.py pattern. Raises on DB error (caller handles).
    """
    from app.database.models import AnalyticsRun, CorrelationResult
    from app.engines.runner import CALCULATION_VERSION

    now = datetime.now(timezone.utc)
    run = AnalyticsRun(
        engine_type="CORRELATION",
        asset_id=None,
        timeframe=timeframe,
        calculation_version=CALCULATION_VERSION,
        input_metadata={
            "portfolio_id": str(portfolio_id),
            "return_method": ret_method,
            "rolling_window": rolling_window,
            "holding_count": len(holdings),
        },
        execution_status="RUNNING",
        started_at=now,
    )
    session.add(run)
    session.flush()

    # Build series per holding (dedupe asset ids)
    seen: set = set()
    series: list[AssetSeries] = []
    for h in holdings:
        if h.asset_id in seen:
            continue
        seen.add(h.asset_id)
        asset = session.get(Asset, h.asset_id)
        if asset is None:
            continue
        s = build_series(session, asset, timeframe, limit=limit)
        if len(s.closes) > 1:
            series.append(s)

    matrix = correlation_matrix(series, ret_method=ret_method,
                                rolling_window=rolling_window,
                                timeframe=timeframe)

    # Persist each pair
    for pair in matrix:
        a = next((s for s in series if s.symbol == pair["asset_a_symbol"]), None)
        b = next((s for s in series if s.symbol == pair["asset_b_symbol"]), None)
        if a is None or b is None or pair["correlation"] is None:
            continue
        # consistent ordering: asset_a_id < asset_b_id (spec §7.5 constraint)
        if str(a.asset_id) > str(b.asset_id):
            a, b = b, a
        session.add(CorrelationResult(
            analytics_run_id=run.id,
            asset_a_id=a.asset_id,
            asset_b_id=b.asset_id,
            correlation_value=pair["correlation"],
            observation_count=pair["observation_count"],
            observation_period=timeframe,
            calculation_method=f"pearson:{ret_method.lower()}",
            result_metadata={
                "return_method": ret_method,
                "rolling_window": rolling_window,
                "rolling": pair.get("rolling"),
            },
        ))

    completed = sum(1 for p in matrix if p["correlation"] is not None)
    run.execution_status = "COMPLETED" if completed > 0 else "INSUFFICIENT_DATA"
    run.completed_at = now
    session.flush()

    return {
        "portfolio_id": str(portfolio_id),
        "timeframe": timeframe,
        "return_method": ret_method,
        "calculation_status": run.execution_status,
        "calculation_version": CALCULATION_VERSION,
        "correlation_matrix": [
            {
                "asset_a": p["asset_a_symbol"],
                "asset_b": p["asset_b_symbol"],
                "correlation": p["correlation"],
                "observation_count": p["observation_count"],
                "rolling": p.get("rolling"),
                "status": p["calculation_status"],
            }
            for p in matrix
        ],
        "pairs_computed": completed,
        "series_used": len(series),
        "analytics_run_id": str(run.id),
    }
