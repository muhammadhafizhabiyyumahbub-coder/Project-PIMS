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

## Appendix A — QA (Sakti, 2026-11-28)

Full report: `docs/QA_REPORT.md`. Ringkas:

- Suite dari root repo (tanpa run paralel): **377 passed, 1 failed, 1 skipped** (379). Satu-satunya gagal: `test_correlation_engine.py::test_correlation_endpoint_persists_results` (`from tests.conftest import` → `ModuleNotFoundError` bila pytest dijalankan dari root; lulus dari `backend/`). Klaim "367 passed" hanya valid dengan CWD `backend/`.
- Suite **tidak paralel-safe**: run bersamaan di `pims_test` memicu `DeadlockDetected` + `UndefinedTable` (contoh terukur: 62 errors).
- `conftest` teardown `drop_all` meninggalkan `alembic_version` stamped → `pims_test` kosong tanpa tabel dan `alembic upgrade head` no-op.
- Keamanan: tidak ada secret hardcoded; SQLi bersih; temuan: tanpa auth + bind `0.0.0.0`, `str(exc)` bocor di 12 handler `analytics_v2.py`, port DB dipublish, `PIMS_FRED_API_KEY` tidak ada di `.env.example`/compose.
- Lint: 235 temuan ruff (app) / 530 (tests); `mypy` tidak terpasang → typecheck tidak dijalankan.

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

---

TASK REPORT

Task: Fix temuan keamanan Sakti Q1 (High) + Q2 (Medium)
Status: DONE (implemented + tested)

Files Created:
- docs/SECURITY_NOTES.md
- backend/tests/test_security_q2.py

Files Modified:
- backend/Dockerfile (comment: why container listens 0.0.0.0)
- docker-compose.yml (hapus publish 5432; backend 127.0.0.1:8000:8000)
- backend/app/api/envelope.py (helper `server_error`)
- backend/app/api/rest/analytics_v2.py (12x SERVER_ERROR -> server_error)
- backend/app/api/rest/analytics.py (1x SERVER_ERROR -> server_error)

Implementation Summary:
- Q1: port DB tidak lagi dipublish; backend hanya host-local (127.0.0.1).
  Dockerfile tetap `--host 0.0.0.0` karena `frontend` service memanggil
  `http://backend:8000` lewat jaringan compose — bind loopback akan memutusnya.
  Kontrol eksposur ditaruh di publish binding compose. Asumsi single-user +
  firewall lokal + auth = Phase 2 didokumentasikan di docs/SECURITY_NOTES.md.
  (Deviasi dari instruksi Q1 dicatat sebagai ISSUE di SECURITY_NOTES §2.)
- Q2: helper `server_error(exc)` di app/api/envelope.py -> `logger.exception`
  detail ke server log, klien menerima generik "Internal error (see server logs)".
  Semua 13 titik `error_response("SERVER_ERROR", str(exc), 500)` diganti
  (12 di analytics_v2.py + 1 di analytics.py). QA menulis "14 tempat" tapi
  hanya melisting 12; total nyata setelah grep = 13.

Tests Executed:
- backend/.venv/Scripts/python.exe -m pytest tests/test_security_q2.py -q  (dari backend/)
- backend/.venv/Scripts/python.exe -m pytest backend/tests/ -q --tb=short  (dari root)

Test Results:
- test_security_q2.py: 3 passed.
- Full suite (root): 380 passed, 1 failed, 1 skipped, 411.91s.
- 1 failed = Q3 pre-existing (`test_correlation_engine.py:152`
  `ModuleNotFoundError: No module named 'tests.conftest'`) — di luar scope
  task ini (bukan Q1/Q2), sudah dicatat di docs/QA_REPORT.md.

Skills used (checked ~/.config/opencode/skills):
- `tdd` — ada; dipakai ringan (test red/green untuk Q2: assert 500 generik).
- `simplify-code` — TIDAK ada di direktori skill (tidak terinstal), tidak dipakai.

Known Issues:
- Q3 correlation test masih gagal bila pytest dijalankan dari root (pre-existing).
- Lint repo belum bersih (Q10), typecheck tidak tersedia, di luar scope.

Architecture Changes:
- None. Kontrak API tetap (envelope error sama bentuk, hanya pesan 500 jadi generik).

Next Recommended Task:
- Q3: perbaiki import helper test (`from conftest import ...` / pindah ke
  `tests/helpers.py`), agar suite hijau penuh dari root.

---

# PIMS — Development Report (M4 Backtesting Engine — Phase 2, rule-based)

TASK REPORT

