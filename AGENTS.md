# AGENTS.md
# Personal Investment Management System (PIMS)

**Document Type:** Project-Level Agent Instructions  
**Version:** 1.0  
**Status:** Initial Baseline  
**Primary Coding Agent:** OpenCode  
**Architecture:** Monorepo + Modular Monolith

---

# 1. PROJECT OVERVIEW

Personal Investment Management System (PIMS) adalah aplikasi pengelolaan investasi dan analisis pasar keuangan yang dirancang untuk mengelola beberapa portofolio secara terpisah.

Sistem ini menggabungkan:

- Market Data Aggregation
- Real-Time Market Monitoring
- Interactive Financial Charts
- Market Scanner
- Technical Analysis
- Fundamental Analysis
- Portfolio Management
- Risk Management
- Asset Allocation
- Correlation Analysis
- AI-Assisted Financial Research

PIMS dirancang sebagai aplikasi modular yang dapat dikembangkan secara bertahap tanpa harus mengubah keseluruhan arsitektur ketika fitur baru ditambahkan.

## 1.1 Primary Objectives

1. Mengumpulkan data pasar dari beberapa penyedia data.
2. Menampilkan harga dan grafik pasar secara real-time apabila feed mendukung.
3. Mengelola beberapa portofolio secara terpisah.
4. Melakukan analisis teknikal, fundamental, dan risiko.
5. Melakukan pemindaian pasar melalui Market Scanner.
6. Menyediakan AI Research Assistant untuk membantu interpretasi informasi.
7. Menyediakan dashboard finansial terintegrasi.

## 1.2 Supported Markets

Target integrasi awal:

| Market | Initial Provider |
|---|---|
| Cryptocurrency | Bybit |
| US Stocks | Finnhub / Alpaca |
| Indonesian Stocks | Yahoo Finance, dengan keterbatasan yang harus diverifikasi |

Semua provider harus menggunakan sistem adapter agar pergantian atau penambahan penyedia data tidak mengharuskan perubahan pada keseluruhan aplikasi.

---

# 2. AGENT RESPONSIBILITIES

OpenCode bertindak sebagai Software Engineering Agent yang bertanggung jawab atas seluruh implementasi teknis.

## 2.1 OpenCode Responsibilities

OpenCode diperbolehkan dan diharapkan untuk:

- Membuat dan mengedit source code.
- Membuat struktur direktori implementasi.
- Mengembangkan frontend dan backend.
- Membuat database models dan migrations.
- Mengimplementasikan API dan WebSocket.
- Mengintegrasikan external data providers.
- Mengimplementasikan seluruh analytics engines.
- Membuat automated tests.
- Menjalankan aplikasi dan pengujian.
- Memperbaiki bug.
- Melakukan refactoring.
- Memperbarui dokumentasi implementasi apabila diperlukan.

## 2.2 Architecture Authority

Arsitektur dan spesifikasi teknis utama dikelola oleh Project Architect melalui dokumen dalam:

- `docs/`
- `specifications/`

OpenCode harus mengikuti dokumen tersebut sebagai acuan implementasi.

OpenCode tidak boleh secara sepihak:

1. Mengganti arsitektur utama.
2. Mengubah teknologi inti.
3. Mengubah kontrak API yang telah ditetapkan.
4. Mengubah database schema yang telah disetujui.
5. Mengubah struktur komunikasi antar-engine.
6. Menghapus fitur atau modul yang telah direncanakan.

Jika terdapat kebutuhan perubahan, OpenCode harus menjelaskan:

- Masalah yang ditemukan.
- Alasan perubahan diperlukan.
- Dampak terhadap sistem.
- Alternatif solusi.
- Rekomendasi teknis.

Tunggu persetujuan sebelum melakukan perubahan arsitektur yang berdampak besar.

## 2.3 Decision Authority

Prioritas keputusan:

1. Instruksi terbaru yang diberikan Project Owner.
2. Spesifikasi teknis yang telah disetujui.
3. Dokumentasi arsitektur.
4. Instruksi dalam AGENTS.md.
5. Asumsi teknis OpenCode.

