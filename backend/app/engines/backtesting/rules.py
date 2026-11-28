"""Backtesting Engine — M4 Phase 2 (rule-based, deterministic, no network).

Owner-approved rule strategies (gap proposal §2 Option B):

- MA_CROSSOVER: long while SMA(fast) > SMA(slow); flat otherwise.
- RSI_THRESHOLD: enter when RSI(period) < oversold; exit when RSI > overbought.
- MOMENTUM: enter when the trailing `period` return > threshold; flat otherwise.

Look-ahead guard: the signal at close[t] decides the position held over the
interval (t, t+1], so no future candle ever backs a decision. Costs are
`|position change| x (fee_bps + slippage_bps)` charged at the change.

All outputs are pure functions of (closes, strategy, config) -> reproducible.
"""
from typing import Optional

from app.engines.backtesting.engine import (
    DEFAULT_FEE_BPS,
    DEFAULT_SLIPPAGE_BPS,
    InsufficientData,
    Series,
    _risk_metrics,
)

RULE_STRATEGIES = ("MA_CROSSOVER", "RSI_THRESHOLD", "MOMENTUM")

DEFAULT_MA_FAST = 10
DEFAULT_MA_SLOW = 30
DEFAULT_RSI_PERIOD = 14
DEFAULT_RSI_OVERSOLD = 30.0
DEFAULT_RSI_OVERBOUGHT = 70.0
DEFAULT_MOMENTUM_PERIOD = 20
DEFAULT_MOMENTUM_THRESHOLD = 0.0


def _signal_ma(closes: list[float], fast: int, slow: int) -> list[float]:
    n = len(closes)
    pos = [0.0] * n
    for t in range(n):
        if t + 1 < slow:
            continue
        f = sum(closes[t - fast + 1:t + 1]) / fast
        s = sum(closes[t - slow + 1:t + 1]) / slow
        pos[t] = 1.0 if f > s else 0.0
    return pos


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)


def _rsi(closes: list[float], period: int) -> list[Optional[float]]:
    """Wilder-smoothed RSI, aligned to `closes` (None before the first value)."""
    n = len(closes)
    out: list[Optional[float]] = [None] * n
    if n < period + 1:
        return out
    gain = 0.0
    loss = 0.0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        gain += d if d > 0 else 0.0
        loss += -d if d < 0 else 0.0
    avg_gain = gain / period
    avg_loss = loss / period
    out[period] = _rsi_value(avg_gain, avg_loss)
    for i in range(period + 1, n):
        d = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + (d if d > 0 else 0.0)) / period
        avg_loss = (avg_loss * (period - 1) + (-d if d < 0 else 0.0)) / period
        out[i] = _rsi_value(avg_gain, avg_loss)
    return out


def _signal_rsi(closes: list[float], period: int, oversold: float,
                overbought: float) -> list[float]:
    rsis = _rsi(closes, period)
    pos = [0.0] * len(closes)
    held = 0.0
    for t, r in enumerate(rsis):
        if r is not None:
            if held == 0.0 and r < oversold:
                held = 1.0
            elif held == 1.0 and r > overbought:
                held = 0.0
        pos[t] = held
    return pos


def _signal_momentum(closes: list[float], period: int, threshold: float) -> list[float]:
    pos = [0.0] * len(closes)
    for t in range(len(closes)):
        if t < period:
            continue
        base = closes[t - period]
        mom = (closes[t] - base) / base if base else 0.0
        pos[t] = 1.0 if mom > threshold else 0.0
    return pos


def _simulate(closes: list[float], positions: list[float], fee_bps: float,
              slippage_bps: float):
    """Run the position series -> (equity, turnover, cost, period_rets, trades)."""
    rate = (fee_bps + slippage_bps) / 10_000.0
    equity = 1.0
    turnover = 0.0
    cost_total = 0.0
    period_rets: list[float] = []
    trades: list[float] = []
    entry_equity: Optional[float] = None
    for t in range(1, len(closes)):
        prev = closes[t - 1]
        held = positions[t - 1]
        r = held * ((closes[t] - prev) / prev) if prev else 0.0
        period_rets.append(r)
        equity *= (1.0 + r)
        if positions[t] != positions[t - 1]:
            delta = abs(positions[t] - positions[t - 1])
            turnover += delta
            cost = delta * rate * equity
            equity -= cost
            cost_total += cost
            if positions[t] == 1.0:
                entry_equity = equity
            elif entry_equity is not None:
                trades.append(equity / entry_equity - 1.0 if entry_equity else 0.0)
                entry_equity = None
    if entry_equity is not None:
        # Open trade closed at the last close (mark-to-market).
        trades.append(equity / entry_equity - 1.0 if entry_equity else 0.0)
    return equity, turnover, cost_total, period_rets, trades


