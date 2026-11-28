# PIMS — QA Report (Sakti / Penguji QA & Keamanan)

Tanggal: 2026-11-28 (±13:00–14:00 WIB)
Repo: `D:/personal-investment-management-system`
Backend: FastAPI + SQLAlchemy 2 + PostgreSQL 17 (`pims_test`)
Scope: komponen stabil — portfolio, scanner, analytics M4 (attribution/backtest/factor/scenario/sentiment/fundamental/correlation/risk/allocation), market ingestion, API/WS.
**Di luar scope:** M4 Macro Engine (FRED) — masih dikerjakan Raka; hanya ikut terpanggil saat full-suite (dicatat sebagai info, bukan verdict QA).

Guardrail dipatuhi: tidak push, tidak ubah `.env`, tidak hapus file, tidak `git checkout`, tidak ada perubahan kode. Semua artefak QA ditulis di luar repo (`D:/temp/qa_*`) kecuali dokumen ini.

Skills dicek di `~/.config/opencode/skills`:
- `tdd` — ada, **tidak dipakai** (QA run ini tidak menulis kode/test baru).
- `simplify-code` — **tidak ada** di direktori skill (tidak terinstal).
- Dipakai: tidak ada skill file; hanya `pytest` + `ruff` bawaan venv.

---

## 0. Catatan metodologi (penting)

Suite memakai satu database bersama `pims_test` dan TRUNCATE per test. Saat QA, Raka menjalankan suite paralel beberapa kali; dua run QA pertama **tidak valid** karena deadlock/`UndefinedTable` antar proses:

| Run | Waktu | Hasil | Status |
|---|---|---|---|
| Run A | 12:21:36–12:31 | 21 failed, 301 passed, 1 skipped, 62 errors | **INVALID** — overlap run Raka. Bukti error: `psycopg.errors.DeadlockDetected`, `relation "performance_results" does not exist` (proses lain `drop_all`) |
| Run B | 12:57:26–13:05 | 359 passed, 1 failed, 1 skipped, 7 errors | **INVALID** — run Raka masuk di tengah run (13:0x) |
| Run C | 13:20:01–13:26:10 | **377 passed, 1 failed, 1 skipped**, 369.18s | **VALID** — diverifikasi tidak ada proses pytest lain selama run |

Kesimpulan proses: **suite tidak aman dijalankan paralel** pada `pims_test` (bukan bug produk, tapi risiko operasional; lihat issue Q7).

---

## 1. Hasil test suite (autoritatif = Run C)

Perintah persis (sesuai penugasan):

```
backend/.venv/Scripts/python.exe -m pytest backend/tests/ -q --tb=line
```

| Metrik | Nilai |
|---|---|
| Total dikumpulkan | 379 |
| Passed | 377 |
| Failed | 1 |
| Skipped | 1 |
| Errors | 0 |
| Warnings | 184 |
| Durasi | 369.18 s |

Satu-satunya kegagalan:

- `backend/tests/test_correlation_engine.py::test_correlation_endpoint_persists_results`
- Error: `ModuleNotFoundError: No module named 'tests.conftest'` (baris 152: `from tests.conftest import synthetic_candles, to_storage`)
- Reproduksi: gagal bila dijalankan dari root repo (`pytest backend/tests/...`), **lulus** bila dijalankan dari `backend/` (`cd backend; ./.venv/Scripts/python.exe -m pytest tests/test_correlation_engine.py -q` → 15 passed). Jadi bug invokasi/path, bukan bug engine.
- Catatan: ini juga sebabnya klaim "full suite 367 passed" di `docs/REPORT_DEV.md` hanya benar jika CWD = `backend/`.

Info (bukan verdict QA): `backend/tests/test_macro_engine.py` (13 test) ikut lulus pada Run C.