Task: M4 Backtesting Phase 2 — rule-based strategies (MA_CROSSOVER / RSI_THRESHOLD / MOMENTUM)
Status: Implemented + tested + live-verified (commit on `master`, not pushed)

Files Created:
- backend/app/engines/backtesting/rules.py
- backend/app/database/migrations/versions/f2b3c4d5e6a7_add_backtest_rule_columns.py
- backend/tests/test_backtest_phase2.py

Files Modified:
- backend/app/engines/backtesting/engine.py (rule branch + persist columns)
- backend/app/engines/backtesting/__init__.py (exports)
- backend/app/database/models/analytics.py (`BacktestMetrics` columns)
- backend/app/api/rest/analytics_v2.py (`BacktestRequest` + rule_config)

Skills used (checked `~/.config/opencode/skills`):
- `tdd` — pure-math rule tests written at public seams (`compute_rule_based`,
  HTTP endpoint); expected values are worked examples, not recomputed.
- `implement-spec` — spec (`docs/management/m4-gap-proposals/01-backtesting.md`
  §2 Option B / §13 item 6) read first; scope held to the ticket.

Implementation Summary:
- Phase 2 rule strategies in `rules.py`, all deterministic, no network:
  - MA_CROSSOVER: long while `SMA(fast) > SMA(slow)`, flat otherwise.
  - RSI_THRESHOLD: enter `RSI(period) < oversold`, exit `RSI(period) > overbought`
    (Wilder smoothing).
  - MOMENTUM: enter while trailing `period` return > threshold.
  - Signal at `close[t]` sets the position held over `(t, t+1]` → no look-ahead.
  - Cost = `|Δposition| × (fee_bps + slippage_bps)`, charged at each change.
  - Too-few candles → `{"calculation_status": "UNAVAILABLE", "reason": ...}`
    (never a crash, never a guessed value). Bad config raises `InsufficientData`.
- `run_backtest_for_assets(..., rule_config=...)`: rule strategies take exactly
  one symbol (else `INVALID_CONFIG`); UNAVAILABLE persists an `AnalyticsRun`
  with `execution_status="UNAVAILABLE"`. BUY_HOLD / STATIC_WEIGHT unchanged.
- Persist per metric row: `strategy_type`, `entry_rule`, `exit_rule`,
  `trade_count`, `win_rate` (plus existing long-format metrics).
- Endpoint `POST /api/v1/analytics/backtest`: `strategy` pattern extended, new
  optional rule config (`ma_fast`, `ma_slow`, `rsi_period`, `rsi_oversold`,
  `rsi_overbought`, `momentum_period`, `momentum_threshold`).
- Migration `f2b3c4d5e6a7` (down_revision `e8a9b0c1d2e3`) adds the 5 columns.

Tests Executed:
- `backend/.venv/Scripts/python.exe -m pytest tests/test_backtest_phase2.py -v`
- Full suite: `... -m pytest -q` (from `backend/`, not parallel).

Test Results:
- `tests/test_backtest_phase2.py`: 16 passed (9 pure-math + 7 endpoint/persist).
- Full suite: **397 passed, 1 skipped** (baseline 381 + 16 new). No regression.

Live verification (TestClient via app startup; dev DB `pims`, 1h CRYPTO candles):
- Migration applied: `e8a9b0c1d2e3 -> f2b3c4d5e6a7`.
- `POST /api/v1/analytics/backtest` `strategy=MA_CROSSOVER` (ma_fast 10, ma_slow 30,
  fee 10bps, slippage 5bps, limit 300):

| symbol | status | trades | win_rate | total_return | sharpe | max_dd |
|---|---|---|---|---|---|---|
| BTCUSDT | COMPLETED | 6 | 0.500 | -7.22% | -0.640 | 7.46% |
| SOLUSDT | COMPLETED | 6 | 0.333 | -7.85% | -0.591 | 8.93% |
| ETHUSDT | COMPLETED | 3 | 0.333 | -4.04% | -0.305 | 7.66% |

- Persistence confirmed: 9 metric rows per run with
  `strategy_type=MA_CROSSOVER`, `entry_rule=SMA(10) > SMA(30)`,
  `exit_rule=SMA(10) < SMA(30)`, `trade_count`, `win_rate` populated.

Known Issues / Limitations:
- Rule-based runs are single-asset (one symbol per run); multi-asset rule
  portfolios are not implemented → `INVALID_CONFIG` if >1 symbol.
- Win rate for rule strategies is trade-level (closed trades; an open trade is
  marked to the last close), unlike the Phase 1 period-level win rate.
