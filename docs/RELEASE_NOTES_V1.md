# PIMS V1 — Release Notes

**Status:** Release Candidate — **belum dirilis**.
**Tanggal:** 19 November 2026

Dokumen ini merangkum fitur yang benar-benar ada pada kode saat ini, apa yang
belum ada, dan catatan schema/migration. Tidak ada klaim bahwa V1 sudah selesai
atau sudah dirilis.

---

## 1. Baseline terverifikasi

Diverifikasi ulang pada 19 November 2026 dengan perintah nyata.

Dependency backend dikunci di `backend/uv.lock` (disetujui Project Owner,
hanya merujuk `pypi.org` / `files.pythonhosted.org`, tanpa kredensial). Pasang
persis versi terkunci dengan `uv sync --frozen` sebelum menjalankan perintah
`uv run ...` di bawah.

### 1.1 Test backend

```text
$ cd backend
$ uv run python -m pytest -q
160 passed, 88 warnings in 160.62s (0:02:40)
```

Tidak ada test yang gagal. (PowerShell menampilkan status pipeline non-nol
karena pytest menulis warning ke stderr; ringkasan pytest tetap `160 passed`.)

### 1.2 Build frontend

```text
$ cd frontend
$ npm run build
...
Route (app)
┌ ○ /
├ ○ /_not-found
├   /instrument/[symbol]
│ └ ◐ /instrument/[symbol]
├ ○ /portfolios
├   /portfolios/[id]
│ └ ◐ /portfolios/[id]
└ ○ /scanner
```

Build berhasil.

### 1.3 Schema dan migration

```text
$ cd backend
$ uv run alembic history
a41c2e9f7b30 -> dcadf6176257 (head), add_performance_and_allocation_results
3374e73084c0 -> a41c2e9f7b30, portfolio domain tables (Stage A, schema-spec §5)
<base> -> 3374e73084c0, initial vertical slice schema

$ uv run alembic current
dcadf6176257 (head)
```

Jumlah tabel di schema `public`: **22** (21 tabel domain + `alembic_version`).

Tabel domain:

```text
allocation_results
analytics_runs
assets
cash_ledger
data_providers
holdings
market_candles
market_regime_results
markets
performance_results
portfolio_snapshots
portfolios
provider_instruments
research_jobs
research_reports
research_requests
risk_results
scanner_results
scanner_runs
technical_results
transactions
```

---

## 2. Fitur yang benar-benar ada

### 2.1 Market data

- Adapter provider: Bybit dan Yahoo Finance, dengan interface yang sama.
- Normalisasi OHLCV dan validasi data.
- Kebijakan freshness (`LIVE`/`STALE`/`UNKNOWN`).
- Endpoint candle historis dan refresh data.
- Kanal WebSocket `market` dengan protokol subscribe/unsubscribe/ping.
- Data feed dibaca dari database, bukan stream provider; setiap pesan menyatakan
  `is_realtime: false` dan `source: "rest_poll"`.

### 2.2 Chart

- TradingView Lightweight Charts.
- Candlestick dan volume untuk timeframe `1h`, `4h`, `1d`.
- Update incremental dari pesan `market.candle`; data identik tidak dirender
  ulang.

### 2.3 Portfolio

- Beberapa portfolio terpisah dengan reporting currency.
- Transaksi: `DEPOSIT`, `WITHDRAWAL`, `BUY`, `SELL`, `FEE`, `DIVIDEND`,
  `INTEREST`.
- Penulisan transaksi dan cash ledger bersifat atomik.
- Idempotency per portfolio melalui `Idempotency-Key`.
- Holdings dibangun ulang dari riwayat transaksi.
- Valuation dengan status `COMPLETE`/`PARTIAL`/`STALE`/`UNAVAILABLE`.
- Snapshot manual; nilai yang tidak tersedia disimpan `NULL`.

### 2.4 Performance

- TWR, simple return, CAGR, dan P&L dari transaksi + snapshot.
- `UNAVAILABLE` beserta alasan bila data belum cukup.