Warnings yang perlu dibereskan (bukan failure): `fastapi.on_event` deprecated, `pytest-asyncio` `asyncio_default_fixture_loop_scope` belum diset, `starlette.testclient` + `httpx` deprecated, `sqlalchemy .distinct(<expr>)` deprecated (`app/api/rest/scanner.py:144`), pattern `elem.find(...) or ...` di `app/data/providers/news/rss.py:40-41` (truth-value test deprecated, akan berubah di Python mendatang).

---

## 2. Audit keamanan dasar

| # | Item | Expected | Actual | Hasil | Bukti |
|---|---|---|---|---|---|
| S1 | Tidak ada secret hardcoded di file tracked | 0 match | 0 match | **PASS** | `git grep -E 'PIMS_(LLM|FRED|BYBIT)_API_(KEY|SECRET)=.+'` → kosong; `git grep '(api_key\|api_secret\|password)=.<8+char>'` → kosong; pola `sk-*`, `AKIA*`, `ghp_*` → kosong; `test_no_hardcoded_credentials.py` lulus |
| S2 | `.env` tidak masuk repository | untracked + ignored | untracked, `.gitignore:23` = `.env` | **PASS** | `git ls-files | grep .env` → hanya `.env.example`; `git check-ignore -v .env` → `.gitignore:23` |
| S3 | `.env.example` hanya placeholder | nilai kosong/contoh | placeholder semua | **PASS** (dengan catatan S3b) | `.env.example` dibaca utuh |
| S3b | `.env.example` lengkap utk semua setting | semua var yang dipakai ada | `PIMS_FRED_API_KEY` **tidak ada** (dipakai `app/config/settings.py:35` + ada di `.env` lokal) | **FAIL (low)** | grep `fred_api_key` vs `.env.example` |
| S4 | Export/endpoint tidak bocor PII/credential | tidak ada endpoint export membocorkan data sensitif | Tidak ada endpoint export/CSV/download sama sekali (`grep export\|csv\|download` di `backend/app/` → 0 match) | **PASS (N/A)** | grep kosong |
| S5 | Body API tidak memuat DSN/credential/stack trace | tidak ada `postgresql`, `password`, `api_key`, `Bearer`, `Traceback` | Dashboard/portfolios body bersih (23/23 probe lolos) | **PASS** | `D:/temp/qa_integration.log` |
| S6 | Tidak ada SQL injection | semua query ter-parameterisasi | 0 f-string/format di `text()`/`execute()`; probe nama `QA'; DROP TABLE portfolios; --` tersimpan sebagai literal, tabel utuh, respons 201 | **PASS** | grep + probe |
| S7 | Error 500 tidak membocorkan detail internal | pesan generik | **14 tempat** mengembalikan `str(exc)` mentah ke client: `app/api/rest/analytics_v2.py:134,171,208,284,343,475,517,573,613,657,712,767` (`error_response("SERVER_ERROR", str(exc), 500)`) | **FAIL (medium)** | grep + baca file |
| S8 | Authentication/authorization pada endpoint sensitif | sesuai spec | Tidak ada auth di seluruh REST & WS (tidak ada middleware/dependency security). Risiko naik karena `backend/Dockerfile:15` bind `--host 0.0.0.0` dan `docker-compose.yml` publish `8000:8000` | **FAIL (high, jika diekspos ke jaringan)** | `app/main.py:46-76`; Dockerfile; compose |
| S9 | Port PostgreSQL tidak diekspos tanpa need | tidak dipublish | `docker-compose.yml` publish `5432:5432` (password via env `${POSTGRES_PASSWORD}`) | **FAIL (medium)** | `docker-compose.yml` |
| S10 | Endpoint memicu operasi mahal tidak bisa disalahgunakan | ada pembatas | `POST /api/v1/research` menjalankan LLM **sinkron** di handler, tanpa auth/rate limit → siapa pun yang bisa akses dapat membakar kredit LLM | **FAIL (medium)** | `app/api/rest/research.py:50-72`, `app/ai/research/orchestrator.py:200-223` |
| S11 | Input validation endpoint portfolios | tolak input invalid | `limit` di luar 1–200 → 422; `name` kosong/151 char → 422; `base_currency="usd"` → 422; field ekstra → 422; UUID invalid → 404 | **PASS** | probe 23/23 |
| S12 | Input validation endpoint transactions | tolak input invalid | `transaction_type="HACK"` → 422; `quantity="abc"` → 422; portfolio tidak ada → 404; `limit=1000` → 422 | **PASS** | probe 23/23 |
| S13 | Batas panjang free-text & enum opsional | ada cap | `PortfolioCreate.description`, `TransactionCreate.notes`, `ResearchRequestBody.symbol/timeframe/request_summary`, `ScannerConfigCreate.name/description/timeframe/universe_config/filter_config` **tanpa** `max_length`/pattern; `ScannerConfigCreate` tanpa `extra="forbid"` | **FAIL (low)** | `app/schemas/portfolio.py:26-58`, `app/api/rest/research.py:23-28`, `app/api/schemas/scanner.py:4-21` |
| S14 | WS: batas subscription & validasi timeframe | ada cap + validasi | `subscribe` tidak dibatasi jumlah per koneksi; `params.timeframe` diterima string apa pun (`market.py:309`) | **FAIL (low-medium)** | `app/api/websocket/market.py:280-333` |
| S15 | Secret provider hanya dari environment | tidak di kode | `bybit_api_key`, `llm_api_key`, `fred_api_key` default `""` dari `Settings` env | **PASS** | `app/config/settings.py:23-36` |
| S16 | Tidak ada mode debug / traceback ke client | debug off | `FastAPI(title=..., version=...)` tanpa `debug=True`; tidak ada handler yang membocorkan traceback (kecuali S7) | **PASS** | `app/main.py:49` |
| S17 | CORS | tidak wildcard | Tidak ada `CORSMiddleware` (default: tanpa header CORS → browser tidak bisa cross-origin) | **PASS** | grep `allow_origins`/`CORS` → 0 |
| S18 | docker-compose meneruskan semua secret yang dipakai | var FRED ikut | `PIMS_FRED_API_KEY` tidak diteruskan ke service backend → `/api/v1/analytics/macro` akan UNAVAILABLE di container (gap fungsional untuk pekerjaan macro Raka) | **FAIL (low, fungsional)** | `docker-compose.yml` backend.environment |

