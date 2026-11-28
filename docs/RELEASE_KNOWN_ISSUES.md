# PIMS V1 — Known Issues

**Status:** Release Candidate — **belum dirilis**.
**Tanggal:** 19 November 2026

Dokumen ini mencatat daftar isu nyata, level urgensi, dan dampaknya terhadap
sistem pada tahap Release Candidate V1.

---

## 1. Daftar isu dan keterbatasan

### 1.1 Jalur Bybit live belum dapat diuji langsung
- **Level:** High
- **Modul:** Market Data Provider
- **Deskripsi:** Domain API exchange (Bybit) sering terblokir oleh ISP di lingkungan pengujian ini.
- **Dampak:** Adapter Bybit tersedia secara kode tetapi tidak dapat diuji langsung terhadap endpoint live exchange. Provider crypto default diatur ke `YAHOO`.
- **Rencana penanganan:** Gunakan proxy/VPN atau provider data terverifikasi saat pengujian lingkungan produksi.

### 1.2 Jalur LLM nyata belum dijalankan
- **Level:** Medium
- **Modul:** AI Research
- **Deskripsi:** Tanpa variabel environment `PIMS_LLM_*`, orchestrator AI tidak memanggil LLM nyata.
- **Dampak:** Job research berakhir `FAILED` dengan kode `PROVIDER_NOT_CONFIGURED` (kejujuran status dijaga, tidak ada laporan palsu). Pengujian backend memakai mock HTTP / error handler.
- **Rencana penanganan:** Konfigurasi endpoint dan API key LLM kompatibel OpenAI jika fitur research ingin diaktifkan.

### 1.3 Metrik Risiko & Konsentrasi belum memiliki beta, benchmark, dan HHI
- **Level:** Medium
- **Modul:** Analytics Engines (Risk & Allocation)
- **Deskripsi:** Engine alokasi hanya menghitung akumulasi bobot Top-N (spec tidak mendefinisikan HHI). Engine risiko belum menghitung beta terhadap indeks pasar atau perbandingan benchmark.
- **Dampak:** Analisis konsentrasi terbatas pada Top-N; analisis risiko berfokus pada statistik portofolio internal tanpa perbandingan pasar relatif.
- **Rencana penanganan:** Tambahkan data series benchmark dan spesifikasi HHI/beta pada fase analitis berikutnya.

### 1.4 Persistensi analitis level portfolio dipicu manual (tidak terjadwal)
- **Level:** Medium
- **Modul:** Analytics Persistence
- **Deskripsi:** Hasil performance/risk/allocation dapat disimpan secara eksplisit
  lewat `POST /portfolios/{id}/analytics/runs` (`analytics_runs` sebagai induk +
  `performance_results` / `risk_results` / `allocation_results` dengan FK).
  **Tidak ada penjadwalan otomatis** (scheduler ditunda).
- **Dampak:** Histori analisis tidak tersimpan otomatis; pengguna harus memanggil
  endpoint setelah transaksi baru atau window risiko berubah. `risk_results`
  tetap menyimpan metodologi di `result_metadata` JSONB (kolomnya tidak diubah).
- **Rencana penanganan:** Tambahkan worker/cron terpisah untuk otomatisasi
  analisis berkala.

### 1.5 Penjadwalan snapshot portfolio masih manual
- **Level:** Medium
- **Modul:** Portfolio Management
- **Deskripsi:** Belum ada background scheduler untuk mengambil snapshot portfolio berkala. `scanner_schedule_enabled` dan `research_schedule_enabled` default `False`.
- **Dampak:** Snapshot portfolio hanya dibuat saat pengguna memanggil `POST /portfolios/{id}/snapshots`.
- **Rencana penanganan:** Tambahkan worker/cron terpisah untuk otomatisasi snapshot harian.

### 1.6 Docker tidak tersedia di lingkungan pengujian ini
- **Level:** Low
- **Modul:** Infrastructure / Dev Environment
- **Deskripsi:** Perintah `docker` tidak terinstall/dikenali di mesin tempat pengujian ini berjalan.
- **Dampak:** File `docker-compose.yml` belum dapat dijalankan di mesin ini. Pengujian dan eksekusi lokal memakai proses Python (`uvicorn`) dan Node.js (`next`) langsung terhadap PostgreSQL lokal.
- **Rencana penanganan:** Siapkan lingkungan berfasilitas Docker untuk verifikasi kontainerisasi.

### 1.7 File lock backend `backend/uv.lock` belum diputuskan
- **Level:** Low
- **Modul:** Version Control / Dependency Management
- **Deskripsi:** File `backend/uv.lock` terbentuk tetapi belum masuk ke `.gitignore` maupun dicommit.
- **Dampak:** Status git repository menampilkan `backend/uv.lock` sebagai untracked file.
- **Rencana penanganan:** Putuskan apakah lockfile `uv` dikomit untuk mengunci dependency backend atau dimasukkan ke `.gitignore`.

