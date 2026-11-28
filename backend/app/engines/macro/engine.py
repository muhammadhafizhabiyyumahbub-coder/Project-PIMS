"""Macro Engine — M4, Phase 1 (FRED-based, deterministic).

Implements the owner-approved Phase-1 macro methodology
(docs/management/m4-gap-proposals/06-macro.md): FRED (option A) as the macro
source, public US/USD series only.

Metrics per series (observations oldest-first):
- YoY change: (last - value `lag` obs earlier) / value `lag` obs earlier * 100.
- Rolling average 12: mean of the last 12 observations.
- Z-score: (last - mean(all)) / population std(all).
- Regime: EXPANSION when the latest level is at/above its 12-obs rolling
  average, else CONTRACTION. Phase-1 simplification: a generic level-trend
  proxy, NOT an economic nowcast (documented in docs/REPORT_DEV.md).

Deterministic: the math is pure; network only through FREDAdapter. No FRED
data (missing series / network failure) -> UNAVAILABLE (value None, never 0).
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.data.providers.macro.fred import FREDAdapter, SERIES_MAP
from app.database.models import AnalyticsRun, MacroResult

CALC_VERSION = "macro.phase1.v1"

ROLLING_WINDOW = 12
DEFAULT_PERIOD = "YOY"

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
    """EXPANSION if level at/above its rolling average, else CONTRACTION."""
    if latest is None or avg is None:
        return "UNAVAILABLE"
    return "EXPANSION" if latest >= avg else "CONTRACTION"


def compute_metrics(observations: list[dict]) -> dict:
    """Compute all Phase-1 metrics for one series' observations.

    observations: [{'date': 'YYYY-MM-DD', 'value': float}] oldest-first.
    """
    values = [o["value"] for o in observations]
    if not values:
        return {
            "status": "UNAVAILABLE",
            "reason": "no FRED data",
            "period": None,
            "level": None,
            "yoy": None,
            "rolling_avg_12": None,
            "zscore": None,
            "regime": "UNAVAILABLE",
        }
    last_avg = rolling_average(values)
    return {
        "status": "COMPLETED",
        "reason": None,
        "period": observations[-1]["date"],
        "level": values[-1],
        "yoy": yoy_change(values),
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
    for key in series_keys:
        provider_series = SERIES_MAP[key]
        observations = fred.fetch_observations(provider_series)
        metrics = compute_metrics(observations)
        results.append(
            {
                "series_id": key,
                "provider_series": provider_series,
                "status": metrics["status"],
                "value": metrics[metric_key],
                "period": metrics["period"],
                "level": metrics["level"],
                "yoy": metrics["yoy"],
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

    return {
        "run_id": str(run.id),
        "analysis_type": analysis_type,
        "source": "FRED",
        "status": "COMPLETED",
        "results": results,
    }
