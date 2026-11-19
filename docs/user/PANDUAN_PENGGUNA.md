# Panduan Pengguna PIMS

**Status:** Release Candidate (V1) — belum dirilis.
**Tanggal:** 19 November 2026

Dokumen ini menjelaskan cara menjalankan PIMS, alur pemakaian, arti setiap label
kejujuran data, dan batasan nyata versi V1. PIMS adalah alat analisis dan
pencatatan investasi pribadi, **bukan platform broker** dan tidak mengeksekusi
order.

---

## 1. Prasyarat

- Python 3.12 atau lebih baru.
- `uv` untuk mengelola environment backend.
- Node.js dan npm untuk frontend.
- PostgreSQL yang berjalan lokal atau dapat dijangkau.
- Git.

Docker **tidak tersedia di mesin pengembangan ini** (perintah `docker` tidak
dikenali). Jalankan PostgreSQL secara lokal; `docker-compose.yml` belum dapat
diverifikasi di mesin ini.

---

## 2. Environment yang diperlukan

Salin `.env.example` menjadi `.env`, lalu isi nilainya. **Jangan commit `.env`.**
Jangan menulis nilai rahasia ke source code atau dokumen.

| Variabel | Kegunaan |
|---|---|
| `PIMS_ENVIRONMENT` | Nama environment, mis. `development`. |
| `PIMS_LOG_LEVEL` | Level log, mis. `INFO`. |
| `PIMS_DATABASE_URL` | URL PostgreSQL. Format: `postgresql+psycopg://<user>:<password>@<host>:<port>/<database>`. |
| `PIMS_CRYPTO_PROVIDER` | Adapter crypto: `YAHOO` (default) atau `BYBIT`. |
| `PIMS_BYBIT_BASE_URL` | Base URL API Bybit. |
| `PIMS_BYBIT_API_KEY` | API key Bybit (rahasia, opsional). |
| `PIMS_BYBIT_API_SECRET` | API secret Bybit (rahasia, opsional). |
| `PIMS_YAHOO_BASE_URL` | Base URL Yahoo Finance. |
| `PIMS_LLM_BASE_URL` | Base URL endpoint LLM yang kompatibel OpenAI. |
| `PIMS_LLM_API_KEY` | API key LLM (rahasia). |
| `PIMS_LLM_MODEL` | Nama model LLM. |

Variabel frontend (opsional, diatur saat menjalankan frontend):

| Variabel | Default / kegunaan |
|---|---|
| `PIMS_API_URL` | Default `http://localhost:8000`. Dipakai proxy Next.js untuk `/api/v1` dan `/health`. |
| `NEXT_PUBLIC_PIMS_WS_URL` | URL WebSocket eksplisit. Jika kosong, frontend memakai `ws://<host>/api/v1/ws/market` (localhost memakai port 8000). |

Nilai rahasia hanya disimpan di `.env` lokal atau environment variable mesin.

---

## 3. Menjalankan aplikasi

### 3.1 PostgreSQL

1. Pastikan PostgreSQL berjalan.
2. Buat database, misalnya `pims`.
3. Set `PIMS_DATABASE_URL` di `.env` agar menunjuk ke database tersebut.

Migration database dijalankan otomatis saat backend start (fungsi
`run_migrations()` di `backend/app/main.py`). Tidak perlu menjalankan Alembic
manual untuk pemakaian normal.

### 3.2 Backend

Sinkronkan dependency terkunci lebih dulu (sekali setelah clone, dan setiap kali
`uv.lock` berubah). `--frozen` memaksa pakai versi persis di lock, tanpa
memutakhirkan apa pun:

```bash
cd backend
uv sync --frozen
```

Jalankan backend:

```bash
cd backend
uv run uvicorn app.main:app --port 8000
```

Cek kesehatan:

```bash
curl http://localhost:8000/health/ready
```

Respons sehat berisi `{"data": {"status": "ok", "database": "connected", ...}}`.

### 3.3 Frontend

```bash
cd frontend
npm install
npm run dev
```

Buka `http://localhost:3000`.