### 1.6 Ingestion `market_quotes` dan `fx_rates` belum ada (endpoint read-only sudah siap)
- **Level:** Medium
- **Modul:** Market Data (Stage V)
- **Deskripsi:** Tabel `market_quotes` (§6.1), `fx_rates` (§6.4), dan `scanner_configurations` (§8.1) beserta endpoint baca/CRUD-nya sudah ada, tetapi belum ada jalur yang **menulis** quote/FX (belum ada job ingestion).
- **Dampak:** `GET /market-data/quotes` dan `.../instruments/{id}/quote` mengembalikan `data: null` dengan `feed_status: UNAVAILABLE` sampai ingestion dibuat — bukan error, bukan angka karangan. Konversi FX lintas mata uang belum dipakai karena spec §6.4 melarang mengasumsikan inverse rate.
- **Rencana penanganan:** Implementasikan job ingestion quote (provider Yahoo/Bybit adapter yang sudah ada) + penulisan `fx_rates`, lalu tambahkan test end-to-end yang memverifikasi `freshness_status`.

### 1.8 Correlation Engine belum diimplementasikan
- **Level:** Medium
- **Modul:** Analytics (Correlation)
- **Deskripsi:** Endpoint `GET /api/v1/analytics/correlation` mengembalikan `200` dengan `data: null` dan status `NOT_IMPLEMENTED`.
- **Dampak:** Analisis korelasi antar portofolio holdings tidak tersedia saat ini.
- **Rencana penanganan:** Spesifikasi rumus korelasi akan ditentukan dan engine akan diimplementasikan pada fase analitis berikutnya.

---

## 2. Ringkasan dampak terhadap pemakaian

Sistem berada dalam kondisi **Release Candidate yang jujur dan konsisten**. Seluruh batasan di atas tidak menyebabkan silent data corruption atau kalkulasi palsu. Saat data/fitur belum tersedia, API dan UI secara eksplisit mengembalikan status `UNAVAILABLE`, `PARTIAL`, `STALE`, atau `PROVIDER_NOT_CONFIGURED`.

---

## 3. Status terverifikasi per 2026-11-22 (`0ff3366`)

Angka di bawah diambil dari perintah nyata, bukan perkiraan.

| Item | Nilai | Cara verifikasi |
|---|---|---|
| Test lokal | **262 passed, 0 failed** | `pytest tests/ -q` (PostgreSQL 17 lokal, suite memaksa DB `*_test`) |
| CI GitHub Actions | **hijau** | job `backend` + `frontend` pada commit `0ff3366` |
| Gate tunggal | `sh scripts/verify_all.sh` → Tests/Linting/Build/Dependencies PASSED | dijalankan lokal |
| Endpoint | 59 operasi (spec 54) | `backend/scripts/audit_api_contract.py` |
| Gap spec tersisa | **9** | 7 `watchlists` + `PATCH`/`DELETE /transactions/{id}` |
| Ingestion | candle+quote+FX, multi-market, jam-an | `python -m app.data.ingestion.candles` → `requested: 5, written: 500` |

### 3.1 Keterbatasan yang masih berlaku

1. **`watchlists` belum ada** (api-spec §17, 7 endpoint). `schema-spec` tidak mendefinisikan tabelnya → butuh keputusan owner sebelum dibuat.
2. **`PATCH`/`DELETE /transactions/{id}` belum ada** — mengubah/menghapus transaksi menyentuh integritas ledger; keputusan owner.
3. **`GET /analytics/correlation`** mengembalikan status *not implemented* karena belum ada rumus korelasi di spec. Tidak diisi angka karangan.
4. **Jalur LLM AI Research** baru diuji dengan provider mock; kunci ada di `.env` tetapi panggilan nyata belum diverifikasi.
5. **Bybit** hanya teruji lewat HTTP mock (endpoint provider diblokir dari jaringan mesin ini); sumber data produksi saat ini Yahoo Finance.
6. **Penjadwalan analytics/snapshot** masih manual (keputusan owner: manual-only). Yang otomatis hanya ingestion pasar per jam.
7. **Kualitas data US/IDX** bergantung pada mapping `provider_instruments` dan feed Yahoo yang delayed (`is_realtime: false`).

### 3.2 Tindakan keamanan yang menunggu owner

- Password PostgreSQL **pernah masuk riwayat git** (`settings.py` sejak commit awal, `conftest.py`, `docker-compose.yml`, `alembic.ini`). Semua sudah dibersihkan dari file yang dilacak **dan** dijaga test `test_no_hardcoded_credentials.py`, tetapi **nilainya masih ada di riwayat repo**. Rotasi password + (opsional) penulisan ulang riwayat adalah keputusan owner.

### 3.3 Insiden data 2026-11-22

Database dev `pims` kehilangan seluruh tabel saat pengerjaan reproduksi CI. Penyebab langsung: `conftest.py` memuat `.env` root sehingga suite menunjuk DB dev lalu `TRUNCATE`. Perbaikan: conftest memaksa DB `*_test` dan menolak jalan bila bukan DB test; ditambah backup harian `D:\pims-backups` (cron `pims-db-backup-daily`, retensi 7). Data lama tidak dapat dipulihkan (tidak ada backup saat itu).

## 2026-11-28 — Status
- H-3: 9 engine tanpa test anti-kebocoran (Q2 hanya 3/13) — pending
- M-1: Tidak ada test regresi compose (5432/0.0.0.0 bisa kembali) — pending
- P5: Dashboard watchlist panel — Raka implementasi
- pims_test flaky lokal (test isolation) — CI lulus
