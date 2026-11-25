# PIMS — Autonomous Project State

**Diperbarui:** 2026-11-25 (Hermes sebagai Project Director, OpenCode sebagai implementasi)
**Repo:** `D:/personal-investment-management-system` · branch `master` · remote SSH `git@github.com:muhammadhafizhabiyyumahbub-coder/Project-PIMS.git`
**Status:** V1 Release Candidate + pengembangan lanjutan (roadmap baru)

---

## 1. Posisi terverifikasi

| Item | Nilai | Cara verifikasi |
|---|---|---|
| Commit terakhir | `d367c9d` (M4 proposals + §26 decision; M4-backtest menyusul) | `git log --oneline -1` |
| Backend test | **270 passed, 0 failed, 1 skipped** (LOKAL, suite penuh) | `pytest tests -q` (PostgreSQL 17 lokal) |
| Bug P0 (fixture) | ~~`test_ingest_quotes_timeout_failed` AttributeError~~ **selesai** (`dda517c`): fixture `Market CRYPTO` dibuat bila tak ada | `pytest tests/test_market_ingestion.py::test_ingest_quotes_timeout_failed` |
| CI GitHub Actions | **HIJAU** — run `10f9871` (CI #42) `conclusion: success` (backend+frontend+migrations) | API `actions/runs` |
| Backup DB | harian 03:00 → `D:\pims-backups\pims-YYYYmmdd-HHMMSS.sql.gz` (cron `pims-db-backup-daily`), simpan 7 terakhir | `gzip -dc … \| grep -c "CREATE TABLE"` |
| Frontend | `eslint` 0 error, `next build` hijau | `npm run lint && npm run build` |
| Migration head | `d2dcc981c45c` | `alembic current` |
| Endpoint terpasang | **59 operasi**; gap spec tersisa **9** (7 `watchlists` + `PATCH`/`DELETE` transaksi — keputusan owner) | openapi vs spec diff |
| Tabel | 22 | `__tablename__` + pg_tables |
| Dependency | terkunci di `backend/uv.lock` (PyPI-only) | `uv lock --check` |

## 1.1 Integrasi market data (audit 2026-11-25, bukti DB nyata + live Yahoo)

| Market | Status | Bukti |
|---|---|---|
| **CRYPTO** | Implemented + **live-verified** (Yahoo); Bybit adapter ada (mock-only, ISP blokir live) | DB: `BTCUSDT/ETHUSDT/SOLUSDT` → mapping `BTC-USD/ETH-USD/SOL-USD`; candle terakhir segar; quotes `is_realtime:false` + LIVE; live probe `BTC-USD` n=10, USD, close 58867 |
| **US STOCKS** | Implemented + **live-verified** (Yahoo, bukan Finnhub/Alpaca resmi) | Live probe `AAPL` n=10, USD, close 354.07 (market tutup → data kemarin); adapter `us_stocks/` kosong (Yahoo generic) |
| **IDX** | Implemented + **live-verified** (Yahoo, symbol `BBCA.JK`) | Live probe `BBCA.JK` n=10, IDR, close 5800 (sekarang); adapter `indonesia/` kosong (Yahoo generic) |

Catatan jujur: US/IDX **bukan** integrasi provider resmi (Finnhub/Alpaca/IDX API) — Yahoo adalah provider live. Verifikasi 2026-11-25 08:20 UTC: ketiga market mengembalikan data segar (lihat P3). Tak ada adapter khusus US/IDX — Yahoo `fetch_klines(instrument)` generic.

## 1.2 Scanner (audit 2026-11-25)

- Sudah benar: provider isolation (`load_candles` per `provider_id`), `MIN_CANDLES=50` guard, skipped reasons, ranking traceable (`rank/score/metric_snapshot/data_timestamp`), `freshness_status`.
- Temuan: (1) provider selection `service.py:80-81` pakai `market.code` — aset `market_id=NULL` salah provider; (2) 8 skenario integration test belum ada; (3) **InFailedSqlTransaction**: `except` block tak rollback session → aborted transaction meracuni query berikutnya (`test_scanner_provider_timeout` CI #40/#41).
- **P2 SELESAI** `7e2f6f4`: fix `is_crypto = asset.asset_type == "CRYPTO"` + fallback provider + 10 integration test.
- **P0-scanner SELESAI** `10f9871`: `session.rollback()` di kedua `except` block (`load_candles` + `run_instrument_engines`), bounded (tak buang ScannerRun); test patch `app.engines.runner.load_candles` (module benar). 10/10 scanner isolated passed.

## 2. Milestone selesai

- **Phase 0–2**: fondasi Next 16 + FastAPI, schema 15 tabel awal, Alembic.
- **Phase 3 (portfolio, Stage A–S)**: schema §5, engine WAC/holdings/valuation, REST portfolio/transaksi/holdings/valuasi, Asset API §11, guard cash & SELL, snapshot, performa TWR, alokasi, risiko (VaR/CVaR), analytics persistence, UI lengkap, scanner page, WebSocket market feed.
- **Phase 4/5 (parsial)**: market data Yahoo live (Bybit hanya mock — ISP), chart REST (WS = push polling yang dilabeli jujur).
- **Dokumentasi rilis**: `docs/user/PANDUAN_PENGGUNA.md`, `docs/RELEASE_NOTES_V1.md`, `docs/RELEASE_KNOWN_ISSUES.md`, `docs/security/...` (tidak ada; PIMS pakai `technical-decisions §7.x`).

## 3. Task ledger

| ID | Tujuan | Prioritas | Status | File | Review |
|---|---|---|---|---|---|
| U | 16 endpoint read-only (dashboard 5, markets 3, candles/asset, research list+delete, scanner 3) | P1 | **SELESAI** `e07956e` (pushed) — suite 189 passed | router API + test baru | lulus: 189 passed, 40 path/46 operasi |
| X | Index `market_candles(asset_id,timeframe,open_time)` + hilangkan N+1 di holdings/valuation/allocation + ukur sebelum/sesudah | P1 | **SELESAI** `5516a29`+`b4b0cdf`+`420603b` (pushed) — suite 190 passed; index terjustifikasi di `technical-decisions §7.14` | migration `2462e115ce2f`, repo batch, `test_query_budget.py` | lulus: 190 passed, query konstan 10 vs 30 posisi |
| V | Migration `market_quotes`, `fx_rates`, `scanner_configurations` (§6.1/§6.4/§8.1) + endpoint quote & CRUD config | P2 | **SELESAI** `d2dcc981c45c` (Stage V) — ingestion quote/FX ada, cron `ingest-pims-market-data-hourly` | migration, models, repos, API | lulus: endpoint quote 200, fx=12, quotes=99 di DB nyata |
| P3 | Real integration test `PIMS_REAL_PROVIDER=1` (Yahoo live, tanpa DB write) | P3 | **SELESAI** — gate skipif benar (skip tanpa key), live probe 2026-11-25: BTC-USD/AAPL/BBCA.JK semua n=10 + currency benar (USD/USD/IDR) | `tests/test_real_integration.py` | lulus: live probe 3 market segar |
| P4 | Sinkronisasi docs status (state doc §1/§1.1/§1.2/§3, api-spec §17 deferred, technical-decisions §7.17) | P1 | **SELESAI** 2026-11-25 — semua angka sinkron dgn commit `dda517c` + CI #37 | docs | lulus: docs sinkron |
| W | Analytics instrument-scope + **watchlists** (butuh keputusan: tabel tidak ada di schema-spec) | P2/P3 | **DEFERRED** (keputusan owner 2026-11-25 via audit GPT): single-user, tak ada tabel `users`; PIMS single-user. Tandai `DEFERRED/NOT IMPLEMENTED` di api-spec §17 tanpa ubah kontrak. Kriteria aktivasi: selesai P2/P3 + owner setujui skema dua-tabel (`watchlists` + `watchlist_items`, tanpa `user_id`). | `api-spec.md §17` (ditandai deferred) | keputusan: tunda; skema 2 tabel disepakat di `technical-decisions` |
| P0 | Perbaiki `test_ingest_quotes_timeout_failed` (fixture `Market CRYPTO` tak ada → `AttributeError`) | P0 | **SELESAI** `dda517c` (pushed) — CI #37 hijau, suite 270 passed | `test_market_ingestion.py` | lulus: test terisolasi passed, suite 270/0/1, CI #37 success |
| P2 | Hardening scanner: perbaiki provider-selection edge (`market_id=NULL`) + 10 integration test (crypto/US/IDX/mixed/missing/insufficient/timeout/stale/currency/isolation) | P2 | **SELESAI** `7e2f6f4` (pushed) — 10/10 scanner test passed | `scanner/service.py`, `tests/test_scanner_integration.py` | lulus: 10 scanner test passed; fix: fallback provider selection |
| P0-scanner | Perbaiki `test_scanner_provider_timeout` InFailedSqlTransaction (CI #40/#41 gagal) | P0 | **SELESAI** `10f9871` (pushed) — `service.py` rollback setelah exception di kedua `except` block (bounded, tak buang ScannerRun); test patch `app.engines.runner.load_candles` (module benar) | `scanner/service.py`, `tests/test_scanner_integration.py` | lulus: 10/10 scanner isolated; 52/53 combined (1 fail = dirty-DB suite order, bukan CI); market ingestion 23/23 |
| P4-audit | PIMS CI recovery + autonomous engineering (brief GPT 2026-11-25): fix CI failure, validasi, audit scanner, market reality, docs audit | P0/P1/P2/P3 | **SELESAI** `9469e49` — P0-scanner fixed (`10f9871`, CI #42 hijau); P2 scanner audit done (10/10 test); P3 market reality: CRYPTO/US/IDX live-verified Yahoo; P4 docs audit: spec↔impl sinkron (59 op, 9 gap by-design, watchlist deferred) | `scanner/service.py`, `tests/test_scanner_integration.py`, docs | lulus: CI #42 success; 10/10 scanner; market 23/23 |
| M1-corr | **Correlation Engine** (roadmap engine #1, spec lengkap 972 baris): model `CorrelationResult` (§7.5) + migration + engine (Pearson §4.2, simple/log return §5, bucketed common-alignment §6, rolling) + endpoint `/analytics/correlation` (persist `analytics_runs` CORRELATION + `correlation_results`) | P1 | **SELESAI** `36b417f` (pushed, CI #46) — deterministik, tanpa network; 15/15 test (pure math + endpoint + e2e persistence); test stub lama di-update (NOT_IMPLEMENTED → INSUFFICIENT_DATA) | `models/analytics.py`, `migrations/8f3a2d91`, `engines/correlation/engine.py`, `api/rest/analytics_v2.py`, `tests/test_correlation_engine.py`, `tests/test_analytics_api.py`, `tests/conftest.py` | lulus: 15/15 correlation; migration upgrade OK; endpoint persist nyata |
| M3-scanner-trigger | Wire scanner-trigger untuk AI Research: `run_scanner` auto-buat `ResearchRequest` (trigger_type=SCANNER) untuk hasil dengan score >= `research_min_scanner_score` (flag `research_scanner_trigger_enabled` default OFF) | P1 | **SELESAI** `4f94bc3` (pushed) — `_maybe_trigger_research` di `scanner/service.py` (setelah persist, outcome di `execution_metadata.research_triggered`); import `create_request` top-level; skor di-guard `isinstance` (tolerant terhadap mocked settings); None-safe `request.id`. 3 test M3 baru (enabled/disabled/below-threshold); 7 test lama scanner di-set flag=False agar path baru tak aktif. Orchestrator tetap owner dedup/cooldown/readiness-gate. | `scanner/service.py`, `tests/test_scanner_integration.py` | lulus: 13/13 scanner; 51/51 combined (scanner+correlation+research+analytics) |
| M2-ai-research-audit | Audit jalur AI Research (P3 brief GPT #2): verifikasi mock vs nyata + gap | P3 | **SELESAI** (audit) — AI Research **BUKAN mock**: orchestrator (readiness gate, dedup, fingerprint, cooldown, lifecycle 9 status, bounded retry, provider gate) + qualification + openai_compat + context_builder + report_generator + 2 test. Gap: (1) scanner-trigger wiring — **selesai di M3**; (2) spec §26 "Decisions Requiring Approval" (11 item: LLM provider, retention, data-sharing, dll) — **butuh approval owner**, tak boleh di-otonomi | `app/ai/*`, `specifications/engines/ai-research-spec.md` | lulus: arsitektur trigger-based sesuai brief P3; 11 decision teridentifikasi |
| M4-gap-proposals | Susun 7 technical gap proposal (Option B, 14 section) untuk engine backtesting/factor/attribution/scenario/fundamental/macro/sentiment + catat decision §26 owner di `technical-decisions.md` | P1 | **SELESAI** (proposed, menunggu approval) — 7 file di `docs/management/m4-gap-proposals/` (1-4 ready-after-approval, 5-7 deferred); decision §26 owner tercatat di `docs/decisions/technical-decisions.md` §7.18. Prioritas owner: Backtesting→Factor→Attribution→Scenario; Fundamental/Macro/Sentiment deferred | `docs/management/m4-gap-proposals/*`, `docs/decisions/technical-decisions.md` | lulus: 7 proposal + INDEX; decision owner terdokumentasi; tak ada code engine baru (menunggu approval) |
| M4-backtest | **Backtesting Engine Phase 1** (prioritas #1, metodologi baseline di-approve owner): model `BacktestMetrics` + migration `5c7e2a90` + engine deterministik (BUY_HOLD / STATIC_WEIGHT, cost model fee+slippage bps, look-ahead guard UNCLOSED, walk-forward 70/30) + endpoint `POST /analytics/backtest` (persist `analytics_runs` BACKTESTING + `backtest_metrics`) | P1 | **SELESAI** (pushed) — deterministik, tanpa network; 9/9 test (pure math + endpoint + persistence); unknown-symbol guard (`InsufficientData` bukan KeyError); envelope error `resp["error"]["code"]`. Phase 2 (rule-based) GATED — belum diimplement | `models/analytics.py`, `migrations/5c7e2a90`, `engines/backtesting/{__init__,engine}.py`, `api/rest/analytics_v2.py`, `tests/test_backtest_engine.py` | lulus: 9/9 backtest; 71/71 combined (backtest+correlation+scanner+analytics+market); migration upgrade OK |
| M4-factor | **Factor Engine Phase 1** (prioritas #2): model `FactorResult` + migration `9b4f1c6e` + engine (MOMENTUM/REVERSAL/VOLATILITY/SIZE, z-score+rank normalization, equal-weight composite, missing-data exclusion, look-ahead CLOSED-only) + endpoint `POST /analytics/factor` (symbol_map response) | P1 | **SELESAI** (saya, commit 3bcd936, pushed) — 9/9 test; composite Phase 1 = EQUAL only; `INSUFFICIENT_DATA` saat candle tak cukup | `models/analytics.py`, `migrations/9b4f1c6e`, `engines/factor/{__init__,engine}.py`, `api/rest/analytics_v2.py`, `tests/test_factor_engine.py` | lulus: 9/9 factor; CI #53 green |
| M4-attribution | **Attribution Engine Phase 1** (prioritas #3): model `AttributionResult` + migration + engine asset-level (contribution=w_j*r_j, konservasi sum=R, active vs benchmark) + endpoint `POST /analytics/attribution` | P1 | **SELESAI** (OpenCode dd16367 + audit saya a1c10b3, pushed) — commit OpenCode tak lengkap (model/endpoint/runner uncommitted), saya selesaikan; 9/9 test | `models/analytics.py`, `engines/attribution/engine.py`, `api/rest/analytics_v2.py`, `runner.py`(candle_status), `tests/test_attribution_engine.py` | lulus: 9/9 attribution; CI #54 green |
| M4-scenario | **Scenario Engine Phase 1** (prioritas #4): model `ScenarioResult` + migration `b3c4d5e6` + engine (SENSITIVITY direct+korelasi M1, HISTORICAL replay, hypothetical GATED) + endpoint `POST /analytics/scenario` | P1 | **SELESAI** (OpenCode cb3e98c + test saya 7df1f9e, pushed) — OpenCode tak bikin test file, saya tulis 6 test; hypothetical → INVALID_CONFIG (owner-gated) | `models/analytics.py`, `migrations/b3c4d5e6`, `engines/scenario/engine.py`, `api/rest/analytics_v2.py`, `tests/test_scenario_engine.py` | lulus: 6/6 scenario; 50/50 combined (scenario+attribution+factor+backtest+correlation+snapshot); CI #55 |
| M4-audit-note | **Catatan audit OpenCode** — commit OpenCode berulang kali TIDAK lengkap (Attribution: 5 file uncommitted; Scenario: tak ada test). Pola fix: OpenCode tulis engine, saya lengkapi (model/endpoint/test/snapshot) + verifikasi test nyata + `git status` bersih. Brief mulai 2026-11-25 mewajibkan "COMMIT LINGKUP LEBAR + git status bersih + test". Fundamental/Macro/Sentiment = DEFERRED (perlu approval data provider + metodologi) | P1 | tercatat | `docs/management/m4-gap-proposals/*` | — |
| M4-full-suite | **Full regression suite (2026-11-25)** — seluruh `tests/` (deselect `test_api_llm_research.py` + `test_m1_ingestion.py`): **331 passed, 1 skipped, 0 failed** (9 mnt). Verifikasi 4 engine M4 + scanner P2/P0 + M3 orchestration + semua endpoint tak rusak | P1 | SELESAI | `tests/` (penuh) | lulus: 331/331, CI hijau |
| M4-decisions-owner | **Keputusan owner (2026-11-25, Hermes putuskan + catat):** Docker = STOP (butuh admin+reboot WSL2/VT-x, tak diinstall ulang); umkm-manager = BUKAN project (owner pindah ke PIMS, tak akan disentuh); Fundamental/Macro/Sentiment = TUNDA (blocked: data provider + API key + metodologi §26, tak bisa di-otonomi). Backtesting Phase 2 (rule-based) + Scenario hypothetical = GATED §26 | P1 | menunggu owner | `docs/management/m4-gap-proposals/05-07`, `technical-decisions.md §7.18` | — |
| M4-fundamental | **Fundamental Engine Phase 1 (M4 #5) — approval owner-delegate (2026-11-25).** Owner (user) instruksi: "saya bos terakhir yang malas, anda putuskan, saya anggap approve". Keputusan Hermes: source = **Yahoo Finance** (sudah provider PIMS, tak perlu key baru); metrik **P/E + ROE + revenue-growth**; scoring z-score + ranking; cadence harian; UNAVAILABLE (bukan 0) saat data tak ada. Macro = tunda (butuh FRED API key owner). Sentiment = menyusul (RSS + LLM agnes, terikat §26). Dispatch ke OpenCode **session P2** `ses_dee3eed4...` (sesuai aturan 1-session). **STATUS: SELESAI + CI** (OpenCode commit `40220da` + fix Hermes `8941001`+`1a1951b`, push) — 8/8 test (fundamental+snapshot). BUG OpenCode yang saya perbaiki: (a) OpenCode **menghapus migration scenario `b3c4d5e6`** (regresi fatal, chain terputus) → saya revert; (b) OpenCode bikin migration fundamental dengan revision id **duplikat `b3c4d5e6`** + down_revision salah (lewati scenario) → saya rename ke `c5d6e7f8` (down=b3c4d5e6). Jejak ini untuk session Telegram `20261125_155751_ff8e10c9` | P1 | SELESAI | `engines/fundamental/*`, `models/analytics.py`, `migrations/c5d6e7f8`, `api/rest/analytics_v2.py`, `tests/test_fundamental_engine.py` | lulus: 8/8 fundamental+snapshot; migration head tunggal c5d6e7f8; CI #59/#60 |
| M4-sentiment | **Sentiment Engine Phase 1 (M4 #7) — approval owner-delegate (2026-11-25).** Keputusan Hermes: source = **RSS berita** (tak perlu key); model = **LLM agnes-3.0-flash** (key sudah di-env, pakai jalur `app/ai/`); scope headline EN/ID; agregat skor tertimbang confidence; terikat **§26 external-data-sharing (strict)**. Tak ada headline/LLM gagal → UNAVAILABLE + reason (bukan skor acak). Dispatch OpenCode **session P2**. **STATUS: SELESAI + pushed** (OpenCode commit `b49efe9`, push) — round ini BERSIH: commit lengkap (`git status` kosong), migration `d6e7f8a9b0c1` (rev baru, tak duplikat, down=c5d6e7f8), 10 test, §26 sanitasi di-test. Audit Hermes: migration head tunggal d6e7f8, 0 placeholder, **18/18 lulus** (sentiment 10 + fundamental 8 + snapshot). Jejak untuk `20261125_155751_ff8e10c9` | P1 | SELESAI | `engines/sentiment/*`, `models/analytics.py`, `migrations/d6e7f8`, `api/rest/analytics_v2.py`, `tests/test_sentiment_engine.py` | lulus: 18/18 sentiment+fundamental+snapshot; migration head tunggal d6e7f8; push b49efe9 |
| Y | Sinkronisasi dokumen tiap tahap + laporan test rilis | P1 | planned | docs | — |
| Z | Docker dev environment | P3 | **ditunda owner** (butuh reboot fisik + WSL2) | — | — |

## 4. Insiden & pemulihan 2026-11-22 — database dev `pims` hilang

- **Apa yang terjadi:** di tengah ronde "bersih-bersih DB" untuk reproduksi CI, seluruh tabel aplikasi di `pims` hilang (tersisa hanya `alembic_version` di `d2dcc981c45c`). DB `pims_test` (25 tabel) aman; `pims_ci` tidak ada.
- **Data hilang permanen:** portfolio, transaksi, holdings, snapshot, candle, quote, hasil analytics. Tidak ada backup saat itu (dicek: tidak ada `.dump`/`.sql`) → tidak dapat dipulihkan.
- **Pemulihan yang dilakukan (terverifikasi):** `alembic stamp base` → `upgrade head` → 25 tabel; seed referensi provider `BYBIT`/`YAHOO`, aset `BTCUSDT`/`ETHUSDT`/`SOLUSDT`, 6 mapping `provider_instruments`; ingestion dijalankan ulang → candle **900** baris, quote **3**, FX **1**, `failed: []`; `GET /market-data/quotes` → 200 (`last 69.02 USD`, `is_realtime: false`).
- **Pencegahan:** backup harian otomatis 03:00 (cron `pims-db-backup-daily`, `ea2f8e5878fe`) ke `D:\pims-backups\` (dump diverifikasi berisi 25 `CREATE TABLE` + 25 blok `COPY`), retensi 7 file. Aturan keras: dilarang `DROP`/`TRUNCATE`/`DELETE` massal, `alembic downgrade`/`stamp` pada `pims` dan `pims_test`; eksperimen destruktif hanya di DB sekali-pakai `pims_scratch_*`.

- **SELESAI (`141c3b8`): schema drift + FX commit.** `MarketQuote` punya `is_realtime`/`feed_status` yang **tidak ada di `schema-spec` §6.1** dan tidak dibuat migrasi mana pun → INSERT/SELECT ORM gagal di DB nyata (API `/market-data/quotes` sempat **500**). Kolom karangan dihapus dari model/repo/endpoint; `is_realtime` kini konstanta properti feed di response. `ingest_fx_rates` tidak pernah `commit()` → `fx_rates` kosong walau laporan `written: 1`; sudah diperbaiki dan diverifikasi (`fx_rates` = 1, USD/IDR 18158.0). Test anti-drift baru: `backend/tests/test_model_drift.py` (kolom model vs spec) + test persistensi FX lewat koneksi baru.
- **Baseline sekarang: 208 passed, 0 failed** (suite serial). Verifikasi nyata: `GET /market-data/quotes` 200, `last 58849.37 USD`, `freshness_status LIVE`, `is_realtime false`.
- **SELESAI (`19ac421`): candle ingestion CLI + schedule.** `python -m app.data.ingestion.candles --timeframe 1h --limit 300` memakai `refresh_asset_candles` (resolve simbol lewat `provider_instruments`, aset tanpa mapping → `skipped` + alasan, 404 → `skipped`, error transport → `failed`, JSON ringkas satu baris). Bukti nyata: `written: 960` untuk BTCUSDT/ETHUSDT/SOLUSDT dari Yahoo, `skipped: 3` (B2/B3/B4). Test `test_candle_ingestion.py` 5 buah (sukses, tanpa mapping, simbol provider benar-benar dipakai, 404→skipped, error transport→failed).
- **Cron per jam sekarang menjalankan candles → quotes → FX** (`ingest-pims-market-data-hourly`), tetap pola watchdog: hanya bersuara bila ada `failed` atau `written == 0`.
- **Baseline sekarang: 213 passed, 0 failed** (suite serial). Verifikasi nyata: valuation portfolio `COMPLETE` dengan harga pasar asli (`BTCUSDT 58989.96875`, `total_value 118777.9375`), halaman `/portfolios` + `/portfolios/[id]` + `/scanner` render di browser lewat `127.0.0.1` maupun `localhost`, `next build` hijau, `eslint` 0 error.
- **Pelajaran penting (jangan diulang):** DB test dibangun dari model, jadi **test hijau tidak membuktikan DB nyata sinkron dengan migrasi**. Setiap perubahan model wajib diuji terhadap DB nyata (`pims`), bukan hanya `pims_test`.
- **Cron ingestion** (`ingest-pims-market-data-hourly`, `41ccd6a31a0a`) sempat gagal karena mewarisi `PYTHONPATH` venv Hermes (`ImportError: cannot import name 'ArgsKwargs' from pydantic_core`); script kini membuang `PYTHONPATH`/`PYTHONHOME` untuk proses anak — sudah diverifikasi dengan simulasi env cron.
- **Utang teknis tercatat:** (1) penjadwalan analytics/snapshot masih manual; (2) `analytics_runs`/penjadwalan ingestion belum punya retry/backoff.
- **Aturan proses:** (1) JANGAN menjalankan `pytest` bersamaan dengan ronde OpenCode — sama-sama memakai DB `pims_test` dan menghasilkan `ForeignKeyViolation`/`UniqueViolation` palsu. (2) OpenCode dilarang `git checkout <sha>`: dulu commit-nya jatuh di detached HEAD sehingga cron push gagal (`'HEAD:refs/heads/HEAD'`); kerja selalu di branch `master`.

- `market_quotes`/`fx_rates`/`scanner_configurations`: dibuat di Stage V (`d2dcc981c45c`); **ingestion quote/FX ADA** (`eaec4f6`) dan **dijadwalkan tiap jam** lewat cron `ingest-pims-market-data-hourly` (watchdog, hanya bersuara bila gagal).
- `watchlists`: 6 endpoint di `api-spec` tanpa tabel di `schema-spec` → **konflik dokumen**, belum dikerjakan.
- Engine `correlation`, `factor`, `sentiment`, `macro`, `backtesting`, `attribution`, `scenario` masih kosong (belum ada rumus di spec).
- `ruff B008` (pola `Depends()` FastAPI) belum dikonfigurasi eksplisit.
- `market_quotes` freshness → `/markets/status` masih diturunkan dari candle.
- ~~Tidak ada CI; verifikasi manual~~ **USANG (histori):** sekarang ada CI di `.github/workflows/ci.yml` (hijau) dan `scripts/verify_all.sh` portabel (Tests/Linting/Build/Dependencies PASSED).
- Bybit live belum teruji (blokir ISP); LLM research baru jalur mock.

## 5. Keputusan teknis yang sudah diambil (lihat `technical-decisions.md` §7.6–§7.13)

WAC cost basis · TWR utama + RFR 0 + CAGR ≥365 hari · risk `current_weights_buy_and_hold_approximation` + VaR historis · alokasi aktual saja (target/rebalance tidak dispesifikasi) · no margin & no overdraft · snapshot/analitik manual · `uv.lock` di-commit · Docker ditunda owner · exchange = `markets.code`.

## 6. Blocker yang menunggu Product Owner

1. **Watchlists**: setujui penambahan tabel ke `schema-spec` (lalu diimplementasi) atau tunda.
2. **Docker**: dikerjakan saat owner di depan laptop (admin + reboot).
3. Metodologi lanjutan bila diminta: MWR/IRR, beta/benchmark, FX multi-currency, penjadwalan otomatis.

## 7. Aturan operasi (jangan dilanggar)

- OpenCode menulis kode; Hermes menulis brief + verifikasi sendiri (bukan percaya laporan).
- Setiap klaim file wajib bukti `git status --short` + `git diff --stat HEAD`.
- Dilarang mematikan proses berdasarkan nama (pernah membunuh router model 9router).
- Dilarang melemahkan/menghapus test; angka test harus ditempel nyata.
- Gagal-jujur: `null`/`UNAVAILABLE` + alasan, tidak pernah 0 atau angka karangan.
- Push hanya lewat SSH; commit + push tiap tahap selesai.

## 5. Gap kontrak API (audit `backend/scripts/audit_api_contract.py`)

- Alat: `cd backend && ./.venv/Scripts/python.exe scripts/audit_api_contract.py` (normalisasi `{param}` → `{}`, jalan dari `backend/` maupun root).
- Kondisi `96deb9b`: spec 54 · app 59 · gap (a) **9** · gap (b) 14.
- 9 gap tersisa: 7 endpoint `watchlists` (api-spec §17, `schema-spec` tanpa tabel → keputusan owner) + `PATCH`/`DELETE /transactions/{id}` (menyentuh integritas ledger → keputusan owner).
- Ditutup aditif: 6 `GET /analytics/*` + `POST/GET /research`, `GET /research/{id}`; `correlation` = `NOT_IMPLEMENTED` jujur (belum ada rumus di spec), tercatat di `RELEASE_KNOWN_ISSUES.md`.
- CI: kegagalan didiagnosis lewat annotation (`::error::` → `/commits/<sha>/check-runs` → `/check-runs/<id>/annotations`), bukan log (butuh token).
