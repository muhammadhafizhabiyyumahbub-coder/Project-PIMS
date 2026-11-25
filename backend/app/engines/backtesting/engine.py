"""Backtesting Engine — M4, Phase 1 (deterministic, no network).

Implements the approved Phase-1 methodology from
`docs/management/m4-gap-proposals/01-backtesting.md`:

- Strategies: BUY_HOLD (all-in at period start, hold to end) and
  STATIC_WEIGHT (rebalance to target weights on a fixed schedule).
- Cost model: per-rebalance turnover x (fee_bps + slippage_bps).
- Look-ahead bias guard: only CLOSED candles at/before the decision
  timestamp are used; an UNCLOSED candle in the window is rejected.
- Reproducibility: pure functions of (candles, config); deterministic.

Phase 2 (rule-based signals) is out of scope here and must not be
added without owner approval of the signal rules.

All formulas are PROPOSED (per the gap proposal) and use the default
parameters the owner approved as baseline: fee 10bps, slippage 5bps,
risk-free rate 0, walk-forward split 70/30.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import Asset, AnalyticsRun, BacktestMetrics
from app.engines.runner import load_candles

CALC_VERSION = "backtest.phase1.v1"

DEFAULT_FEE_BPS = 10.0
DEFAULT_SLIPPAGE_BPS = 5.0
DEFAULT_RISK_FREE = 0.0
WALKFORWARD_IN_FRACTION = 0.7

# candles per period per timeframe, used for annualization
PERIODS_PER_YEAR = {"1h": 24 * 365, "1d": 365, "1m": 12}


@dataclass
class Series:
    """One asset's price series over the backtest window (CLOSED candles only)."""
    symbol: str
    asset_id: object
    closes: list[float] = field(default_factory=list)
    close_times: list[datetime] = field(default_factory=list)


class InsufficientData(Exception):
    """Raised when an asset lacks enough CLOSED candles for the backtest."""


def _per_period_equity(curve: list[float]) -> list[float]:
    """Per-period simple returns from an equity curve (curve[0] is base 1.0)."""
    rets: list[float] = []
    for i in range(1, len(curve)):
        prev = curve[i - 1]
        rets.append((curve[i] - prev) / prev if prev else 0.0)
    return rets


def _simple_returns(closes: list[float]) -> list[float]:
    """Period-over-period simple returns; first element is None (no prior)."""
    rets: list[Optional[float]] = [None]
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        rets.append((closes[i] - prev) / prev if prev else 0.0)
    return rets


def _collect_series(
    session: Session,
    asset: Asset,
    timeframe: str,
    limit: int,
    require_closed: bool = True,
) -> Series:
    """Load CLOSED candles for one asset and build a deterministic series.

    Look-ahead guard: if the most recent candle is UNCLOSED, it is excluded
    (its close price is not final). Raises InsufficientData when fewer than
    MIN candles remain after filtering.
    """
    MIN = 3
    candles = load_candles(session, asset.id, timeframe, limit=limit)
    closes: list[float] = []
    close_times: list[datetime] = []
    for c in candles:
        if require_closed and c.get("candle_status") == "UNCLOSED":
            # Never back a decision on a price that is still moving.
            continue
        closes.append(float(c["close"]))
        close_times.append(c["close_time"])
    if len(closes) < MIN:
        raise InsufficientData(
            f"{asset.symbol}: {len(closes)} CLOSED candles < {MIN}"
        )
    return Series(symbol=asset.symbol, asset_id=asset.id,
                  closes=closes, close_times=close_times)


def _annualize(factor_periods: int) -> float:
    return float(PERIODS_PER_YEAR.get(factor_periods, 365))


def compute_buy_hold(series: Series) -> dict:
    """All-in at first close, hold to last close. No rebalance => no costs."""
    if len(series.closes) < 2:
        raise InsufficientData(f"{series.symbol}: need >= 2 candles")
    start = series.closes[0]
    end = series.closes[-1]
    total_return = (end - start) / start if start else 0.0

    # annualized (geometric) using period count
    n_periods = len(series.closes) - 1
    ann = None
    if start and end and start > 0 and end > 0 and n_periods > 0:
        ann = (end / start) ** (1 / n_periods) - 1

    # volatility + sharpe from simple returns
    rets = _simple_returns(series.closes)[1:]
    vol, sharpe, max_dd = _risk_metrics(rets)

    return {
        "strategy": "BUY_HOLD",
        "total_return": total_return,
        "annual_return": ann,
        "volatility": vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "win_rate": _win_rate(rets),
        "turnover": 0.0,  # single entry, no rebalance
        "cost": 0.0,
        "cost_adjusted_return": total_return,
        "periods": n_periods,
        "start_price": start,
        "end_price": end,
    }