Untuk mode produksi lokal:

```bash
cd frontend
npm run build
npm run start
```

### 3.4 Menjalankan test backend

```bash
cd backend
uv run python -m pytest -q
```

Jalankan dari direktori `backend/` karena konfigurasi test memuat `alembic.ini`
dari sana.

---

## 4. Jika provider belum dikonfigurasi

- `PIMS_CRYPTO_PROVIDER` default adalah `YAHOO`. Adapter Bybit tersedia, tetapi
  domain API exchange sering diblokir oleh ISP; karena itu Yahoo dipakai sebagai
  default.
- Jika `PIMS_CRYPTO_PROVIDER` berisi nilai yang tidak dikenal, refresh data gagal
  dengan pesan `Unknown PIMS_CRYPTO_PROVIDER: <nilai>`.
- Jika baris provider/instrumen tidak ada di database, refresh data gagal. Tidak
  ada data palsu yang dibuat.
- Aplikasi tetap menampilkan candle terakhir yang tersimpan. Data yang sudah lama
  ditandai `STALE`, bukan dianggap harga terbaru.
- Jika `PIMS_LLM_*` kosong, permintaan research tetap dicatat tetapi job berakhir
  `FAILED` dengan kode `PROVIDER_NOT_CONFIGURED`. Tidak ada laporan AI palsu.

---

## 5. Alur pemakaian

### 5.1 Dashboard

Halaman `/` menampilkan ringkasan portofolio dan daftar instrumen hasil scanner
terakhir. Angka yang tidak tersedia ditampilkan sebagai `—`, bukan nol.

### 5.2 Membuat portfolio

1. Buka `/portfolios`.
2. Buat portfolio baru dengan nama dan base currency (mis. `USD`).
3. Portfolio muncul di daftar; buka detailnya di `/portfolios/<id>`.

### 5.3 Deposit

Di form transaksi pada halaman portfolio, pilih tipe `DEPOSIT`, isi
`gross_amount`, lalu simpan. Saldo cash bertambah dan tercatat di cash ledger.

### 5.4 Beli / Jual

- `BUY`: pilih aset, isi `quantity` dan `price`. Total outflow = `quantity × price + fee`. Tidak ada margin pada V1: saldo cash harus mencukupi.
- `SELL`: pilih aset yang dimiliki, isi `quantity` dan `price`. Tidak ada short selling: kuantitas tidak boleh melebihi holding.
- `fee` opsional dan tidak boleh negatif.

Form UI menyediakan `DEPOSIT`, `WITHDRAWAL`, `BUY`, dan `SELL`. API backend juga
menerima `FEE`, `DIVIDEND`, dan `INTEREST`.

### 5.5 Arti error transaksi

| Kode | HTTP | Arti |
|---|---|---|
| `INSUFFICIENT_CASH` | 422 | Outflow `BUY` (atau cash outflow lain) melebihi saldo cash. Tidak ada margin. |
| `FEE_EXCEEDS_PROCEEDS` | 422 | Pada `SELL`, fee lebih besar atau sama dengan gross sehingga net proceeds tidak positif. |
| `INSUFFICIENT_HOLDINGS` | 422 | Kuantitas `SELL` melebihi holding yang tersedia. Short selling tidak didukung. |
| `IDEMPOTENCY_CONFLICT` | 409 | `Idempotency-Key` yang sama dipakai lagi dengan payload berbeda. |
| `CURRENCY_MISMATCH` | 422 | Currency transaksi harus sama dengan reporting currency portfolio (batasan Stage A). |
| `PORTFOLIO_INACTIVE` | 422 | Portfolio tidak berstatus `ACTIVE`. |
| `NON_POSITIVE_AMOUNT` | 422 | Quantity, price, atau amount tidak positif. |

Catatan idempotency: key yang sama dengan payload **identik** mengembalikan
transaksi lama dengan HTTP 200 dan `idempotent_replay: true`. Transaksi baru
mengembalikan HTTP 201.

### 5.6 Holdings dan valuation

Halaman portfolio menampilkan:

- Ringkasan valuation: cash, invested, total value, realized P&L, unrealized P&L.
- Tabel holdings: quantity, average cost, cost basis, harga pasar, market value,
  unrealized P&L, dan `price_status`.

### 5.7 Snapshot

Tombol snapshot menyimpan kondisi valuation saat itu. Snapshot bersifat
**manual** pada V1; belum ada penjadwalan otomatis. Nilai yang tidak dapat
dihitung disimpan sebagai `NULL`, bukan nol.

### 5.8 Performa

Panel Performa menghitung TWR, simple return, CAGR, dan P&L dari transaksi serta
snapshot yang tersimpan. Jika data belum cukup, hasilnya `UNAVAILABLE` beserta
alasan, bukan angka tebakan.

### 5.9 Alokasi

Panel Alokasi menampilkan distribusi aktual per asset class, market, currency,
dan per aset, termasuk cash. Lihat bagian 6.3 untuk arti `weight_base`.

### 5.10 Risiko

Panel Risiko menghitung volatility, annualized volatility, max drawdown, Sharpe,
Sortino, dan VaR/CVaR dari candle harian tersimpan. Window dapat dipilih
(30–3650 hari; default 90). Jika return harian kurang dari 30, hasilnya
`UNAVAILABLE` beserta alasan.

### 5.11 Scanner

Buka `/scanner`, pilih timeframe, lalu jalankan scan. Halaman menampilkan status
eksekusi, waktu selesai, universe, jumlah instrumen eligible, dan jumlah hasil.
Baris hasil dapat diperluas untuk melihat qualification per engine.

Kategori di bagian atas halaman adalah **cakupan yang direncanakan**, bukan filter
aktif. Backend V1 menjalankan satu scan teknikal deterministik.

### 5.12 Halaman instrument dan chart

Buka `/instrument/<SYMBOL>` (mis. `/instrument/BTCUSDT`). Halaman menampilkan:

- Harga terakhir dan perubahan harian dari data tersimpan.
- Chart candlestick 1h/4h/1d dengan volume.
- Tombol `Refresh Data` untuk meminta backend mengambil candle terbaru dari
  provider.
- Badge status feed dan waktu data terakhir.

Chart diperbarui saat pesan WebSocket baru masuk. Data yang identik tidak
dirender ulang dan tidak ada titik palsu yang ditambahkan.

### 5.13 Research

Panel AI Research Assistant memerlukan seluruh engine deterministik yang wajib
dalam status `READY`. Jika gate belum lolos, job berstatus `BLOCKED` dan tidak
memanggil LLM. Jika `PIMS_LLM_*` belum diisi, job berakhir `FAILED` dengan
`PROVIDER_NOT_CONFIGURED`.

Output AI adalah **interpretasi**, bukan fakta terverifikasi. Angka finansial
utama tetap dihitung oleh engine deterministik.

---

## 6. Arti label kejujuran

### 6.1 Status valuation dan analytics

| Label | Arti |
|---|---|
| `COMPLETE` | Semua posisi yang dimiliki punya harga fresh dari candle tersimpan; total final. |
| `PARTIAL` | Sedikitnya satu posisi tidak punya harga tersimpan; nilai yang tidak tersedia disimpan `NULL`. |
| `STALE` | Harga tersimpan lebih lama dari kebijakan freshness; nilai ditahan, tidak diestimasi. |
| `UNAVAILABLE` | Tidak ada transaksi/holding, atau data tidak cukup; hanya cash (jika ada) yang bermakna. |

Label yang sama dipakai di modul lain dengan arti dasar "tersedia penuh /
sebagian / kedaluwarsa / tidak tersedia". Alasan spesifik selalu disertakan di
field `reason` atau `status_reason`.

### 6.2 `null` berarti "tidak tersedia", bukan nol

- `null` = nilai tidak dapat dihitung atau tidak tersedia.
- `0` hanya dipakai bila nilainya memang benar-benar nol (mis. belum ada posisi,
  sehingga invested value benar-benar `0`).
- Nilai yang tidak tersedia tidak boleh ditampilkan sebagai `0`.