---

## 3. Integration test (FastAPI TestClient, tanpa server)

Skrip: `D:/temp/qa_integration.py` (DB `pims_test`, 23 assertion). Hasil: **23 PASS / 0 FAIL**.

Endpoint prefix sebenarnya `/api/v1/...` — tugas menyebut `/api/portfolios` & `/api/dashboard`; path benar: `/api/v1/portfolios`, `/api/v1/dashboard/overview`. (`/api/portfolios` tanpa `v1` memang tidak ada.)

| No | Item | Expected | Actual | Hasil |
|---|---|---|---|---|
| 1 | `GET /health` | 200, status ok | 200 `{"status":"ok"}` | PASS |
| 2 | `GET /api/v1/portfolios` | 200 + envelope `data` | 200, `data`+`meta` | PASS |
| 3–5 | `limit=0`, `limit=999`, `limit=abc` | 422 | 422 | PASS |
| 6 | POST portfolio `name=""` | 422 | 422 | PASS |
| 7 | POST `base_currency="usd"` | 422 (pattern `^[A-Z]{3,5}$`) | 422 | PASS |
| 8 | POST field ekstra `is_admin` | 422 (`extra=forbid`) | 422 | PASS |
| 9 | POST name 151 char | 422 | 422 | PASS |
| 10 | POST nama berisi `'; DROP TABLE portfolios; --` | 201, tersimpan literal, skema utuh | 201, tabel utuh | PASS |
| 11 | `GET /api/v1/transactions?limit=1000` | 422 | 422 | PASS |
| 12 | POST transaction `type=HACK` | 422 | 422 | PASS |
| 13 | POST transaction `quantity="abc"` | 422 | 422 | PASS |
| 14 | POST transaction portfolio tak dikenal | 404 | 404 | PASS |
| 15 | `GET /api/v1/dashboard/overview` | 200 | 200, body agregat kosong | PASS |
| 16–21 | Body dashboard bebas `postgresql`/`password`/`api_key`/`PIMS_`/`Bearer`/`Traceback` | tidak ada | tidak ada | PASS (6×) |
| 22 | `dashboard/overview?portfolio_id=not-a-uuid` | 404 | 404 | PASS |
| 23 | `GET /api/v1/portfolios/zzz` | 404 | 404 | PASS |