Jangan menganggap asumsi sebagai keputusan yang telah disetujui.

---

# 3. PROJECT ARCHITECTURE

PIMS menggunakan pendekatan:

**Monorepo + Modular Monolith**

Frontend dan backend dipisahkan secara direktori, tetapi backend tetap menggunakan satu aplikasi utama dengan modul internal yang terorganisasi.

## 3.1 Main Technologies

| Component | Technology |
|---|---|
| Frontend | Next.js |
| UI Framework | React |
| Language | TypeScript |
| Styling | Tailwind CSS |
| Backend | Python |
| Backend Framework | FastAPI |
| Database | PostgreSQL |
| Chart Library | TradingView Lightweight Charts |
| Cache | Redis (optional initially) |
| Containerization | Docker |
| Market Communication | REST API + WebSocket |

Versi dependency harus menggunakan versi stabil yang kompatibel dan dicatat dalam package manager masing-masing.

Jangan menggunakan dependency baru tanpa alasan teknis yang jelas.

## 3.2 Architectural Principles

1. Modular architecture.
2. Separation of concerns.
3. Single responsibility.
4. Loose coupling.
5. High cohesion.
6. Reusable components.
7. Explicit interfaces.
8. Centralized configuration.
9. Testable business logic.
10. Data integrity.

Hindari membuat microservices pada tahap awal kecuali terdapat alasan dan persetujuan khusus.

---

# 4. REPOSITORY STRUCTURE

Struktur repository utama:

```text
personal-investment-management-system/
│
├── AGENTS.md
├── README.md
├── LICENSE
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── docs/
│
├── specifications/
│
├── frontend/
│
├── backend/
│
├── infrastructure/
│
├── tests/
│
└── scripts/
```

## 4.1 Directory Ownership

| Directory | Responsibility |
|---|---|
| `docs/` | Architecture and project documentation |
| `specifications/` | Technical implementation specifications |
| `frontend/` | Frontend source code |
| `backend/` | Backend source code |
| `infrastructure/` | Deployment and infrastructure |
| `tests/` | Cross-application tests |
| `scripts/` | Development and maintenance scripts |

OpenCode bertanggung jawab atas implementasi seluruh direktori kecuali dokumen perancangan yang dikelola Project Architect.

Jangan membuat direktori atau file kosong dalam jumlah besar hanya untuk memenuhi struktur yang direncanakan. Buat sesuai kebutuhan implementasi.

---

# 5. DOCUMENTATION REQUIREMENTS

Sebelum mengimplementasikan suatu modul, OpenCode harus membaca spesifikasi terkait.

Contoh:

| Task | Required Documents |
|---|---|
| Frontend Dashboard | `specifications/frontend/` |
| Lightweight Charts | `specifications/frontend/chart-engine-spec.md` |
| Market Data | `specifications/data/` |
| Bybit Integration | `specifications/data/provider-integration-spec.md` |
| Market Scanner | `specifications/engines/market-scanner-spec.md` |
| Portfolio Engine | `specifications/engines/portfolio-engine-spec.md` |
| Risk Engine | `specifications/engines/risk-engine-spec.md` |
| Database | `specifications/database/` |
| API | `specifications/backend/api-spec.md` |

Jika dokumen yang diperlukan belum tersedia:

1. Jangan mengarang spesifikasi kompleks.
2. Identifikasi informasi yang belum tersedia.
3. Laporkan kebutuhan spesifikasi.
4. Tunggu arahan atau persetujuan sebelum membuat asumsi yang berdampak pada arsitektur.

Untuk detail implementasi kecil yang tidak memengaruhi kontrak sistem, OpenCode boleh memilih solusi teknis yang wajar dan mendokumentasikan keputusannya.

---

# 6. FRONTEND DEVELOPMENT RULES

Frontend menggunakan Next.js, React, TypeScript, dan Tailwind CSS.

## 6.1 General Rules

