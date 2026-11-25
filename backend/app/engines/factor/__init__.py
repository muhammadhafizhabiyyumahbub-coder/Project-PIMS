"""Factor Engine (M4, Phase 1) — market-based factor scores.

Deterministic, no-network computation of momentum / volatility /
reversal / size factors from stored candles. Fundamental-based factors
are out of scope (owner deferred). See `engine.py`.
"""
from app.engines.factor.engine import (
    CALC_VERSION,
    FactorConfig,
    build_universe_series,
    composite,
    compute_momentum,
    compute_reversal,
    compute_size,
    compute_volatility,
    normalize,
    run_factor_for_universe,
)

__all__ = [
    "CALC_VERSION",
    "FactorConfig",
    "build_universe_series",
    "composite",
    "compute_momentum",
    "compute_reversal",
    "compute_size",
    "compute_volatility",
    "normalize",
    "run_factor_for_universe",
]
