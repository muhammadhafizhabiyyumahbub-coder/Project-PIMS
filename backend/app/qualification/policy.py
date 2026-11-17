"Qualification policy. Deterministic, configurable criteria for engine passes."

DEFAULT_POLICY = {
    # Engines that MUST be ready before AI research may run.
    "required_engines": ["TECHNICAL", "MARKET_REGIME", "RISK", "SCANNER"],
    # Engines that may be missing; their absence must be disclosed, never PASSED.
    "optional_engines": ["CORRELATION", "FUNDAMENTAL", "SENTIMENT"],
    # Engine results older than this are STALE and block research.
    "max_stale_seconds": 3600,
    # Risk pass criterion: annualized volatility at or below this threshold.
    "risk_max_annualized_volatility": 0.85,
    # Regime pass criterion: any completed classification passes (no trend filter).
    "regime_allowed_trends": None,
    # Scanner pass criterion: minimum ranking score for dashboard qualification.
    "scanner_min_score": None,
}