- Gunakan TypeScript secara konsisten.
- Hindari penggunaan `any` tanpa alasan kuat.
- Gunakan reusable components.
- Pisahkan business logic dari UI components.
- Gunakan centralized API services.
- Gunakan centralized WebSocket services.
- Hindari duplikasi kode.
- Gunakan state management secara terstruktur.
- Terapkan loading, empty, error, dan disconnected states.

## 6.2 Chart Engine

Gunakan TradingView Lightweight Charts sebagai library utama untuk visualisasi harga pasar.

Penting:

Lightweight Charts hanya bertanggung jawab untuk visualisasi. Library tersebut bukan penyedia market data.

Alur data harus melalui:

```text
Market Data Provider
        |
        v
Backend Data Pipeline
        |
        v
Normalized Market Data
        |
        v
Backend WebSocket
        |
        v
Frontend Chart Component
        |
        v
Lightweight Charts
```

Ketentuan:

- Historical candles diperoleh melalui backend API.
- Live updates dikirim melalui backend WebSocket.
- Jangan membuat koneksi provider terpisah untuk setiap chart.
- Jangan melakukan perhitungan finansial utama di frontend.
- Pastikan timestamp dan timeframe konsisten.
- Tangani data yang terlambat atau terputus.
- Tampilkan informasi sumber data dan status feed.

Chart harus mendukung pengembangan bertahap untuk candlestick, volume, indikator teknikal, dan fitur visualisasi tambahan.

---

# 7. BACKEND DEVELOPMENT RULES

Backend menggunakan Python dan FastAPI.

## 7.1 General Rules

- Pisahkan API, services, repositories, dan business logic.
- Gunakan dependency injection apabila sesuai.
- Gunakan Pydantic untuk validasi data.
- Gunakan centralized configuration.
- Gunakan structured logging.
- Tangani exception secara konsisten.
- Hindari business logic di dalam route handlers.
- Gunakan asynchronous operations untuk I/O yang sesuai.

## 7.2 Backend Responsibilities

Backend menjadi sumber utama untuk:

- Market data processing.
- Portfolio calculations.
- Technical indicators.
- Risk calculations.
- Asset allocation.
- Correlation calculations.
- Scanner processing.
- AI research orchestration.

Frontend hanya bertanggung jawab atas presentasi dan interaksi pengguna.

---

# 8. MARKET DATA RULES

Market data merupakan komponen fundamental PIMS.

Setiap provider harus menggunakan adapter tersendiri.

Contoh:

```text
data/
└── providers/
    ├── base.py
    ├── crypto/
    │   └── bybit.py
    ├── us_stocks/
    │   ├── finnhub.py
    │   └── alpaca.py
    └── indonesia/
        └── yahoo_finance.py
```

## 8.1 Provider Isolation

Jangan menghubungkan business logic langsung dengan format respons provider.

Gunakan alur:

```text
Provider Adapter
       |
       v
Raw Market Data
       |
       v
Normalization
       |
       v
Validation
       |
       v
Aggregation
       |
       v
Internal Market Data Model
```

## 8.2 Normalized Data

Data internal harus memiliki struktur yang konsisten.

Informasi yang perlu diperhatikan:

- Symbol.
- Asset class.
- Exchange.
- Provider.
- Timestamp.
- Timeframe.
- Open.
- High.
- Low.
- Close.
- Volume.
- Currency.
- Market session.
- Data freshness.
- Feed status.

Field final harus mengikuti spesifikasi data yang disetujui.

## 8.3 Real-Time Data

- Gunakan provider WebSocket apabila tersedia.
- Gunakan REST API untuk historical data apabila sesuai.
- Terapkan reconnection handling.
- Terapkan heartbeat dan connection monitoring jika didukung.
- Terapkan rate limiting.
- Hindari duplicate subscriptions.
- Tangani missing data.
- Validasi urutan timestamp.
- Bedakan real-time, delayed, dan unavailable feeds.

Jangan pernah mengklaim data real-time apabila provider tidak menjaminnya.

OpenCode harus mematuhi ketentuan lisensi, batas penggunaan, dan kebijakan distribusi data setiap provider.

