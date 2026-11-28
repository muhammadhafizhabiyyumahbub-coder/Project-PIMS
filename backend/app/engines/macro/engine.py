"""Macro Engine — M4, Phase 1 (FRED-based, deterministic).

Implements the owner-approved Phase-1 macro methodology
(docs/management/m4-gap-proposals/06-macro.md): FRED (option A) as the macro
source, public US/USD series only.

Metrics per series (observations oldest-first), frequency-aware:
- YoY change: level series -> (last - value `lag` obs earlier)/that value *100;
  percent series (rates/yields) -> the difference in percentage points (pp),
  because a relative % of a rate is meaningless (audit F3). `lag` is the
  12-month lookback in observations for the series frequency (12 monthly,
  4 quarterly, 252 daily) (audit F2).
- Rolling average 12m: mean of the last 12 months of observations
  (12 monthly, 4 quarterly, 12 daily) (audit F4).
- Z-score: (last - mean(all)) / population std(all).
- Per-series regime: EXPANSION when the latest level is at/above its rolling
  average, else CONTRACTION. This is a generic level-trend proxy, kept for the
  persisted per-series rows; the economic `macro_regime` is derived separately
  from GDP YoY and the UNRATE direction (audit F6).

Deterministic: the math is pure; network only through FREDAdapter. No FRED
data (missing series / network failure) -> UNAVAILABLE (value None, never 0).
"""
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.data.providers.macro.fred import FREDAdapter, SERIES_MAP
from app.database.models import AnalyticsRun, MacroResult

logger = logging.getLogger(__name__)

CALC_VERSION = "macro.phase1.v2"

ROLLING_WINDOW = 12
DEFAULT_PERIOD = "YOY"

# Logical series -> (frequency, unit). Frequency drives the YoY lag and the
# rolling-average window; unit "percent" means YoY is reported in percentage
# points (pp) (audit F3).
SERIES_META = {
    "CPI": ("monthly", "index"),
    "GDP": ("quarterly", "level"),  # GDPC1: real, chained 2017 USD
    "UNRATE": ("monthly", "percent"),
    "FEDFUNDS": ("monthly", "percent"),
    "DFF": ("daily", "percent"),
    "10YUSTR": ("daily", "percent"),
}

# 12-month lookback / window expressed in observations per frequency (audit F2/F4).
YOY_LAG = {"monthly": 12, "quarterly": 4, "daily": 252}
MA_WINDOW = {"monthly": 12, "quarterly": 4, "daily": 12}

# Requested period -> internal metric key.
PERIOD_TO_METRIC = {
    "YOY": "yoy",
    "LEVEL": "level",
    "ROLLING_AVG_12M": "rolling_avg_12",
    "ZSCORE": "zscore",
}

# Metrics persisted per series (analysis_type column) -> compute_metrics key.
_PERSISTED_METRICS = {
    "YOY": "yoy",
    "ROLLING_AVG_12M": "rolling_avg_12",
    "ZSCORE": "zscore",
    "REGIME": None,
}


def yoy_change(values: list[float], lag: int = ROLLING_WINDOW) -> Optional[float]:
    """Percent change of the last value vs `lag` observations earlier."""
    if len(values) <= lag:
        return None
    prev = values[-1 - lag]
    if prev == 0:
        return None
    return (values[-1] - prev) / prev * 100.0


def yoy_change_pp(values: list[float], lag: int = ROLLING_WINDOW) -> Optional[float]:
    """Percentage-point change of the last value vs `lag` obs earlier.

    For series already expressed in percent (rates/yields) a relative % change
    is meaningless (audit F3); report the difference in percentage points.
    """
    if len(values) <= lag:
        return None
    return values[-1] - values[-1 - lag]


def rolling_average(values: list[float], window: int = ROLLING_WINDOW) -> Optional[float]:
    """Mean of the last `window` values; None if fewer than `window` available."""
    if len(values) < window:
        return None
    return sum(values[-window:]) / window


def zscore(values: list[float]) -> Optional[float]:
    """Population z-score of the last value in the series."""
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    if var <= 0:
        return None
    return (values[-1] - mean) / (var ** 0.5)


def classify_regime(latest: Optional[float], avg: Optional[float]) -> str:
    """Per-series level-trend proxy: EXPANSION if level at/above its average."""
    if latest is None or avg is None:
        return "UNAVAILABLE"
    return "EXPANSION" if latest >= avg else "CONTRACTION"


def classify_macro_regime(
    gdp_yoy: Optional[float], unrate_values: Optional[list[float]]
) -> tuple[str, dict]:
    """Economic macro regime (audit F6): EXPANSION when real GDP YoY > 0 and
    UNRATE is falling (latest below the previous reading), else CONTRACTION."""
    if gdp_yoy is None or not unrate_values or len(unrate_values) < 2:
        return "UNAVAILABLE", {}
    unrate_delta = unrate_values[-1] - unrate_values[-2]
    basis = {"gdp_yoy": gdp_yoy, "unrate_delta": unrate_delta}
    regime = "EXPANSION" if gdp_yoy > 0 and unrate_delta < 0 else "CONTRACTION"
    return regime, basis