def _unavailable(symbol: str, strategy: str, entry_rule: str, exit_rule: str,
                 reason: str) -> dict:
    return {
        "strategy": strategy,
        "calculation_status": "UNAVAILABLE",
        "reason": f"{symbol}: {reason}",
        "entry_rule": entry_rule,
        "exit_rule": exit_rule,
        "trade_count": 0,
    }


def compute_rule_based(
    series: Series,
    strategy: str,
    config: Optional[dict] = None,
    fee_bps: float = DEFAULT_FEE_BPS,
    slippage_bps: float = DEFAULT_SLIPPAGE_BPS,
) -> dict:
    """Backtest one rule strategy on a single asset's CLOSED-candle series.

    Returns a metrics dict, or `{"calculation_status": "UNAVAILABLE", ...}` when
    the series is too short for the configured rule (never a crash / guess).
    """
    cfg = config or {}
    closes = series.closes
    n = len(closes)

    if strategy == "MA_CROSSOVER":
        fast = int(cfg.get("ma_fast", DEFAULT_MA_FAST))
        slow = int(cfg.get("ma_slow", DEFAULT_MA_SLOW))
        if fast < 1 or slow < 2 or fast >= slow:
            raise InsufficientData("MA_CROSSOVER requires 1 <= ma_fast < ma_slow")
        need = slow + 1
        entry_rule = f"SMA({fast}) > SMA({slow})"
        exit_rule = f"SMA({fast}) < SMA({slow})"
        make = lambda: _signal_ma(closes, fast, slow)
    elif strategy == "RSI_THRESHOLD":
        period = int(cfg.get("rsi_period", DEFAULT_RSI_PERIOD))
        oversold = float(cfg.get("rsi_oversold", DEFAULT_RSI_OVERSOLD))
        overbought = float(cfg.get("rsi_overbought", DEFAULT_RSI_OVERBOUGHT))
        if period < 2 or not (0 < oversold < overbought < 100):
            raise InsufficientData(
                "RSI_THRESHOLD requires period >= 2 and 0 < oversold < overbought < 100"
            )
        need = period + 2
        entry_rule = f"RSI({period}) < {oversold:g}"
        exit_rule = f"RSI({period}) > {overbought:g}"
        make = lambda: _signal_rsi(closes, period, oversold, overbought)
    elif strategy == "MOMENTUM":
        period = int(cfg.get("momentum_period", DEFAULT_MOMENTUM_PERIOD))
        threshold = float(cfg.get("momentum_threshold", DEFAULT_MOMENTUM_THRESHOLD))
        if period < 1:
            raise InsufficientData("MOMENTUM requires momentum_period >= 1")
        need = period + 2
        entry_rule = f"ret({period}) > {threshold:g}"
        exit_rule = f"ret({period}) <= {threshold:g}"
        make = lambda: _signal_momentum(closes, period, threshold)
    else:
        raise ValueError(f"unsupported rule strategy {strategy!r}")

    if n < need:
        return _unavailable(series.symbol, strategy, entry_rule, exit_rule,
                            f"{n} CLOSED candles < {need} required")

    positions = make()
    equity, turnover, cost_total, period_rets, trades = _simulate(
        closes, positions, fee_bps, slippage_bps)
    n_periods = n - 1
    ann = equity ** (1.0 / n_periods) - 1.0 if n_periods > 0 and equity > 0 else None
    vol, sharpe, max_dd = _risk_metrics(period_rets, n_periods)
    wins = sum(1 for tr in trades if tr > 0)
    return {
        "strategy": strategy,
        "calculation_status": "COMPLETED",
        "total_return": equity - 1.0,
        "annual_return": ann,
        "volatility": vol,
        "sharpe": sharpe,
        "max_drawdown": max_dd,
        "win_rate": (wins / len(trades)) if trades else None,
        "turnover": turnover,
        "cost": cost_total,
        # equity curve is already net of costs
        "cost_adjusted_return": equity - 1.0,
        "trade_count": len(trades),
        "entry_rule": entry_rule,
        "exit_rule": exit_rule,
        "periods": n_periods,
        "fee_bps": fee_bps,
        "slippage_bps": slippage_bps,
    }