---

# 9. ANALYTICS ENGINE RULES

Setiap analytics engine harus memiliki tanggung jawab yang jelas.

Engine awal yang direncanakan:

1. Technical Analysis Engine.
2. Market Scanner Engine.
3. Portfolio Engine.
4. Risk Engine.
5. Asset Allocation Engine.
6. Correlation Engine.
7. Market Regime Engine.
8. Fundamental Analysis Engine.
9. Sentiment Analysis Engine.
10. Macro Analysis Engine.
11. Factor Analysis Engine.
12. Attribution Engine.
13. Backtesting Engine.
14. Scenario Analysis Engine.

## 9.1 Engine Design Principles

Setiap engine harus:

- Memiliki fungsi dan batas tanggung jawab yang jelas.
- Menggunakan normalized input.
- Memiliki output schema yang jelas.
- Memisahkan calculation dan presentation.
- Memiliki unit tests.
- Menangani invalid input.
- Mendokumentasikan asumsi matematis.
- Menghindari ketergantungan langsung pada provider tertentu.

## 9.2 Financial Calculation Accuracy

Perhitungan finansial harus dapat diuji dan direproduksi.

Ketentuan:

- Jangan mengarang nilai input.
- Dokumentasikan formula yang digunakan.
- Perhatikan currency dan unit.
- Tangani missing values.
- Perhatikan timestamp dan periode perhitungan.
- Hindari floating-point errors pada perhitungan uang yang memerlukan presisi.
- Gunakan Decimal atau pendekatan presisi yang sesuai untuk nilai moneter.
- Verifikasi hasil menggunakan test cases.

AI tidak boleh menggantikan perhitungan matematis deterministik.

---

# 10. MARKET SCANNER RULES

Market Scanner merupakan engine tersendiri, bukan hanya halaman frontend.

Alur dasar:

```text
Market Universe
      |
      v
Market Data
      |
      v
Scanner Processing
      |
      v
Filtering
      |
      v
Ranking
      |
      v
Scanner Results
      |
      v
Frontend Scanner
```

Scanner harus dirancang agar dapat dikembangkan untuk:

- Technical Scanner.
- Momentum Scanner.
- Volume Scanner.
- Volatility Scanner.
- Fundamental Scanner.
- Market Trend Scanner.
- Anomaly Scanner.
- Correlation Scanner.

Jangan membuka satu koneksi provider untuk setiap instrumen.

Gunakan sistem pengelolaan data terpusat dan pemrosesan yang efisien.

---

# 11. DATABASE RULES

Gunakan PostgreSQL sebagai database utama.

Ketentuan:

- Pisahkan database models dan repositories.
- Gunakan migrations.
- Gunakan foreign keys.
- Gunakan indexes berdasarkan kebutuhan query.
- Hindari duplikasi data yang tidak diperlukan.
- Terapkan transaksi database ketika dibutuhkan.
- Jangan mengubah schema produksi secara langsung tanpa migration.
- Jangan menghapus data pengguna tanpa persetujuan.

Database schema final harus mengikuti `specifications/database/schema-spec.md`.

---

# 12. AI RESEARCH RULES

AI Research Engine digunakan untuk membantu interpretasi dan penyusunan informasi.

AI dapat digunakan untuk:

- Merangkum berita.
- Menjelaskan indikator.
- Membandingkan instrumen.
- Menyusun laporan penelitian.
- Menjelaskan risiko dan skenario.
- Menginterpretasikan output analytics engines.

Ketentuan:

1. Pisahkan AI provider dari business logic.
2. Jangan menganggap output AI sebagai fakta terverifikasi.
3. Sertakan sumber data jika tersedia.
4. Bedakan data faktual dan interpretasi AI.
5. Jangan membiarkan AI mengubah transaksi portofolio secara otomatis.
6. Jangan memberikan instruksi eksekusi transaksi tanpa persetujuan pengguna.
7. Jangan menyimpan API keys dalam source code.

---

# 13. SECURITY RULES

