# PIMS — Development Report (M4 Macro Engine)

TASK REPORT

Task: M4 #6 — Macro Engine (was DEFERRED, now DONE)
Status: Implemented + tested (see Test Results)

Files Created:
- backend/app/data/providers/macro/__init__.py
- backend/app/data/providers/macro/fred.py
- backend/app/engines/macro/engine.py
- backend/app/database/migrations/versions/e8a9b0c1d2e3_add_macro_results.py
- backend/tests/test_macro_engine.py
- docs/REPORT_DEV.md

Files Modified:
- backend/app/config/settings.py (added `fred_api_key`, `fred_base_url`)
- backend/app/database/models/analytics.py (added `MacroResult`)
- backend/app/database/models/__init__.py (export `MacroResult`)
- backend/app/api/rest/analytics_v2.py (added `GET /api/v1/analytics/macro`)
- docs/management/m4-gap-proposals/06-macro.md (status DEFERRED -> DONE)

Skills used:
- `tdd` (SKILL.md) — red/green loop per metric; each pure-math test written
  before/with its function, tests live at public seams (engine functions +
  HTTP endpoint), no private internals, independent expected values.
- `implement-spec` (SKILL.md) — task graph, single integration branch,
  implementer scope limited to the ticket.

---

## 1. Overview

Macro engine Phase 1, FRED source (owner-approved per
`docs/management/m4-gap-proposals/06-macro.md`, option A). FRED API key read
from `.env` (`PIMS_FRED_API_KEY`); no secret in source.

Data flow:

```
FRED REST API (httpx)
      |
      v
FREDAdapter.fetch_observations   (app/data/providers/macro/fred.py)
      |
      v
compute_metrics (pure math)      (app/engines/macro/engine.py)
      |
      v
AnalyticsRun(type=MACRO) + MacroResult rows (PostgreSQL)
      |
      v
GET /api/v1/analytics/macro
```

FRED series map (logical key -> series id):
`CPI=CPIAUCSL, GDP=GDPA, UNRATE=UNRATE, FEDFUNDS=FEDFUNDS, DFF=DFF, 10YUSTR=DGS10`.

## 2. Metrics and formula (Phase 1)

| Metric | Definition | Persisted `analysis_type` |
|---|---|---|
| YoY change | `(last - value[-1-12]) / value[-1-12] * 100` | `YOY` |
| Rolling average 12 | mean of last 12 observations | `ROLLING_AVG_12M` |
| Z-score | `(last - mean) / population_std` | `ZSCORE` |
| Regime | `EXPANSION` if `last >= rolling_avg_12` else `CONTRACTION` | `REGIME` |
| Level | latest observation value | returned only |

Interval is 12 **observations** (not calendar months): correct for monthly
series; for the annual `GDPA` it is 12 years — documented limitation, not
silently wrong. All math is pure and covered by unit tests with independent
expected values.

### Decision (internal contract, no architecture change)

`macro_results` columns: `id, analytics_run_id, analysis_type, series_id,
value, period, computed_at`.

- `analysis_type` = metric name (`YOY`/`ROLLING_AVG_12M`/`ZSCORE`/`REGIME`).
- `value` = numeric metric; `REGIME` encoded `+1.0` EXPANSION / `-1.0`
  CONTRACTION (numeric-only column).
- `period` = latest FRED observation date (ISO).
- The requested `?period=YoY` selects which metric is returned as `value`
  in the response (`YoY` default; also `LEVEL`, `ROLLING_AVG_12M`, `ZSCORE`).

The task's proposed table name differ slightly (`macro_indicators`); the
owner-approved implementation uses `macro_results` per this ticket. Reported
here rather than changed silently.

## 3. HONEST data policy

- Missing FRED value (`"."`) or empty series -> `UNAVAILABLE`, `value = NULL`
  (never fabricated as `0`).
- HTTP/network failure -> `fetch_observations` returns `[]` -> `UNAVAILABLE`.
- No mock data in production paths; tests use `httpx.MockTransport` only.

## 4. Live verification (real FRED key, real network)

- Migration applied to dev DB: `d6e7f8a9b0c1 -> e8a9b0c1d2e3`.
- `GET /api/v1/analytics/macro?period=YoY&series=CPI,UNRATE,FEDFUNDS` -> **200**:

| series | period | level | YoY % | rolling_avg_12 | z-score | regime |
|---|---|---|---|---|---|---|
| CPI | 2026-10-01 | 337.476 | 4.081 | 331.259 | 2.319 | EXPANSION |
| UNRATE | 2026-10-01 | 4.1 | -6.818 | 4.267 | -0.911 | CONTRACTION |
| FEDFUNDS | 2026-10-01 | 3.88 | -5.134 | 3.693 | -0.202 | EXPANSION |

## 5. Tests Executed

- `backend/tests/test_macro_engine.py` (13 tests): pure math (YoY, rolling
  average, z-score, regime), UNAVAILABLE = None-not-0, endpoint + persistence
  of `analytics_runs(MACRO)` + 8 `macro_results` rows, validation (unknown
  series / invalid period -> 422), determinism. No network (MockTransport).
- Full suite: see Test Results below.

Test Results:
- `tests/test_macro_engine.py`: 13 passed.
- Full suite (`pytest -q`): 367 passed, 1 skipped (354 baseline + 13 new).
  (Baseline before change: 354 passed, 1 skipped.)

Known Issues / Limitations:
- Regime is a generic level-trend proxy (`last >= rolling_avg_12`); it is NOT
  an economic nowcast and treats all series identically (e.g. rising UNRATE
  reads CONTRACTION while rising CPI reads EXPANSION). Phase-2 owner decision
  (proposal §14 #6: feed `market_regime` vs separate).
- 12-observation interval is calendar-inaccurate for annual series (`GDPA`).
- FRED revision policy not tracked (always latest vintage); proposal §14 #4.
- Mixed frequencies not normalized to a common calendar.

Architecture Changes:
- None. New engine + provider adapter + table following existing
  `sentiment`/`fundamental` patterns. No core tech, API contract, or approved
  schema changed.

Next Recommended Task:
- Owner decision on regime model wiring (`market_regime`) + revision policy,
  then Phase 2 (yield-curve slope, real rate, VIX risk-on/off proxy).
