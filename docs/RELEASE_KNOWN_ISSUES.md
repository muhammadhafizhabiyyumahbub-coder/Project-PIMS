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