Bukti mentah: `D:/temp/qa_integration.log`.

---

## 4. Lint & type check

| Item | Tool | Hasil | Catatan |
|---|---|---|---|
| Lint app | `ruff 0.17.5` | **FAIL** — 235 temuan `E,F,W`; 408 bila rule set diperluas | `backend/pyproject.toml` hanya set `line-length=100`,`target-version=py312`, **tidak ada `[tool.ruff.lint]` select** → tidak ada gate lint di repo |
| Lint tests | `ruff` | **FAIL** — 530 temuan `E,F,W` | dominan `E501`(269), `W293`(167), `F401`(57) |
| Type check | `mypy` | **TIDAK DIJALANKAN** | `mypy` tidak terpasang di `backend/.venv` dan bukan dependency proyek → typecheck tidak bisa dijalankan |

Rincian app (prioritas fix):

- `F401` unused import (28) — mis. `app/api/rest/scanner.py:17-19`, `app/api/rest/analytics_v2.py:20`, `app/engines/attribution/engine.py:20,29`, `app/engines/portfolio/service.py:12`, `app/engines/risk/portfolio_risk.py:42`, `app/api/schemas/scanner.py:1`.
- `F841` unused variable (9) — `app/ai/research/orchestrator.py:136` (`now`), `app/api/rest/scanner.py:214` (`market`), `app/data/ingestion/quotes.py:58` (`requested_ids`), `app/data/providers/crypto/yahoo.py:144` (`key_stats`), `app/engines/scanner/service.py:69,80`, `app/engines/backtesting/engine.py:261`, `app/engines/factor/engine.py:278`, `app/qualification/service.py:195`.
- `F811` redefinition `HTTPStatusError` — `app/data/ingestion/quotes.py:10`.
- `E712` perbandingan `== True` di query — `app/data/ingestion/candles.py:22`, `app/data/ingestion/quotes.py:39,41`, `app/engines/scanner/service.py:41,42,56`.
- `E501` line > 100 — 122 baris di app.

---

## 5. Daftar issue untuk Raka (prioritas)

