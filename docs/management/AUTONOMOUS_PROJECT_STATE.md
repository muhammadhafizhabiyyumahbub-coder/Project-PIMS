# PIMS — Autonomous Project State

**Diperbarui:** 2026-11-19 (Hermes sebagai Project Director, OpenCode sebagai implementasi)
**Repo:** `D:/personal-investment-management-system` · branch `master` · remote SSH `git@github.com:muhammadhafizhabiyyumahbub-coder/Project-PIMS.git`
**Status:** V1 Release Candidate + pengembangan lanjutan (roadmap baru)

---

## 1. Posisi terverifikasi

| Item | Nilai | Cara verifikasi |
|---|---|---|
| Commit terakhir | `b825565` | `git log --oneline -1` |
| Backend test | **197 passed, 0 failed** | `pytest -q` (PostgreSQL 17 lokal) |
| Frontend | `eslint` 0 error, `next build` hijau | `npm run lint && npm run build` |
| Migration head | `dcadf6176257` | `alembic current` |
| Endpoint terpasang | 46 operasi (40 path) dari 54 di `api-spec.md` | openapi vs spec diff |
| Tabel | 22 | `__tablename__` + pg_tables |
| Dependency | terkunci di `backend/uv.lock` (PyPI-only) | `uv lock --check` |

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
| V | Migration `market_quotes`, `fx_rates`, `scanner_configurations` (§6.1/§6.4/§8.1) + endpoint quote & CRUD config | P2 | **in progress** | migration, models, repositories, API | pending |
| W | Analytics instrument-scope + **watchlists** (butuh keputusan: tabel tidak ada di schema-spec) | P2/P3 | blocked (keputusan owner) | — | — |
| Y | Sinkronisasi dokumen tiap tahap + laporan test rilis | P1 | planned | docs | — |
| Z | Docker dev environment | P3 | **ditunda owner** (butuh reboot fisik + WSL2) | — | — |

## 4. Bug/weakness yang diketahui (jujur)

- **SELESAI (`790f25d`, `b825565`):** (a) cacat qualification tertutup — `_latest_scanner_result` join ke tabel salah (`AnalyticsRun` via `scanner_run_id`; seharusnya kolom `ScannerResult.timeframe` sendiri) sehingga selalu `None`; gate riset memblokir `PARTIAL` (kini blokir hanya `STALE`/`NOT_QUALIFIED`); `volatility=None` tidak lagi dianggap 0; risk/scanner sudah difilter timeframe. (b) test tambahan: 3 gate (READY+FAILED diblokir, volatility NULL, timeframe mismatch) + 4 Stage V (constraint `fx_rates`, freshness quote, `parse_float` anti-float, validasi scanner config 422/404).
- **Baseline sekarang: 197 passed, 0 failed** (suite serial, `b825565`).
- **Utang teknis tercatat:** `backend/app/api/rest/scanner.py:100` memakai `payload.dict(...)` (deprecated Pydantic V2) → ganti `payload.model_dump()`.
- **Aturan proses:** (1) JANGAN menjalankan `pytest` bersamaan dengan ronde OpenCode — sama-sama memakai DB `pims_test` dan menghasilkan `ForeignKeyViolation`/`UniqueViolation` palsu. (2) OpenCode dilarang `git checkout <sha>`: dulu commit-nya jatuh di detached HEAD sehingga cron push gagal (`'HEAD:refs/heads/HEAD'`); kerja selalu di branch `master`.

- `market_quotes`/`fx_rates`/`scanner_configurations`: **dibuat di Stage V** (`d2dcc981c45c`), tetapi ingestion quote/FX belum ada → endpoint baca bisa kosong (`data: null` + `UNAVAILABLE`) sampai job ingestion dibuat.
- `watchlists`: 6 endpoint di `api-spec` tanpa tabel di `schema-spec` → **konflik dokumen**, belum dikerjakan.
- Engine `correlation`, `factor`, `sentiment`, `macro`, `backtesting`, `attribution`, `scenario` masih kosong (belum ada rumus di spec).
- `ruff B008` (pola `Depends()` FastAPI) belum dikonfigurasi eksplisit.
- `market_quotes` freshness → `/markets/status` masih diturunkan dari candle.
- Tidak ada CI; verifikasi masih manual (`scripts/verify_all.sh` belum dibuat).
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