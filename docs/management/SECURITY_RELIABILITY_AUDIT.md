# Audit Keamanan & Reliabilitas PIMS (P7)

**Auditor:** Nadia subagent (Auditor Rumus & Rubrik — Kantor 2)
**Tanggal:** 2026-11-28
**Scope:** commit `84a3dda` (Q1+Q2), `708a06a` (FRED api_key), input validation, error handling, dependency audit
**Metode:** baca diff commit + verifikasi statis (grep/AST/YAML parse) + uji dinamis `TestClient` terhadap DB test (`pims_test`) + `pip-audit` terhadap `backend/.venv`
**Status keseluruhan: PARTIAL PASS** — 1 kritis, 3 tinggi, 6 sedang, 5 rendah.
**Catatan:** tidak ada kode yang diubah. Semua file probe sementara sudah dihapus.

---

## Ringkasan temuan

| ID | Severity | Temuan | Status |
|----|----------|--------|--------|
| C-1 | **KRITIS** | `api_key` FRED tetap bocor ke log (2 jalur: httpx INFO + `str(exc)` HTTPStatusError) | FAIL |
| H-1 | **TINGGI** | Frontend publish `3000:3000` + rewrite `/api/v1` → API tanpa auth tetap terjangkau dari LAN | FAIL |
| H-2 | **TINGGI** | `timeframe` di `POST /api/v1/research` tidak divalidasi → nilai sampah diterima (200) | FAIL |
| H-3 | **TINGGI** | Test Q2 hanya mencakup 3 dari 13 titik yang diperbaiki | PARTIAL |
| M-1 | SEDANG | Tidak ada test regresi untuk exposure docker-compose (Q1) | FAIL |
| M-2 | SEDANG | Bentuk respons 422 tidak konsisten (envelope vs `{"detail": ...}` Pydantic) | FAIL |
| M-3 | SEDANG | 500 yang tidak di-handle → `text/plain "Internal Server Error"`, di luar envelope | FAIL |
| M-4 | SEDANG | Docker image build `pip install .` tanpa lock → dependency image ≠ yang diaudit | FAIL |
| M-5 | SEDANG | Tidak ada global exception handler / logging terstruktur untuk 500 non-analytics | FAIL |
| M-6 | SEDANG | `get_db()` tanpa rollback eksplisit; tidak ada timeout connect/statement | FAIL |
| L-1..L-5 | RENDAH | lihat §G | INFO |

---

## A. Commit `84a3dda` — Q1 (exposure)

| # | Item | Expected | Actual | Pass/Fail | Bukti | Fix disarankan |
|---|------|----------|--------|-----------|-------|----------------|
| A1 | Port Postgres tidak dipublish | db tanpa `ports` | `services.db.ports = None`; tidak ada `5432` | **PASS** | `python -c "yaml.safe_load(...)"` → `db ports= None`, `db_published_5432= False`; `docker-compose.yml:9-16` | — |
| A2 | Backend bind host-local | `127.0.0.1:8000:8000` | `127.0.0.1:8000:8000` | **PASS** | `docker-compose.yml:27`; YAML parse `backend ports= ['127.0.0.1:8000:8000']` | — |
| A3 | `docs/SECURITY_NOTES.md` ada + isi Q1/Q2 | Dokumen ada, sebut 5432/127.0.0.1/13 titik | Ada (55 baris), §2 dan §3 lengkap, deviasi Dockerfile didokumentasikan | **PASS** | `docs/SECURITY_NOTES.md` §2–§3 | — |
| A4 | Tidak ada jalur eksposur lain ke API | Hanya loopback yang terjangkau | `frontend` publish `3000:3000` (semua interface) dan `next.config.ts:13` meneruskan `/api/v1/:path*` ke `backend:8000` → API tanpa auth terjangkau `http://<LAN-IP>:3000/api/v1/...` | **FAIL (H-1)** | `docker-compose.yml:39`; `frontend/next.config.ts:13`; `package.json` `"dev": "next dev"` (listen 0.0.0.0) | Bind frontend `127.0.0.1:3000:3000`, atau jalankan `next dev -H 127.0.0.1` |
| A5 | Ada test regresi untuk exposure | Test yang gagal bila `5432`/`0.0.0.0` kembali | Tidak ada test menyentuh `docker-compose.yml` | **FAIL (M-1)** | `grep -rln "docker-compose" backend/tests tests` → kosong | Tambah test parse YAML: assert `db.ports` kosong, backend prefix `127.0.0.1:` |
| A6 | Dockerfile tidak listen 0.0.0.0 | (instruksi Q1) `127.0.0.1` | Tetap `0.0.0.0` di dalam container; deviasi didokumentasikan (dibutuhkan `frontend -> backend`) | **PASS (dengan deviasi tercatat)** | `backend/Dockerfile:17`; `docs/SECURITY_NOTES.md` blockquote §2 | Butuh keputusan owner; alternatif: network compose terpisah + `--host 127.0.0.1` tidak mungkin lintas container |