- MOMENTUM uses a fixed threshold comparison; no volatility scaling.
- Short selling not supported (flat/long only).

Architecture Changes:
- None. Additive engine module + additive nullable columns + extended request
  fields. No core tech, API contract, or approved schema changed.

Next Recommended Task:
- Owner decision on multi-asset rule portfolios + short support, then wire
  scanner/technical signals into a RULE_BASED scanner-backed strategy.

---

# PIMS — Development Report (Watchlist module, api-spec §17)

TASK REPORT

Task: Implement Watchlist (2 tables, single-user) — model + migration + repo + REST + tests
Status: Implemented + tested + live-verified (commits on `master`, not pushed)

Files Created:
- backend/app/database/models/watchlist.py (`Watchlist`, `WatchlistItem`)
- backend/app/database/migrations/versions/a3f5c7d9e1b2_add_watchlist_tables.py
- backend/app/database/repositories/watchlist.py
- backend/app/api/rest/watchlist.py
- backend/app/schemas/watchlist.py
- backend/tests/test_watchlist.py

Files Modified:
- backend/app/database/models/__init__.py (export `Watchlist`, `WatchlistItem`)
- backend/app/database/repositories/__init__.py (register `watchlist`)
- backend/app/main.py (include watchlist router under `/api/v1`)
- backend/tests/conftest.py (add `watchlist_items`, `watchlists` to TRUNCATE list)
- backend/tests/test_api_contract_snapshot.py (add 7 watchlist endpoints)

Skills used (checked `~/.config/opencode/skills`):
- `tdd` — tests written at public seams (HTTP endpoints + DB), independent
  expected values; `test_unique_constraint_enforced_in_db` locks the DB-level
  unique rule directly.
- `implement-spec` — read api-spec §17 + technical-decisions §7.17 first; scope
  held to the 7-endpoint ticket, no schema invention.

Implementation Summary:
- `watchlists(id, name, description, created_at, updated_at)`.
- `watchlist_items(id, watchlist_id FK→watchlists ON DELETE CASCADE,
  asset_id FK→assets ON DELETE RESTRICT, added_at)`, `UNIQUE(watchlist_id,
  asset_id)`, index on both FKs. No `user_id` (single-user).
- Repository: list/create/get(+items)/update/delete + add/get/remove item.
- Endpoints: `GET/POST /watchlists`, `GET/PATCH/DELETE /watchlists/{id}`,
  `POST /watchlists/{id}/items`, `DELETE /watchlists/{id}/items/{asset_id}`.
  Errors: 404 (unknown watchlist/asset/uuid), 409 (duplicate item), 422
  (body validation via Pydantic).
- Item `added_at` used per task; technical-decisions §7.17 says `created_at`
  for that column. Task instruction (owner) takes priority; reported here, not
  changed silently.

### Migration head deviation (IMPORTANT)
Task stated head = `e8a9b0c1d2e3`. Actual head is **`f2b3c4d5e6a7`**
(`add_backtest_rule_columns`, already `down_revision = e8a9b0c1d2e3`). Using
`e8a9b0c1d2e3` as the new down_revision would create **two heads** and break
`alembic upgrade head` at startup. New migration
`a3f5c7d9e1b2` therefore has `down_revision = f2b3c4d5e6a7`, keeping a single
head (`alembic heads` → `a3f5c7d9e1b2`).

Tests Executed:
- `backend/.venv/Scripts/python.exe -m pytest tests/test_watchlist.py -v`
- Full suite: `... -m pytest tests -q` (from `backend/`, not parallel).

Test Results:
- `tests/test_watchlist.py`: **10 passed** (CRUD, duplicate 409, FK/unique,
  404/422, cascade delete).
- Full suite: **410 passed, 1 skipped** (no regression).

Live verification (TestClient + dev DB `pims`):
- Migration applied: `f2b3c4d5e6a7 -> a3f5c7d9e1b2`.
- create watchlist → 201; add item (`BTCUSDT`) → 201 with symbol; detail shows
  `item_count=1` + items; remove item → 200; watchlist delete cascades items.

Known Issues / Limitations:
- `pims_test` is **not parallel-safe**: running this suite concurrently with
  another process on `pims_test` caused intermittent `DeadlockDetected` /
  `DuplicateTable (pg_type_typname_nsp_index)` at fixture setup, and one
  spurious add-item 404. Green only when run alone; verified with an idle-DB
  gate. Pre-existing, matches `docs/QA_REPORT.md`.