| ID | Sev | File:line | Masalah | Perbaikan yang disarankan (bukan dikerjakan QA) |
|---|---|---|---|---|
| Q1 | High | `backend/Dockerfile:15`, `docker-compose.yml` | API tanpa auth bind `0.0.0.0` + publish port host; DB 5432 juga dipublish | Jangan publish `5432`; bind backend ke `127.0.0.1` untuk dev; tentukan kebijakan auth (atau dokumentasikan asumsi single-user + firewall) |
| Q2 | Medium | `backend/app/api/rest/analytics_v2.py:134,171,208,284,343,475,517,573,613,657,712,767` | `str(exc)` mentah ke response 500 → info disclosure (SQL/DSN/internal path) | Map exception ke kode error generik; log detail di server (`logger.exception`) |
| Q3 | Medium | `backend/tests/test_correlation_engine.py:152` | `from tests.conftest import ...` → `ModuleNotFoundError` bila pytest dijalankan dari root repo (satu-satunya test gagal) | import absolut dari paket test (`from conftest import ...` tidak portable) atau pindahkan helper ke `backend/tests/helpers.py` + tambah `tests/__init__.py`, lalu jalankan suite dari root |
| Q4 | Medium | `backend/tests/conftest.py:79-91` | Teardown `drop_all` meninggalkan `alembic_version` tetap stamped → `alembic upgrade head` jadi no-op dan `pims_test` kosong tanpa tabel; run QA/TestClient berikutnya crash `UndefinedTable` | Buang `drop_all` (cukup TRUNCATE), atau drop juga `alembic_version`, atau jalankan `create_all` di teardown |
| Q5 | Medium | `backend/app/api/rest/research.py:50-72` | LLM call sinkron di handler, tanpa auth/rate limit → abuse biaya & request timeout panjang | Enqueue job / timeout ketat; batasi trigger (policy `research_*` sudah ada, belum dipakai di endpoint) |
| Q6 | Low-Med | `backend/app/api/websocket/market.py:280-333` | Tanpa cap jumlah subscription per koneksi; `timeframe` tak divalidasi | Cap (mis. 20) + validasi timeframe ke set yang didukung engine |
| Q7 | Low-Med | proses QA | Suite tidak paralel-safe pada DB bersama `pims_test` (deadlock + drop_all antar proses) | Gunakan lock file/pg advisory lock saat run, atau DB per runner; dokumentasikan di README test |
| Q8 | Low | `app/config/settings.py:35` vs `.env.example` | `PIMS_FRED_API_KEY` (dan `PIMS_FRED_BASE_URL`) tidak ada di `.env.example`; `docker-compose.yml` tidak meneruskannya | Tambahkan ke `.env.example` (tanpa nilai) dan ke compose |
| Q9 | Low | `app/schemas/portfolio.py:34,58`, `app/api/rest/research.py:23-28`, `app/api/schemas/scanner.py:4-21` | Free-text tanpa `max_length`; `ScannerConfigCreate` tanpa `extra="forbid"`; `timeframe` tanpa enum | Tambah `Field(max_length=...)`, `extra="forbid"`, pattern enum |
| Q10 | Low | lint | 235 (app) / 530 (tests) temuan ruff; tidak ada gate lint di repo | Tambah `[tool.ruff.lint] select` + jalankan `ruff check`, `ruff format --check` di CI/pre-commit |
| Q11 | Low | `app/main.py:51`, `backend/pyproject.toml:26-28` | `@app.on_event("startup")` deprecated; `asyncio_default_fixture_loop_scope` belum diset (warning tiap run) | Migrasi ke `lifespan`; set `asyncio_default_fixture_loop_scope = "function"` |
| Q12 | Low | `app/data/providers/news/rss.py:40-41` | `elem.find(...) or ...` — truth-value Element deprecated (warning 90×/run) | Ganti `is not None` |

---

## 6. Tidak dijalankan / batasan QA

- Type check (mypy) — tidak terpasang.
- Dependency vulnerability scan (pip-audit) — tidak terpasang; tidak ditambahkan (guardrail: tanpa dependency baru).
- Frontend lint/build — di luar scope backend.
- Test integrasi provider live (network Bybit/Yahoo/FRED) — tidak dijalankan agar deterministik.
- Macro Engine (FRED) — tidak dinilai QA (pekerjaan Raka yang masih berjalan).

## 7. Ringkasan status

- Full suite (invokasi dari root, tanpa run paralel): **377 passed / 1 failed (Q3) / 1 skipped**. ⚠️ bukan 100% hijau.
- API integration + validasi input: **23/23 PASS**.
- Keamanan: tidak ada secret hardcoded; SQLi & traversal data bersih; **temuan utama: tanpa auth + bind 0.0.0.0 (Q1), kebocoran `str(exc)` (Q2), port DB dipublish**.
- Lint: belum bersih; typecheck tidak tersedia.