Kesimpulan Q1: hardening inti benar, tetapi **tidak lengkap** karena jalur frontend (A4) membatalkan proteksi LAN, dan tidak ada test penjaga (A5).

---

## B. Commit `84a3dda` — Q2 (generic 500)

| # | Item | Expected | Actual | Pass/Fail | Bukti | Fix |
|---|------|----------|--------|-----------|-------|-----|
| B1 | 13 titik `str(exc)` pada 500 diganti | 12 analytics_v2 + 1 analytics | `grep -c "server_error(exc)"` → `analytics_v2.py:12`, `analytics.py:1`; `grep -rn 'error_response("SERVER_ERROR"' app` → hanya definisi di `envelope.py:39`; `grep 'str(exc), 500'` → 0 | **PASS** | commit `84a3dda`; grep di atas | — |
| B2 | Helper generik + log server-side | `logger.exception` + pesan generik | `server_error()` di `app/api/envelope.py:32-39` → `logger.exception(...)`, body `"Internal error (see server logs)"` | **PASS** | `envelope.py:32-39` | — |
| B3 | Test Q2 | Test membuktikan tidak ada kebocoran | `pytest tests/test_security_q2.py` → **3 passed** (dari `backend/`); DSN/`S3CRETPW`/`Traceback` tidak muncul di body, `error.message == "Internal error (see server logs)"` | **PASS** | run 2026-11-28; 3 passed in 14.26s / 14.33s | — |
| B4 | Cakupan test memadai | Minimal 1 test per pola handler (GET, POST/persist, engine, macro, backtest) | Hanya 3 endpoint: `analytics/risk`, `analytics/allocation`, `portfolios/{id}/analytics/runs`. 10 titik lain (technical, market_regime, backtest, attribution, fundamental, sentiment, macro, scenario, factor) tanpa test | **FAIL (H-3)** | `backend/tests/test_security_q2.py` (58 baris) vs 13 titik di grep | Parametrisasi test atas seluruh 13 titik, atau assert statis: tidak ada `str(exc)` dengan status 500 |
| B5 | Tidak ada sisa `str(exc)` di jalur 500 | 0 | 0 pada 500; 10 sisa `str(exc)` hanya pada 422 (`VALIDATION_ERROR`/`INVALID_CONFIG`/`INSUFFICIENT_DATA`) — pesan domain, bukan DSN | **PASS** | `grep -rn "str(exc)" app/api` → 10 (semua 422) + 1 komentar | Pertahankan; pastikan engine hanya melempar `ValueError` berisi pesan publik |

Kesimpulan Q2: implementasi benar dan terbukti untuk 3 jalur; cakupan test kurang (H-3).

---

## C. Commit `708a06a` — FRED `api_key`

