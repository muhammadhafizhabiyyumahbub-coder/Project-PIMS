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

---

# PIMS — Development Report (M4 Macro Engine — formula audit fixes)

TASK REPORT

Task: Fix 5 Macro Engine bugs from `docs/management/MACRO_FORMULA_AUDIT.md` (Nadia)
Status: Implemented + tested; commit `652f5a9` on `master` (not pushed)

Files Modified:
- backend/app/engines/macro/engine.py
- backend/app/data/providers/macro/fred.py
- backend/app/data/providers/macro/fred_fetch.py
- backend/tests/test_macro_engine.py

Skills used:
- `tdd` (SKILL.md) — one failing test per audit finding before the fix, at the
  public seams (`compute_metrics`, `classify_macro_regime`, `FREDAdapter`,
  `FredFetcher`, the HTTP endpoint); expected values taken from the audit's
  independent hand computations, not recomputed the way the code does.
- `implement-spec` (SKILL.md) — not used: it needs a task tracker/tickets
  (frontier graph) and an integration branch, none exists for this bug list.

Implementation Summary:
- F2: `SERIES_MAP["GDP"]` `GDPA` (annual nominal) -> `GDPC1` (quarterly real);
  YoY lag follows frequency (`YOY_LAG`: 12 monthly, 4 quarterly, 252 daily).
- F4: rolling window follows frequency (`MA_WINDOW`: 12 monthly, 4 quarterly,
  12 daily) instead of global `12`.
- F3: `SERIES_META` tags unit; percent series (UNRATE, FEDFUNDS, DFF, 10YUSTR)
  report YoY in percentage points (`yoy_change_pp`, `yoy_unit="pp"`), level
  series keep relative `%`.
- F6: new `classify_macro_regime` — EXPANSION iff real GDP YoY > 0 AND UNRATE
  is falling (latest < previous), else CONTRACTION; exposed as top-level
  `regime` + `regime_basis` in the API response. Per-series `regime` kept
  unchanged as a level-trend proxy (persisted REGIME rows unchanged).
- F7: empty/`test_key` API key -> `[]` (no stub `100.0`); HTTP errors logged
  and return `[]` (UNAVAILABLE). `"."`/missing values skipped.
- `CALC_VERSION` -> `macro.phase1.v2` (methodology changed).

| # | before | after |
|---|---|---|
| F2 GDP | GDPA annual, YoY 82.82% | GDPC1 quarterly, YoY 2.29% (lag 4) |
| F3 UNRATE | YoY -6.818% (relative) | YoY -0.30 pp |
| F4 GDP MA | 12 quarters (12y) 22,980 | 4 quarters 24,368.27 |
| F6 regime | level >= MA12 | GDP YoY>0 & UNRATE falling |
| F7 key empty | fabricated 100.0 | UNAVAILABLE; HTTP err logged |

Tests Executed:
- `pytest backend/tests/test_macro_engine.py -q` (24 tests).

Test Results:
- `tests/test_macro_engine.py`: 24 passed (13 original unchanged + 11 new for
  F2/F3/F4/F6/F7).
- Full suite (`pytest -q`): 345 passed, 9 failed, 28 errors, 1 skipped — the
  failures/errors are pre-existing DB issues (`UndefinedTable: relation
  "portfolios" does not exist`, `DeadlockDetected`) in unrelated modules
  (`test_asset_api`, `test_analytics_api`, ...); they reproduce in isolation
  with no macro code involved. No macro module is among them.

Live verification (`TestClient`, real FRED key + dev DB):
`GET /api/v1/analytics/macro?period=YoY&series=CPI,GDP,UNRATE,FEDFUNDS` -> 200

| series | provider | freq | period | level | YoY | unit | MA | regime |
|---|---|---|---|---|---|---|---|---|
| CPI | CPIAUCSL | monthly | 2026-10-01 | 337.476 | 4.081 | % | 331.259 | EXPANSION |
| GDP | GDPC1 | quarterly | 2026-07-01 | 24665.201 | 2.290 | % | 24368.27 | EXPANSION |
| UNRATE | UNRATE | monthly | 2026-10-01 | 4.1 | -0.300 | pp | 4.267 | CONTRACTION |
| FEDFUNDS | FEDFUNDS | monthly | 2026-10-01 | 3.88 | -0.210 | pp | 3.693 | EXPANSION |

- `macro_regime: EXPANSION`, `regime_basis: {gdp_yoy: 2.29, unrate_delta: -0.10}`.
- YoY GDP now matches the audit's hand value (2.29%), UNRATE/FEDFUNDS in pp,
  regime follows the standard rule.

Known Issues / Limitations:
- Per-series `regime` still the level-trend proxy (persisted REGIME rows);
  only the top-level `macro_regime` follows the GDP/UNRATE rule. Tests lock
  the per-series behavior.
- UNRATE "falling" uses month-over-month (latest vs previous), matching the
  audit's expected-manual (4.2 -> 4.1). A 3-month delta is the audit's
  recommendation but is not applied (no ticket for it).
- `httpx` logs the full FRED URL at INFO, including `api_key` — secret visible
  in logs (pre-existing, `app/core/logging.py`, out of this task's scope).

Architecture Changes:
- None. Same engine/provider/table; API response gained additive
  `regime`/`regime_basis` fields and per-result `frequency`/`unit`/`yoy_unit`.

Next Recommended Task:
- Silence the httpx INFO URL log (secret leak), and owner decision on the
  3-month UNRATE delta + z-score window (`ddof`, window) per audit item 3/5.