Keamanan harus menjadi bagian dari pengembangan sejak awal.

- Simpan secrets dalam environment variables.
- Jangan commit API keys.
- Jangan menyimpan password dalam plain text.
- Validasi seluruh input eksternal.
- Terapkan authentication dan authorization sesuai spesifikasi.
- Lindungi endpoint sensitif.
- Jangan menampilkan secrets pada logs.
- Gunakan dependency yang terpercaya.
- Periksa risiko keamanan dependency.
- Jangan menonaktifkan mekanisme keamanan untuk mengatasi error.

File `.env` tidak boleh dimasukkan ke repository.

Gunakan `.env.example` untuk mendokumentasikan nama variabel yang diperlukan tanpa nilai rahasia.

---

# 14. TESTING REQUIREMENTS

Setiap fitur yang diimplementasikan harus memiliki pengujian sesuai kompleksitasnya.

Jenis pengujian:

1. Unit Testing.
2. Integration Testing.
3. API Testing.
4. WebSocket Testing.
5. End-to-End Testing.
6. Data Validation Testing.

Prioritas pengujian:

- Market data normalization.
- Candle aggregation.
- Technical indicators.
- Portfolio calculations.
- Risk calculations.
- Scanner filtering.
- Database operations.
- API responses.

Jangan menyatakan implementasi selesai apabila pengujian yang diwajibkan gagal.

Jangan mengubah atau menghapus test hanya untuk membuat hasil pengujian terlihat berhasil.

---

# 15. DEVELOPMENT WORKFLOW

OpenCode harus mengikuti alur kerja berikut untuk setiap task.

## Step 1 — Read

Baca:

- AGENTS.md.
- Spesifikasi modul terkait.
- Dokumentasi arsitektur terkait.
- Kode existing yang berkaitan.

## Step 2 — Analyze

Identifikasi:

- Tujuan task.
- File yang terpengaruh.
- Dependencies.
- Potensi konflik.
- Risiko perubahan.

## Step 3 — Plan

Sebelum task yang melibatkan banyak file, berikan rencana implementasi singkat.

## Step 4 — Implement

Implementasikan hanya ruang lingkup task yang telah disetujui.

Jangan melakukan refactoring besar yang tidak berkaitan dengan task.

## Step 5 — Test

Jalankan pengujian yang relevan.

## Step 6 — Review

Periksa:

- Kesesuaian spesifikasi.
- Akurasi logika.
- Keamanan.
- Konsistensi arsitektur.
- Kualitas kode.
- Potensi regression.

## Step 7 — Report

Setiap task harus menghasilkan laporan:

```text
TASK REPORT

Task:
Status:

Files Created:
- ...

Files Modified:
- ...

Implementation Summary:
- ...

Tests Executed:
- ...

Test Results:
- ...

Known Issues:
- ...

Architecture Changes:
- None / Proposed

Next Recommended Task:
- ...
```

Jangan mengklaim test berhasil apabila test tidak benar-benar dijalankan.

---

# 16. GIT AND VERSION CONTROL

Ketentuan:

- Gunakan Git untuk version control.
- Gunakan commit message yang deskriptif.
- Hindari commit yang mencampurkan banyak fitur tidak berkaitan.
- Jangan menghapus perubahan pengguna.
- Jangan melakukan destructive Git commands tanpa persetujuan.
- Jangan melakukan force push tanpa persetujuan.
- Periksa status repository sebelum melakukan perubahan besar.

Gunakan branch terpisah untuk fitur besar apabila sesuai dengan workflow proyek.

---

# 17. IMPLEMENTATION PRIORITIES

Pengembangan dilakukan bertahap.

Urutan awal yang direncanakan:

## Phase 1 — Foundation

- Project setup.
- Frontend foundation.
- Backend foundation.
- Database connection.
- Environment configuration.
- Docker setup.

## Phase 2 — Market Data Infrastructure

- Provider adapter architecture.
- Bybit integration.
- Market data normalization.
- Historical data.
- WebSocket distribution.
- Data validation.

## Phase 3 — Chart Engine