| # | Item | Expected | Actual | Pass/Fail | Bukti | Fix |
|---|------|----------|--------|-----------|-------|-----|
| C1 | Pesan log hanya series, bukan URL | Format `"series %s"` | Sudah `"FRED fetch failed for series %s: %s"` di `fred.py:67` dan `fred_fetch.py:36` | **PASS** | diff `708a06a`; file saat ini | — |
| C2 | Tidak ada `api_key` di log | 0 kemunculan | **Bocor 2 jalur**: (a) httpx logger INFO mencetak URL penuh (query `api_key=...`); (b) `httpx.HTTPStatusError.__str__` memuat URL penuh, dan `logger.warning(..., exc)` menuliskannya | **FAIL (C-1)** | Repro `FREDAdapter(api_key=..., transport=MockTransport(401))`: `INFO httpx HTTP Request: GET https://api.stlouisfed.org/fred/series/observations?series_id=CPIAUCSL&api_key=a1b2c3d4SECRETFREDKEY&file_type=json "HTTP/1.1 401"` lalu `WARNING ... FRED fetch failed for series CPIAUCSL: Client error '401 Unauthorized' for url 'https://api.stlouisfed.org/fred/series/observations?...&api_key=a1b2c3d4SECRETFREDKEY...'` | Jangan log `exc` mentah: log `type(exc).__name__` + `exc.response.status_code`; kirim api_key via header (`Authorization`) atau redaksi query sebelum log; set `logging.getLogger("httpx").setLevel(WARNING)` di `configure_logging` |
| C3 | Test menjamin tidak ada kebocoran | Assert `api_key not in caplog.text` | `test_fred_adapter_http_error_is_logged` hanya assert `"CPIAUCSL" in calls[0]` — tidak memeriksa ketiadaan key | **FAIL** | `backend/tests/test_macro_engine.py:311-325` | Tambah assert `KEY not in str(calls[0])` + test caplog level INFO untuk logger `httpx` |
| C4 | `FREDAdapter` tidak memakai key kosong | return `[]` | `if not self.api_key: return []` | **PASS** | `fred.py:59-60`; `test_fred_adapter_empty_key_returns_no_data` | — |

Catatan: `docs/REPORT_DEV.md` (ditulis di commit yang sama) sudah menandai "httpx logs the full URL at INFO, including api_key" sebagai known issue — tetapi bug ini **belum diperbaiki** dan kini terbukti juga merembes lewat `str(exc)`.

---

## D. Audit input validation

Diuji dengan `TestClient` (DB `pims_test`). 12 probe sintaksis + 4 probe semantik.

| # | Endpoint / input | Expected | Actual | Pass/Fail | Bukti |
|---|------------------|----------|--------|-----------|-------|
| D1 | `POST /portfolios` body `{}` | 422 | 422 | **PASS** | probe |
| D2 | `POST /portfolios` `name=""` / `name` 200 char | 422 | 422 | **PASS** | probe |
| D3 | `POST /portfolios` `base_currency="usd"` (lowercase) | 422 (pattern `^[A-Z]{3,5}$`) | 422 | **PASS** | `app/schemas/portfolio.py:32` |
| D4 | `POST /portfolios` field asing (`bogus`) | 422 (`extra=forbid`) | 422 | **PASS** | `model_config = ConfigDict(extra="forbid")` |
| D5 | `POST /transactions` body `{}` / `transaction_type="HACK"` / `quantity="abc"` / field asing | 422 | 422 (semua) | **PASS** | `app/schemas/portfolio.py:44-58` |
| D6 | Transaksi semantik: `BUY quantity=-5` / `quantity=0` | 422 | 422 `BUSINESS_RULE_ERROR` / `NON_POSITIVE_AMOUNT` | **PASS** | probe: `"quantity and price must be positive"` |
| D7 | `SELL 9999` melebihi holdings | 422 | 422 `INSUFFICIENT_HOLDINGS` `"SELL 9999 exceeds available holdings 0"` | **PASS** | `app/engines/portfolio/service.py` |
| D8 | `DEPOSIT` membawa `quantity/price` | 422 | 422 `FIELD_NOT_ALLOWED` | **PASS** | probe |
| D9 | `POST /research` `{}` / `symbol=""` / field asing | 422 | 422 | **PASS** | `app/api/rest/research.py:26-32` |
| D10 | `POST /research` `timeframe="99z"` (symbol valid `BTCUSDT`) | 422 | **200** — job dibuat dengan status `BLOCKED`; timeframe sampah tersimpan di `research_requests` | **FAIL (H-2)** | probe: `RESEARCH_BAD_TF 200 {"data":{"action":"CREATED","job":{...,"status":"BLOCKED"...}}}`; `research.py:28` tanpa pattern/enum |
| D11 | `GET /analytics/risk?portfolio_id=not-a-uuid` | 422 + envelope | 422 envelope `VALIDATION_ERROR "invalid portfolio_id format"` | **PASS** | probe |
| D12 | `GET /analytics/technical?limit=1` (di bawah `ge=60`) | 422 | 422 tetapi bentuk Pydantic mentah `{"detail":[{"type":"greater_than_equal",...}]}` — bukan envelope | **FAIL (M-2)** | probe; `analytics_v2.py:266,325` |
| D13 | `GET /portfolios?limit=0` | 422 envelope | 422 `VALIDATION_ERROR "limit must be between 1 and 200"` | **PASS** | `portfolios.py:66-68` |