### 2.5 Allocation

- Distribusi aktual per asset class, market, currency, dan per aset.
- Cash sebagai komponen tersendiri.
- Konsentrasi top-3/top-5/top-10 dan holding terbesar.
- `weight_base = priced_components_incl_cash`.
- Sektor `UNAVAILABLE` karena metadata sektor belum disimpan.

### 2.6 Risk

- Volatility, annualized volatility, max drawdown, Sharpe, Sortino, VaR/CVaR.
- Method `current_weights_buy_and_hold_approximation`.
- Risk-free rate 0; annualization 365 untuk semua-crypto, selain itu 252.
- `UNAVAILABLE` bila return harian kurang dari 30.

### 2.7 Market Scanner

- Scan teknikal deterministik atas universe crypto yang tersimpan.
- Hasil scan tersimpan beserta rank dan score.
- Qualification per engine dapat diperiksa per hasil.
- Kategori tambahan (momentum, volume, fundamental, dan lain-lain) baru berupa
  cakupan yang direncanakan, bukan filter aktif.

### 2.8 AI Research

- Orkestrasi dengan gate readiness engine deterministik.
- Dedup job, fingerprint konteks, dan cooldown.
- Provider LLM kompatibel OpenAI melalui konfigurasi `PIMS_LLM_*`.
- Tanpa konfigurasi LLM, job berakhir `FAILED` dengan
  `PROVIDER_NOT_CONFIGURED`.
- Output AI adalah interpretasi, bukan fakta terverifikasi.

### 2.9 Dashboard dan WebSocket

- Dashboard menampilkan ringkasan portfolio dan instrumen hasil scanner.
- Kanal WebSocket `research.status` tetap tersedia.
- Kanal WebSocket `market` menambahkan `market.quote`, `market.candle`, dan
  `market.status`.

---

## 3. Yang belum ada pada V1

- Eksekusi order atau integrasi broker.
- Stream real-time dari exchange.
- Target weight, drift band, dan rebalancing.
- Beta, benchmark, dan HHI.
- Penjadwalan snapshot otomatis.
- Multi-currency dan konversi FX.
- Penjadwalan otomatis analytics (persistensi masih dipicu manual).
- Provider US stocks dan IDX (modul masih kosong).
- Jalur LLM nyata yang tervalidasi end-to-end di environment ini.
- Docker-based setup yang terverifikasi di mesin ini.

---

## 4. Catatan schema dan migration

- Migration dijalankan otomatis saat backend start (`run_migrations()` di
  `backend/app/main.py`).
- Migration terakhir: `dcadf6176257` (`add_performance_and_allocation_results`,
  Stage Q/R) — membuat `performance_results` dan `allocation_results`.
- Migration sebelumnya: `a41c2e9f7b30` (`portfolio domain tables`, Stage A),
  lalu `3374e73084c0` (`initial vertical slice schema`).
- Persistensi analytics level instrumen (runner): `analytics_runs`,
  `technical_results`, `market_regime_results`, `risk_results`.
- Persistensi analytics level portfolio (Stage Q/R, manual): `analytics_runs`
  (induk) + `performance_results` / `risk_results` / `allocation_results`.
  Kolom `risk_results` tidak diubah; metadata metodologi disimpan di
  `result_metadata` JSONB (§7.3).
- Endpoint additive: `POST /portfolios/{id}/analytics/runs`,
  `GET /portfolios/{id}/analytics/runs`, `GET /portfolios/{id}/analytics/runs/{run_id}`.
- `backend/uv.lock` masih untracked; keputusan commit/gitignore belum diambil.

---

## 5. Status

**Release Candidate — belum dirilis.** Gunakan
[`docs/user/PANDUAN_PENGGUNA.md`](user/PANDUAN_PENGGUNA.md) untuk cara
menjalankan dan memakai, dan
[`docs/RELEASE_KNOWN_ISSUES.md`](RELEASE_KNOWN_ISSUES.md) untuk isu yang masih
terbuka.
