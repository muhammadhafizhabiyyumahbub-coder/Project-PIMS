# PIMS — Autonomous Project State

**Diperbarui:** 2026-11-22 (Hermes sebagai Project Director, OpenCode sebagai implementasi)
**Repo:** `D:/personal-investment-management-system` · branch `master` · remote SSH `git@github.com:muhammadhafizhabiyyumahbub-coder/Project-PIMS.git`
**Status:** V1 Release Candidate + pengembangan lanjutan (roadmap baru)

---

## 1. Posisi terverifikasi

| Item | Nilai | Cara verifikasi |
|---|---|---|
| Commit terakhir | `ed11334` | `git log --oneline -1` |
| Backend test | **219 passed, 0 failed** (lokal) | `pytest -q` (PostgreSQL 17 lokal) |
| Bug P0 | ~~`POST /scanner/run` 500~~ **selesai** (`39058ef`, terverifikasi 200) | `curl -X POST /api/v1/scanner/run` |
| CI GitHub Actions | **aktif** (`.github/workflows/ci.yml`); `frontend` ✅, `backend` ❌ `Run tests` — `FileNotFoundError: site-packages/alembic.ini` (backend terpasang sebagai package, bukan editable) | API `actions/runs` |
| Backup DB | harian 03:00 → `D:\pims-backups\pims-YYYYmmdd-HHMMSS.sql.gz` (cron `pims-db-backup-daily`), simpan 7 terakhir | `gzip -dc … | grep -c "CREATE TABLE"` |
| Frontend | `eslint` 0 error, `next build` hijau | `npm run lint && npm run build` |
| Migration head | `d2dcc981c45c` | `alembic current` |
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