Fix H-2: `timeframe: Literal["1h","4h","1d"]` (atau reuse `TIMEFRAME_SECONDS` dari `app/data/validation/freshness.py`) di `ResearchRequestBody`.
Fix M-2: tambah `@app.exception_handler(RequestValidationError)` yang membungkus ke `error_response("VALIDATION_ERROR", ..., 422)`.

---

## E. Audit error handling (kebocoran internal pada 500)

Metode: monkeypatch dependency endpoint agar melempar `RuntimeError("postgresql://pims:S3CRETPW@db:5432/pims SELECT * FROM portfolios")`, panggil endpoint, periksa body terhadap marker `S3CRETPW`, `postgresql://`, `Traceback`, `SELECT * FROM`, `psycopg`, `site-packages`.

| # | Endpoint | Status/Content-Type | Kebocoran | Pass/Fail | Bukti |
|---|----------|---------------------|-----------|-----------|-------|
| E1 | `GET /analytics/risk` (engine gagal) | 500 `application/json`, `error.code=SERVER_ERROR`, pesan generik | Tidak ada | **PASS** | `backend/tests/test_security_q2.py` 3 passed |
| E2 | `GET /portfolios/{id}/holdings` (valuation gagal) | 500 `text/plain` `"Internal Server Error"` | Tidak ada | **PASS (bocor) / FAIL (kontrak, M-3)** | probe: `PORTFOLIOS_500 500 text/plain ... Internal Server Error` |
| E3 | `POST /transactions` (service gagal) | 500 `text/plain` `"Internal Server Error"` | Tidak ada | **PASS (bocor) / FAIL (kontrak, M-3)** | probe: `TRANSACTIONS_500 500 text/plain` |
| E4 | `POST /research` (orchestrator gagal, symbol valid) | 500 `text/plain` `"Internal Server Error"` | Tidak ada | **PASS (bocor) / FAIL (kontrak, M-3)** | probe: `RESEARCH_500_SEEDED 500 text/plain` |
| E5 | Handler global untuk 500 non-analytics | Ada handler yang menghasilkan envelope + log terstruktur | Tidak ada `exception_handler` maupun middleware; traceback hanya keluar lewat uvicorn default | **FAIL (M-5)** | `grep -rn "exception_handler\|middleware" app/` → kosong |
| E6 | Rollback sesi saat error | Rollback eksplisit | `get_db()` hanya `try/yield/finally: session.close()`; rollback bergantung pada `close()` implisit. Handler yang menangkap exception melakukan `db.rollback()` manual (baik), yang tidak menangkap tidak | **FAIL ringan (M-6)** | `app/core/db.py:35-40` |
| E7 | Timeout DB / pool | `connect_timeout`/`statement_timeout`, pool size eksplisit | Hanya `pool_pre_ping=True`; tanpa timeout → request bisa menggantung saat DB lambat | **FAIL (M-6)** | `app/core/db.py:18` |
| E8 | `server_error()` menulis detail ke log | Ada, tapi tidak boleh memuat secret | Traceback bisa memuat DSN pada `OperationalError` (server-side saja; bukan response) | **INFO** | `envelope.py:38` |

Fix M-3/M-5: satu `@app.exception_handler(Exception)` → `server_error(exc)` sehingga semua 500 berbentuk envelope.
Fix M-6: `create_engine(..., pool_size=5, max_overflow=10, connect_args={"connect_timeout": 5})` + `get_db` dengan `except: session.rollback(); raise`.

---

## F. Audit dependency (`pip-audit`)