def compute_metrics(
    observations: list[dict], freq: str = "monthly", unit: str = "level"
) -> dict:
    """Compute all Phase-1 metrics for one series' observations.

    observations: [{'date': 'YYYY-MM-DD', 'value': float}] oldest-first.
    `freq` sets the YoY lag and rolling window; `unit` "percent" reports YoY in
    percentage points (pp) instead of relative %.
    """
    values = [o["value"] for o in observations]
    lag = YOY_LAG.get(freq, ROLLING_WINDOW)
    window = MA_WINDOW.get(freq, ROLLING_WINDOW)
    if not values:
        return {
            "status": "UNAVAILABLE",
            "reason": "no FRED data",
            "period": None,
            "level": None,
            "yoy": None,
            "yoy_unit": None,
            "rolling_avg_12": None,
            "zscore": None,
            "regime": "UNAVAILABLE",
        }
    if unit == "percent":
        yoy = yoy_change_pp(values, lag)
        yoy_unit = "pp"
    else:
        yoy = yoy_change(values, lag)
        yoy_unit = "%"
    last_avg = rolling_average(values, window)
    return {
        "status": "COMPLETED",
        "reason": None,
        "period": observations[-1]["date"],
        "level": values[-1],
        "yoy": yoy,
        "yoy_unit": yoy_unit,
        "rolling_avg_12": last_avg,
        "zscore": zscore(values),
        "regime": classify_regime(values[-1], last_avg),
    }


def run_macro_analysis(
    session: Session,
    series_keys: list[str],
    period: str = DEFAULT_PERIOD,
    adapter: Optional[FREDAdapter] = None,
) -> dict:
    """Fetch FRED series, compute metrics, persist analytics_runs(MACRO) +
    macro_results. `period` selects the reported metric (YoY by default)."""
    analysis_type = (period or DEFAULT_PERIOD).upper()
    if analysis_type not in PERIOD_TO_METRIC:
        raise ValueError(
            f"unsupported period {period!r}; allowed: {sorted(PERIOD_TO_METRIC)}"
        )
    unknown = [k for k in series_keys if k not in SERIES_MAP]
    if unknown:
        raise ValueError(f"unknown macro series: {unknown}; allowed: {sorted(SERIES_MAP)}")

    metric_key = PERIOD_TO_METRIC[analysis_type]
    fred = adapter or FREDAdapter()
    now = datetime.now(timezone.utc)

    run = AnalyticsRun(
        engine_type="MACRO",
        calculation_version=CALC_VERSION,
        execution_status="COMPLETED",
        started_at=now,
        completed_at=now,
        input_metadata={
            "period": analysis_type,
            "series": list(series_keys),
            "source": "FRED",
            "sanitized": True,
        },
    )
    session.add(run)
    session.flush()

    results = []
    by_key = {}
    unrate_values = None
    for key in series_keys:
        provider_series = SERIES_MAP[key]
        freq, unit = SERIES_META.get(key, ("monthly", "level"))
        observations = fred.fetch_observations(provider_series)
        metrics = compute_metrics(observations, freq=freq, unit=unit)
        if key == "UNRATE":
            unrate_values = [o["value"] for o in observations]
        by_key[key] = metrics
        results.append(
            {
                "series_id": key,
                "provider_series": provider_series,
                "frequency": freq,
                "unit": unit,
                "status": metrics["status"],
                "value": metrics[metric_key],
                "period": metrics["period"],
                "level": metrics["level"],
                "yoy": metrics["yoy"],
                "yoy_unit": metrics["yoy_unit"],
                "rolling_avg_12": metrics["rolling_avg_12"],
                "zscore": metrics["zscore"],
                "regime": metrics["regime"],
                "reason": metrics["reason"],
            }
        )
        for metric, persist_key in _PERSISTED_METRICS.items():
            if metric == "REGIME":
                value = (
                    None if metrics["regime"] == "UNAVAILABLE"
                    else (1.0 if metrics["regime"] == "EXPANSION" else -1.0)
                )
            else:
                value = metrics[persist_key]
            session.add(
                MacroResult(
                    analytics_run_id=run.id,
                    analysis_type=metric,
                    series_id=key,
                    value=value,
                    period=metrics["period"],
                    computed_at=now,
                )
            )
    session.flush()

    macro_regime, regime_basis = classify_macro_regime(
        (by_key.get("GDP") or {}).get("yoy"), unrate_values
    )

    return {
        "run_id": str(run.id),
        "analysis_type": analysis_type,
        "source": "FRED",
        "status": "COMPLETED",
        "regime": macro_regime,
        "regime_basis": regime_basis,
        "results": results,
    }
