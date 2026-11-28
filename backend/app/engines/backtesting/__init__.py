"""Backtesting Engine (M4, Phase 1 + Phase 2).

Deterministic, no-network backtest of BUY_HOLD / STATIC_WEIGHT strategies
(Phase 1) and rule-based strategies MA_CROSSOVER / RSI_THRESHOLD / MOMENTUM
(Phase 2) over stored candles.
"""
from app.engines.backtesting.engine import (
    CALC_VERSION,
    DEFAULT_FEE_BPS,
    DEFAULT_SLIPPAGE_BPS,
    InsufficientData,
    Series,
    compute_buy_hold,
    compute_static_weight,
    equity_curve_series,
    run_backtest_for_assets,
    walk_forward_split,
)
from app.engines.backtesting.rules import (
    RULE_STRATEGIES,
    compute_rule_based,
)

__all__ = [
    "CALC_VERSION",
    "DEFAULT_FEE_BPS",
    "DEFAULT_SLIPPAGE_BPS",
    "InsufficientData",
    "RULE_STRATEGIES",
    "Series",
    "compute_buy_hold",
    "compute_rule_based",
    "compute_static_weight",
    "equity_curve_series",
    "run_backtest_for_assets",
    "walk_forward_split",
]