| # | Item | Expected | Actual | Pass/Fail | Bukti |
|---|------|----------|--------|-----------|-------|
| F1 | Vulnerability di `backend/.venv` | 0 known vuln | **0** | **PASS** | `uvx pip-audit -r <freeze 44 paket>` → `No known vulnerabilities found` (2026-11-28) |
| F2 | Paket lokal `pims-backend` | Dilewati (bukan PyPI) | `pims-backend 0.1.0 — Dependency not found on PyPI and could not be audited` | **INFO** | output pip-audit |
| F3 | Dependency image = dependency yang diaudit | Build memakai lock | `backend/Dockerfile:9` `pip install --no-cache-dir .` → resolver mengambil versi terbaru saat build; `uv.lock` tidak dipakai | **FAIL (M-4)** | `backend/Dockerfile`; `backend/uv.lock` ada tetapi tidak direferensikan | 
| F4 | Pin versi minimum | Semua dependensi punya batas bawah | `pyproject.toml:8-18` semua `>=` (tanpa upper bound) | **INFO** | `backend/pyproject.toml` |

Fix M-4: `COPY uv.lock` + `uv sync --frozen` (atau `pip install --require-hashes -r requirements.lock`).

---

## G. Temuan rendah / catatan reliabilitas

| ID | Temuan | Bukti | Dampak | Fix |
|----|--------|-------|--------|-----|
| L-1 | Test suite tidak paralel-safe (dokumentasi QA lama) | `docs/REPORT_DEV.md` Appendix A; run paralel → `DeadlockDetected`/`UndefinedTable` | CI paralel bisa flaky | Jalankan serial / DB per-worker |
| L-2 | Migrasi alembic dijalankan saat startup app | `app/main.py:47` `run_migrations()` pada `@app.on_event("startup")` | Boot lambat, race bila >1 replika | Pindahkan ke entrypoint/CI step |
| L-3 | API tanpa auth + endpoint LLM hanya cooldown 900 s (Q5) | `settings.research_cooldown_seconds=900`; `research.py:58`; `SECURITY_NOTES.md` §4 | Biaya LLM bila terekspos | Sudah tercatat; tutup H-1 |
| L-4 | WebSocket tanpa auth/validasi channel (Q6) | `app/api/websocket/channels.py:53` | Terima pesan sembarang bila terekspos | Validasi channel + cap subscription |
| L-5 | Pesan 404/422 menggemakan input user (`portfolio_id` dsb.) | `portfolios.py:92` | Reflected string (JSON-escaped) — risiko rendah | Tidak perlu; pastikan frontend tidak render sebagai HTML |

### Status test suite saat audit
- `pytest tests/test_security_q2.py` → **3 passed**.
- Full suite (`backend/`, serial): **408 passed, 1 skipped in 593.60s**, exit 0. Angka > 397 karena working tree memuat pekerjaan watchlist yang belum di-commit (bukan bagian audit ini).
- Catatan: run penuh yang dijalankan **bersamaan** dengan probe audit menghasilkan puluhan `E`/`F` (interferensi DB) — konsisten dengan L-1, bukan regresi kode.

---

## H. Rekomendasi prioritas

1. **P0 (C-1):** hentikan kebocoran `api_key` FRED — jangan log `exc` mentah (ambil `status_code`), redaksi query `api_key` sebelum log, dan set `httpx` logger ke WARNING. Tambah test `KEY not in logs`.
2. **P1 (H-1):** bind frontend ke loopback (`127.0.0.1:3000:3000`) agar rewrite `/api/v1` tidak membuka API ke LAN.
3. **P1 (H-2):** validasi `timeframe` di `ResearchRequestBody` (`Literal["1h","4h","1d"]`).
4. **P2 (H-3, M-1, M-2, M-3, M-5):** perluas test Q2 (13 titik), test YAML compose, exception handler global (`RequestValidationError` + `Exception` → envelope), test anti-regresi `docker-compose`.
5. **P2 (M-4):** build image dari `uv.lock` (frozen).
6. **P2 (M-6):** rollback eksplisit di `get_db()` + timeout DB.

---

## I. Limitasi audit

- Tidak menjalankan `docker compose config`/container (Docker CLI tidak tersedia di host audit); verifikasi compose dilakukan via parse YAML.
- `pip-audit` memakai snapshot advisory saat eksekusi (2026-11-28); bukan jaminan masa depan.
- Uji 500 memakai monkeypatch untuk mensimulasikan kegagalan engine/DB, bukan kegagalan DB nyata.
- `backend/.venv` adalah environment yang diaudit; image Docker belum dibangun sehingga paket hasil resolusi build belum diverifikasi (lihat M-4).

*Nadia subagent — Auditor Rumus & Rubrik, Kantor 2.*