- Lightweight Charts integration.
- Historical candles.
- Real-time updates.
- Timeframe management.
- Volume visualization.

## Phase 4 — Portfolio Management

- Multiple portfolios.
- Transactions.
- Holdings.
- Portfolio valuation.
- Performance calculations.

## Phase 5 — Analytics

- Technical Analysis.
- Risk Analysis.
- Asset Allocation.
- Correlation Analysis.
- Market Regime.

## Phase 6 — Market Scanner

- Market universe.
- Scanner rules.
- Filtering.
- Ranking.
- Scanner results.

## Phase 7 — Advanced Intelligence

- Fundamental Analysis.
- Sentiment Analysis.
- Macro Analysis.
- AI Research Assistant.
- Backtesting.
- Scenario Analysis.

Tahapan tersebut merupakan urutan perencanaan awal. Implementasi aktual harus mengikuti spesifikasi dan prioritas yang disetujui.

---

# 18. IMPORTANT RESTRICTIONS

OpenCode dilarang:

1. Mengimplementasikan fitur besar tanpa membaca spesifikasi.
2. Mengganti teknologi inti berdasarkan preferensi pribadi.
3. Mengubah arsitektur tanpa persetujuan.
4. Membuat data pasar palsu dan menggunakannya seolah-olah data asli.
5. Mengklaim koneksi real-time ketika feed sebenarnya delayed.
6. Menyimpan API credentials di source code.
7. Mengabaikan error dan test failures.
8. Menghapus fitur existing tanpa persetujuan.
9. Membuat duplikasi engine dengan tanggung jawab yang sama.
10. Menambahkan dependency tanpa alasan yang jelas.
11. Mengubah rumus finansial tanpa dokumentasi dan pengujian.
12. Menganggap rekomendasi AI sebagai hasil perhitungan yang terverifikasi.
13. Mengubah, memindahkan, membuat ulang, atau "membersihkan" file `.env` atau file kredensial lokal; perubahan hanya lewat persetujuan owner. (Pembersihan default kredensial di kode seperti `settings.py`/`conftest.py` tetap diperbolehkan).
14. Melakukan `DROP`/`TRUNCATE`/`DELETE` massal, `alembic downgrade`, atau `alembic stamp` pada database dev/test (`pims`, `pims_test`). Dilarang membuat/menghapus database. Eksperimen destruktif hanya di database `pims_scratch_*`.

Untuk development, mock data diperbolehkan hanya apabila diberi label yang jelas dan tidak disamarkan sebagai data pasar aktual.

---

# 19. COMMUNICATION PROTOCOL

Apabila menemukan masalah, OpenCode harus melaporkan masalah secara jelas.

Gunakan format:

```text
ISSUE REPORT

Problem:
Affected Module:

Why It Happens:

Technical Impact:

Possible Solutions:
1.
2.

Recommended Solution:

Does This Require Architecture Approval?
Yes / No
```

Apabila spesifikasi bertentangan, jangan memilih secara diam-diam. Laporkan konflik dan tunggu keputusan.

Apabila perubahan hanya bersifat implementasi internal dan tidak mengubah kontrak sistem, OpenCode dapat mengambil keputusan teknis yang wajar dan mencatatnya.

---

# 20. FINAL DEVELOPMENT PRINCIPLE

Prioritas utama PIMS bukan sekadar menghasilkan dashboard yang terlihat modern.

Prioritas utamanya adalah membangun sistem yang:

- Memiliki data pasar yang dapat dipercaya.
- Memiliki perhitungan finansial yang akurat.
- Memiliki arsitektur modular.
- Memiliki pemisahan tanggung jawab yang jelas.
- Dapat diuji dan dipelihara.
- Dapat dikembangkan tanpa merusak modul existing.
- Dapat diperluas ke berbagai pasar dan fitur analisis.

**Build correctly before building extensively.**

Setiap modul harus dirancang, diimplementasikan, diuji, dan direview sebelum menjadi fondasi bagi modul berikutnya.

---

**END OF AGENTS.md**