def compute_static_weight(
    series_map: dict[str, Series],
    weights: dict[str, float],
    rebalance_every: int,
    fee_bps: float = DEFAULT_FEE_BPS,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> dict:
    """Rebalance the basket to target weights every `rebalance_every` periods.

    Single source of truth for the equity curve: `equity_curve_series`.
    Costs accrue on turnover at each scheduled rebalance.
    """
    if not weights:
        raise InsufficientData("no weights supplied")
    # Guard: every weight key must have a series (unknown symbol -> clean error,
    # not a KeyError mid-calculation).
    unknown = [k for k in weights if k not in series_map]
    if unknown:
        raise InsufficientData(f"weights reference unknown symbols: {unknown}")
    total_w = sum(abs(w) for w in weights.values())
    if total_w <= 0:
        raise InsufficientData("weights sum to zero")
    target = {k: v / total_w for k, v in weights.items()}

    min_len = min(len(s.closes) for s in series_map.values())
    if min_len < 2:
        raise InsufficientData("need >= 2 common periods")

    curve = equity_curve_series(series_map, target, min_len, rebalance_every,
                                fee_bps, slippage_bps)
    per_period = _per_period_equity(curve)
    n_periods = len(per_period)

    # aggregate turnover/cost across all rebalances (recompute for the report)
    total_turnover, total_cost = _aggregate_costs(series_map, target, min_len,
                                                   rebalance_every, fee_bps, slippage_bps)

    vol, sharpe, max_dd = _risk_metrics(per_period, n_periods)
    total_return = curve[-1] - 1.0

    # annualized (geometric) return over the observation window
    ann = None
    if n_periods > 0 and curve[0] > 0 and curve[-1] > 0:
        ann = (curve[-1] / curve[0]) ** (1 / n_periods) - 1

    return {
        "strategy": "STATIC_WEIGHT",
        "total_return": total_return,
        "annual_return": ann,
        "volatility": vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "win_rate": _win_rate(per_period),
        "turnover": total_turnover,
        "cost": total_cost,
        "cost_adjusted_return": total_return,  # equity curve is net of costs
        "periods": n_periods,
        "rebalance_every": rebalance_every,
        "fee_bps": fee_bps,
        "slippage_bps": slippage_bps,
        "weights": {k: round(v, 6) for k, v in target.items()},
    }


def _aggregate_costs(series_map, target, min_len, rebalance_every, fee_bps, slippage_bps):
    """Sum turnover + cost across every scheduled rebalance (report only)."""
    cost_rate = (fee_bps + slippage_bps) / 10_000.0
    curve = [1.0]
    holdings = {sym: target[sym] for sym in target}
    last_rebalance = 0
    total_turnover = 0.0
    total_cost = 0.0
    for t in range(1, min_len):
        total = 0.0
        for sym, w in holdings.items():
            s = series_map[sym]
            prev = s.closes[t - 1]
            holdings[sym] = w * ((s.closes[t] - prev) / prev if prev else 1.0)
            total += holdings[sym]
        if t - last_rebalance >= rebalance_every:
            turnover = sum(
                abs(target[sym] - (holdings[sym] / total if total else 0.0))
                for sym in target
            )
            cost = turnover * cost_rate * total
            total_cost += cost
            total_turnover += turnover
            last_rebalance = t
            holdings = {sym: target[sym] for sym in target}
        curve.append(total)
    return total_turnover, total_cost


def equity_curve_series(series_map, target, min_len, rebalance_every, fee_bps, slippage_bps):
    """Exact equity curve (net of rebalance costs) for risk metrics.

    Recomputed cleanly (the inline loop in compute_static_weight is replaced
    by this single source of truth to avoid double-booking costs).
    """
    cost_rate = (fee_bps + slippage_bps) / 10_000.0
    curve = [1.0]
    last_rebalance = 0
    # track current holdings value per asset (in equity units)
    holdings = {sym: target[sym] for sym in target}
    for t in range(1, min_len):
        total = 0.0
        for sym, w in holdings.items():
            s = series_map[sym]
            prev = s.closes[t - 1]
            period_mult = (s.closes[t] - prev) / prev if prev else 1.0
            holdings[sym] = w * period_mult
            total += holdings[sym]
        if t - last_rebalance >= rebalance_every:
            turnover = sum(
                abs(target[sym] - holdings[sym] / total if total else 0.0)
                for sym in target
            )
            cost = turnover * cost_rate * total
            total = total - cost
            # renormalize holdings to target after charging cost
            scale = 1.0
            for sym in target:
                holdings[sym] = target[sym]
            last_rebalance = t
        curve.append(total)
    return curve


def _risk_metrics(rets: list[float], periods: Optional[int] = None) -> tuple[Optional[float], Optional[float], Optional[float]]:
    """(volatility, sharpe, max_drawdown) over period returns.

    `periods` is the annualizing divisor hint; volatility is annualized by
    sqrt of periods-per-year when `periods` is given, else left raw.
    Returns None for any metric that cannot be computed (insufficient data).
    """
    clean = [r for r in rets if r is not None]
    if len(clean) < 2:
        return None, None, None
    mean = sum(clean) / len(clean)
    var = sum((r - mean) ** 2 for r in clean) / (len(clean) - 1)
    vol = var ** 0.5
    # annualize
    if periods is not None and periods > 0:
        ann_vol = vol * (periods ** 0.5)
    else:
        ann_vol = vol
    sharpe = (mean * periods if periods else mean) / ann_vol if ann_vol else None
    # max drawdown on cumulative equity
    eq = 1.0
    peak = 1.0
    max_dd = 0.0
    for r in clean:
        eq *= (1 + r)
        peak = max(peak, eq)
        dd = (peak - eq) / peak if peak else 0.0
        max_dd = max(max_dd, dd)
    return ann_vol, sharpe, max_dd


def _win_rate(rets: list[float]) -> Optional[float]:
    clean = [r for r in rets if r is not None]
    if not clean:
        return None
    wins = sum(1 for r in clean if r > 0)
    return wins / len(clean)


def walk_forward_split(n_periods: int) -> tuple[int, int]:
    """(in_sample, out_of_sample) period counts at the 70/30 owner default.

    `oos` is derived (n - ins) so the split always sums to n; with n=1 the
    single period is in-sample and out-of-sample is 0.
    """
    if n_periods <= 0:
        return 0, 0
    ins = int(n_periods * WALKFORWARD_IN_FRACTION)
    ins = max(min(ins, n_periods - 1), 1)  # keep >=1 in, >=0 out
    oos = n_periods - ins
    return ins, oos


def run_backtest_for_assets(
    session: Session,
    assets: list[Asset],
    weights: dict[str, float],
    strategy: str = "STATIC_WEIGHT",
    timeframe: str = "1d",
    limit: int = 300,
    rebalance_every: int = 21,
    fee_bps: float = DEFAULT_FEE_BPS,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
    risk_free: float = DEFAULT_RISK_FREE,
) -> dict:
    """Execute a Phase-1 backtest and persist to analytics_runs + backtest_metrics.

    `weights` keys are asset symbols. For BUY_HOLD, weights are ignored
    (all-in on the single asset, or equal if multiple).
    """
    series_map: dict[str, Series] = {}
    for asset in assets:
        s = _collect_series(session, asset, timeframe, limit)
        series_map[s.symbol] = s

    if strategy == "BUY_HOLD":
        # single-asset backtest (or equal-weight basket via static)
        if len(series_map) == 1:
            only = next(iter(series_map.values()))
            raw = compute_buy_hold(only)
        else:
            # multiple assets with BUY_HOLD -> treat as static equal weight
            eq_w = {sym: 1.0 / len(series_map) for sym in series_map}
            raw = compute_static_weight(series_map, eq_w, rebalance_every,
                                        fee_bps, slippage_bps)
    elif strategy == "STATIC_WEIGHT":
        missing = [k for k in weights if k not in series_map]
        if missing:
            raise InsufficientData(f"weights reference unknown symbols: {missing}")
        raw = compute_static_weight(series_map, weights, rebalance_every,
                                    fee_bps, slippage_bps)
    else:
        raise ValueError(f"unsupported strategy {strategy!r} in Phase 1")

    # walk-forward annotation (deterministic split of the observation window)
    n_periods = raw.get("periods", 0)
    ins, oos = walk_forward_split(n_periods) if n_periods else (0, 0)

    # persist under an analytics run
    now = datetime.now(timezone.utc)
    run = AnalyticsRun(
        engine_type="BACKTESTING",
        asset_id=assets[0].id if len(assets) == 1 else None,
        timeframe=timeframe,
        observation_start=series_map[next(iter(series_map))].close_times[0],
        observation_end=series_map[next(iter(series_map))].close_times[-1],
        calculation_version=CALC_VERSION,
        input_metadata={
            "strategy": strategy,
            "weights": weights,
            "rebalance_every": rebalance_every,
            "fee_bps": fee_bps,
            "slippage_bps": slippage_bps,
            "risk_free": risk_free,
            "n_periods": n_periods,
            "walkforward_in": ins,
            "walkforward_oos": oos,
        },
        execution_status="COMPLETED",
        started_at=now,
        completed_at=now,
    )
    session.add(run)
    session.flush()

    metric_rows = []
    for key in ("total_return", "annual_return", "volatility", "sharpe",
                "max_drawdown", "win_rate", "turnover", "cost"):
        val = raw.get(key)
        # Guard: backtest metrics must fit Numeric(30,12) (|x| < 1e18).
        # Compound annualization over many 1h periods can produce inf/huge
        # values (or None) -> store None rather than overflow the column.
        import math as _math
        if isinstance(val, float) and (_math.isinf(val) or _math.isnan(val) or abs(val) >= 1e15):
            val = None
        session.add(BacktestMetrics(
            analytics_run_id=run.id,
            metric=key,
            value=float(val) if val is not None else None,
            detail={"strategy": strategy},
        ))
        metric_rows.append((key, val))

    session.flush()
    return {
        "run_id": str(run.id),
        "strategy": strategy,
        "calculation_status": "COMPLETED",
        "metrics": {k: v for k, v in raw.items()},
        "walkforward": {"in_sample_periods": ins, "out_of_sample_periods": oos},
        "calculation_version": CALC_VERSION,
        "observation_start": raw and series_map[next(iter(series_map))].close_times[0].isoformat(),
        "observation_end": series_map[next(iter(series_map))].close_times[-1].isoformat(),
    }