### 6.3 Weight base alokasi

`weight_base` = `priced_components_incl_cash`.

Bobot dihitung sebagai `nilai komponen / (nilai posisi yang berharga + cash) ×
100`. Posisi tanpa harga dikecualikan dari bobot dan **tidak** diubah menjadi
nol; total tidak dinormalisasi ulang untuk menyembunyikan posisi yang tidak
berharga. Cakupan data dilaporkan terpisah.

### 6.4 "Buy & hold approximation" pada Risiko

`method` = `current_weights_buy_and_hold_approximation`.

Artinya: return portofolio harian didekati dari **bobot holding saat ini**
dikalikan return harian masing-masing aset, memakai candle harian tersimpan.
Ini adalah proxy buy-and-hold atas komposisi hari ini, **bukan** return
historis yang benar-benar terealisasi. Cash dikecualikan; bobot dinormalisasi
atas holding yang berharga. Risk-free rate = 0. Annualization memakai 365 untuk
portofolio semua-crypto, selain itu 252.

### 6.5 Badge feed

Badge feed berasal dari pesan backend, bukan tebakan frontend.

| Label | Arti |
|---|---|
| `LIVE` | Data stream real-time. **Tidak dipakai pada V1** karena belum ada stream provider. |
| `DELAYED` | Data tersimpan masih dalam batas freshness, tetapi bukan stream real-time. |
| `STALE` | Data tersimpan lebih lama dari kebijakan freshness. |
| `UNAVAILABLE` | Tidak ada data untuk simbol/timeframe tersebut. |
| `CONNECTING` | Koneksi WebSocket sedang dibuka. |
| `CONNECTED` | Koneksi terbuka, belum tentu siap memproses subscription. |
| `READY` | Koneksi siap memproses subscription. |
| `RECONNECTING` | Client mencoba menyambung ulang dengan backoff. |
| `DISCONNECTED` | Koneksi tertutup. Tombol reconnect manual muncul. |
| `ERROR` | Koneksi mengalami error. Tombol reconnect manual muncul. |

Pada V1, market feed menyatakan `is_realtime: false` dan `source: "rest_poll"`.
Backend membaca candle yang **sudah ada di database** setiap 3 detik
(`poll_interval_seconds: 3`), bukan membuka stream ke provider. Karena itu data
fresh tetap dilabeli `DELAYED`, tidak pernah `LIVE`.

---

## 7. Batasan nyata V1

1. **Bukan platform broker.** PIMS tidak mengeksekusi order dan tidak terhubung
   ke akun broker.
2. **Crypto default via Yahoo.** Adapter Bybit ada, tetapi domain exchange sering
   diblokir ISP; jalur Bybit live belum dapat diuji di mesin ini.
3. **WebSocket = polling REST.** Backend membaca database setiap 3 detik, bukan
   stream real-time. `is_realtime: false`, `source: "rest_poll"`.
4. **AI research = interpretasi.** Bukan fakta terverifikasi; memerlukan
   konfigurasi LLM.
5. **Alokasi belum punya target/rebalance.** Hanya distribusi aktual dan
   konsentrasi top-N.
6. **Risiko belum punya beta/benchmark.** Tidak ada perbandingan terhadap pasar.
7. **Snapshot masih manual.** Belum ada penjadwalan otomatis.
8. **Multi-currency belum didukung.** Transaksi harus memakai reporting currency
   portfolio.
9. **Docker belum tersedia di mesin ini.** Jalankan PostgreSQL lokal.

---

## 8. Baseline verifikasi

Angka berikut diverifikasi pada 19 November 2026:

- Backend: `150 passed, 78 warnings` dari `uv run python -m pytest -q`.
- Frontend: `npm run build` berhasil.
- Database: 20 tabel di schema `public` (19 tabel domain + `alembic_version`).
- Migration terakhir: `a41c2e9f7b30` (portfolio domain, Stage A).

Status keseluruhan tetap **release candidate, belum dirilis**. Lihat
`docs/RELEASE_NOTES_V1.md` dan `docs/RELEASE_KNOWN_ISSUES.md`.