- `a3f5c7d9e1b2` and other watchlist files were already swept into commit
  `d7fb248` by a concurrent automation (`git add -A`) before this task's own
  commit; a follow-up commit `1ad751d` removed two scratch artifacts that
  commit had captured (`backend/pyver.txt`, `backend/scripts/
  debug_watchlist_flow.py`). Not pushed.

Architecture Changes:
- None. Additive tables/models/repo/schemas/router per approved two-table design
  (technical-decisions §7.17); API contract follows api-spec §17 unchanged.

Next Recommended Task:
- Frontend watchlist view (deferred), and a migration-hygiene note in
  `docs/decisions/technical-decisions.md` §7.17 (watchlist now implemented).

---

# P5 — Dashboard Watchlist Panel

TASK REPORT

Task: P5 Dashboard Watchlist Panel — connect the existing watchlist API to the dashboard
Status: Implemented + verified

Files Created:
- frontend/src/features/watchlist/WatchlistPanel.tsx
- frontend/app/watchlist/page.tsx
- docs/REPORT_DEV.md (this section)

Files Modified:
- frontend/src/services/api.ts (added listWatchlists / getWatchlist / createWatchlist / addWatchlistItem + type imports)
- frontend/src/types/api.ts (added Watchlist, WatchlistItem, WatchlistDetail)
- frontend/app/page.tsx (added "Watchlists" link in the dashboard header nav)

Skills used (from `~/.config/opencode/skills`):
- `tdd` — tests live at the public seam (HTTP endpoints via TestClient), no
  private internals, independent expected values. The backend seam was already
  covered by the existing suite, so no new test file was added (see Known Issues).
- `implement-spec` — ticket scope limited to P5; read the existing dashboard/API
  contracts and reused them rather than inventing new ones.

Implementation Summary:
- Backend: no change. Watchlist endpoints already complete in `d7fb248`
  (`backend/app/api/rest/watchlist.py`, 7 routes under `/api/v1/watchlists`).
- Frontend data layer: 4 API functions + 3 types mirroring the existing
  `{data, meta}` envelope / `ApiRequestError` pattern in `services/api.ts`.
- Panel: `WatchlistPanel` (client) lists watchlists (`GET /watchlists`, shows
  `item_count`), loads items on select (`GET /watchlists/{id}` -> symbol, name),
  creates a watchlist, and adds an instrument via the shared `AssetPicker`
  (`POST /watchlists/{id}/items`). Loading / empty / error + retry states match
  `PortfolioList` / `PortfolioWidget`.
- Route: `app/watchlist/page.tsx` (`metadata` + panel), same shape as
  `app/scanner/page.tsx`.
- Link added in the dashboard header next to Scanner / Portfolios.
- Deviation from the task wording: the repo has no `app/(dashboard)/` route
  group and no `app/(dashboard)/components/`. Followed the existing convention
  instead — feature component under `src/features/`, page under `app/watchlist/`.

Tests Executed:
- Frontend typecheck (no build): `node node_modules/typescript/bin/tsc --noEmit`
  (from `frontend/`).
- Backend: `backend/.venv/Scripts/python.exe -m pytest tests/test_watchlist.py -q`
  (sequential; not run in parallel).

Test Results:
- `tsc --noEmit`: clean (no diagnostics).
- `tests/test_watchlist.py`: 10 passed. Covers the required codes — list 200,
  detail 200, `GET/PATCH/DELETE` missing -> 404, invalid UUID -> 404,
  create/patch/add-item validation -> 422, duplicate item -> 409. This is the
  P5 "watchlist endpoint 200 / 404 / 422" integration coverage.
- Live-verify: `GET /api/v1/watchlists` returns 200 (asserted in
  `test_create_and_list`; `meta.count` matches).

Known Issues:
- `backend/tests/test_watchlist_api.py` was NOT created: its stated scope
  (4-5 TestClient cases for 200 / 404 / 422) is already fully covered by the
  existing `backend/tests/test_watchlist.py` (10 cases, same file/DB seam).
  A second file would duplicate the same responsibility (AGENTS.md §18.9).
  Say the word if the exact filename is required.
- No frontend test file: the repo has no JS test runner installed (no
  vitest/jest); the task scoped the frontend check to "verify file, no build".
  Adding a runner would add an unrequested dependency. Verification here is the
  clean `tsc --noEmit` typecheck.
- `pims_test` is not parallel-safe (pre-existing, see `docs/QA_REPORT.md`);
  the watchlist suite was run alone.

Architecture Changes:
- None. Additive frontend files only; API contract (`api-spec §17`) unchanged.

Next Recommended Task:
- Add assets to a watchlist from the instrument page, and a project-level JS
  test runner if the frontend is to get real component tests.

