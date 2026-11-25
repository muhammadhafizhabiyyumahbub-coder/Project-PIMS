"""Backtesting Engine (M4, Phase 1).

Deterministic, no-network backtest of BUY_HOLD / STATIC_WEIGHT strategies
over stored candles. See `engine.py`. Phase 2 (rule-based signals) is
out of scope and gated behind owner approval.
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

__all__ = [
    "CALC_VERSION",
    "DEFAULT_FEE_BPS",
    "DEFAULT_SLIPPAGE_BPS",
    "InsufficientData",
    "Series",
    "compute_buy_hold",
    "compute_static_weight",
    "equity_curve_series",
    "run_backtest_for_assets",
    "walk_forward_split",
]
