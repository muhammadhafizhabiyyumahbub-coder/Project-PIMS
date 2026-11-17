# Project Overview
## Personal Investment Management System (PIMS)

**Document Version:** 1.0  
**Project Status:** Planning  
**Document Type:** Project Specification  
**Last Updated:** November 2026

---

# 1. Project Introduction

Personal Investment Management System (PIMS) merupakan aplikasi pengelolaan dan analisis investasi yang dirancang untuk membantu pengguna mengelola beberapa portofolio, memantau kondisi pasar keuangan, menganalisis aset, serta mengevaluasi risiko dan performa investasi melalui satu platform terintegrasi.

PIMS menggabungkan portfolio management, market data visualization, quantitative analytics, market screening, dan AI-assisted research dalam satu sistem.

Aplikasi ini dirancang dengan pendekatan modern financial dashboard yang mengutamakan kejelasan informasi, konsistensi data, akurasi perhitungan, dan kemudahan dalam memahami kondisi investasi.

PIMS tidak hanya berfungsi sebagai pencatat aset, tetapi juga sebagai sistem pendukung analisis dan pengambilan keputusan berbasis data.

# 2. Project Vision

Membangun sistem pengelolaan investasi personal yang memiliki kemampuan analisis menyerupai workflow profesional dalam pengelolaan portofolio.

PIMS diharapkan menjadi satu pusat pengelolaan informasi investasi yang memungkinkan pengguna untuk:

- Mengelola beberapa portofolio secara terpisah.
- Memantau berbagai pasar keuangan.
- Menganalisis performa investasi.
- Mengukur risiko portofolio.
- Memahami distribusi aset.
- Menemukan peluang melalui market scanner.
- Menggunakan AI untuk membantu memahami hasil analisis.
- Mengembangkan strategi pengelolaan portofolio berdasarkan data.

# 3. Problem Statement

Pengelolaan investasi sering kali membutuhkan beberapa aplikasi dan sumber informasi yang berbeda.

Pengguna dapat menggunakan satu platform untuk melihat harga pasar, aplikasi lain untuk mencatat transaksi, spreadsheet untuk menghitung performa, dan sumber lain untuk melakukan riset.

Kondisi tersebut menimbulkan beberapa permasalahan:

### 3.1 Fragmented Investment Data

Informasi investasi tersebar di berbagai platform sehingga sulit memperoleh gambaran portofolio secara menyeluruh.

### 3.2 Limited Portfolio Analytics

Pencatatan transaksi tidak selalu menyediakan analisis mendalam mengenai performa, risiko, alokasi, dan diversifikasi.

### 3.3 Limited Market Monitoring

Memantau banyak instrumen secara manual membutuhkan waktu dan tidak efisien.

### 3.4 Difficult Risk Evaluation

Pengguna membutuhkan metrik kuantitatif untuk memahami volatilitas, drawdown, konsentrasi, dan hubungan antar-aset.

### 3.5 Fragmented Research Workflow

Informasi pasar, indikator teknikal, data fundamental, dan berita sering kali perlu dianalisis secara terpisah.

PIMS dirancang untuk mengintegrasikan proses tersebut dalam satu sistem.

# 4. Project Objectives

Tujuan pengembangan PIMS adalah:

1. Membangun sistem pengelolaan beberapa portofolio secara terstruktur.
2. Menyediakan visualisasi market data melalui chart interaktif.
3. Mengintegrasikan data pasar dari beberapa sumber.
4. Mengembangkan quantitative analytics untuk evaluasi portofolio.
5. Menyediakan Market Scanner untuk melakukan screening instrumen.
6. Mengembangkan AI Research Assistant untuk membantu interpretasi informasi.
7. Menyediakan informasi risiko dan performa secara terukur.
8. Membangun arsitektur yang modular dan dapat dikembangkan secara bertahap.

# 5. Target Users

Target pengguna utama adalah individu yang ingin mengelola investasi secara lebih sistematis dan menggunakan analisis kuantitatif untuk memahami kondisi portofolionya.

Karakteristik pengguna:

- Mengelola satu atau beberapa portofolio.
- Memantau lebih dari satu jenis aset.
- Membutuhkan informasi performa dan risiko.
- Menggunakan market data untuk melakukan analisis.
- Membutuhkan sistem pencatatan transaksi.
- Menginginkan workflow riset yang terintegrasi.

PIMS pada tahap awal difokuskan untuk penggunaan personal, bukan sebagai platform trading publik atau layanan pengelolaan dana pihak ketiga.

# 6. Supported Markets

PIMS dirancang untuk mendukung beberapa kategori pasar.

| Market | Initial Provider | Data Integration |
|---|---|---|
| Cryptocurrency | Bybit | REST API / WebSocket |
| US Stocks | Finnhub / Alpaca | REST / Streaming |
| Indonesian Stocks | Yahoo Finance | Provider-dependent |

Provider tersebut merupakan rencana integrasi awal, bukan jaminan bahwa seluruh instrumen, timeframe, atau jenis data tersedia secara real-time.

Ketersediaan data, batas API, biaya, lisensi, dan hak penggunaan harus diverifikasi sebelum implementasi.

# 7. Core Product Modules

PIMS memiliki beberapa modul utama.

## 7.1 Portfolio Management

Modul untuk mengelola beberapa portofolio secara terpisah.

Fitur utama:

- Portfolio creation.
- Portfolio overview.
- Asset holdings.
- Transaction management.
- Cash balance.
- Portfolio valuation.
- Portfolio history.

Transaksi menjadi sumber utama pembentukan data kepemilikan.

## 7.2 Market Data and Visualization

Modul untuk memantau kondisi pasar dan menampilkan informasi instrumen.

Fitur utama:

- Instrument search.
- Market overview.
- Historical market data.
- Real-time market updates jika feed mendukung.
- Interactive charts.
- OHLCV visualization.
- Market data freshness status.

Chart menggunakan TradingView Lightweight Charts sebagai library visualisasi.

## 7.3 Quantitative Analytics

Modul untuk melakukan analisis matematis terhadap portofolio dan aset.

Analisis utama:

- Portfolio Performance.
- Risk Analysis.
- Asset Allocation.
- Technical Analysis.
- Correlation Analysis.
- Market Regime Analysis.

Perhitungan dilakukan secara deterministik di backend agar hasilnya konsisten dan dapat diuji.

## 7.4 Market Scanner

Modul untuk melakukan screening terhadap instrumen dalam market universe.

Kategori screening:

- Technical.
- Momentum.
- Volume.
- Volatility.
- Fundamental.
- Market Trend.
- Anomaly.
- Correlation.

Fitur utama:

- Market universe selection.
- Screening filters.
- Custom screening conditions.
- Ranking.
- Scanner history.
- Instrument drill-down.

Market Scanner harus dapat melakukan screening terhadap instrumen di luar aset yang dimiliki pengguna.

## 7.5 AI Research Assistant

Modul untuk membantu pengguna memahami informasi dan hasil analisis.

Fitur utama:

- AI-assisted market research.
- Portfolio analysis explanation.
- Technical analysis interpretation.
- Research report generation.
- Information summarization.
- Structured research context.

AI berfungsi sebagai lapisan interpretasi. AI tidak menjadi sumber utama perhitungan finansial dan tidak boleh menghasilkan angka analisis tanpa data pendukung.

# 8. Product Design Direction

PIMS menggunakan pendekatan **Modern Financial Dashboard** dengan karakteristik visual yang terinspirasi dari aplikasi analisis keuangan profesional.

Prinsip desain:

- Professional financial interface.
- Information-dense but readable.
- Clear visual hierarchy.
- Consistent spacing and typography.
- Modular dashboard layout.
- Interactive charts.
- Data-focused visualization.
- Responsive interface.
- Consistent color semantics.

Desain tidak boleh terlihat seperti template SaaS generik.

Dashboard harus mengutamakan penyajian informasi yang relevan, bukan dekorasi visual yang berlebihan.

## 8.1 Dashboard Concept

Dashboard utama dirancang sebagai pusat informasi yang menampilkan:

- Portfolio overview.
- Total portfolio value.
- Portfolio performance.
- Asset allocation.
- Market overview.
- Watchlist.
- Risk summary.
- Recent activity.
- Market scanner highlights.

Komposisi dan prioritas setiap widget akan ditentukan lebih lanjut melalui `dashboard-spec.md`.

# 9. Technology Overview

Teknologi utama yang direncanakan:

| Layer | Technology |
|---|---|
| Frontend Framework | Next.js |
| UI Library | React |
| Programming Language | TypeScript |
| Styling | Tailwind CSS |
| Chart Library | TradingView Lightweight Charts |
| Backend Framework | Python / FastAPI |
| Data Validation | Pydantic |
| Database | PostgreSQL |
| ORM | SQLAlchemy (Proposed) |
| Migration | Alembic (Proposed) |
| Analytics | Pandas / NumPy / SciPy |
| Market Data | Provider APIs |
| AI Integration | LLM API |
| Containerization | Docker |
| Cache | Redis (Deferred / Optional) |

Teknologi yang berstatus Proposed atau Deferred tidak boleh dianggap sebagai keputusan final tanpa persetujuan.

Detail keputusan teknologi terdapat pada:

`docs/decisions/technical-decisions.md`

# 10. System Architecture

PIMS menggunakan pendekatan:

- Monorepo.
- Modular Monolith.
- Feature-oriented frontend.
- Domain-oriented backend modules.
- Provider Adapter Pattern.
- REST API.
- WebSocket.
- Centralized Market Data Processing.
- Deterministic Quantitative Engines.

Arsitektur Modular Monolith dipilih agar sistem tetap mudah dikembangkan dan dipelihara oleh tim kecil atau satu pengembang.

Setiap modul harus memiliki tanggung jawab yang jelas tanpa harus langsung dipisahkan menjadi microservices.

## 10.1 Main Architectural Layers

1. Presentation Layer.
2. API and Application Layer.
3. Domain Layer.
4. Market Data Layer.
5. Analytics and Intelligence Layer.
6. Persistence Layer.
7. External Integration Layer.

Detail arsitektur dijelaskan dalam folder:

`docs/architecture/`

# 11. Data Architecture Principles

Data merupakan bagian utama dari PIMS.

Prinsip pengelolaan data:

### 11.1 Data Source Transparency

Setiap market data harus memiliki informasi sumber.

### 11.2 Data Freshness

Sistem harus membedakan data LIVE, DELAYED, STALE, HISTORICAL, UNAVAILABLE, dan UNKNOWN.

### 11.3 Data Normalization

Data dari berbagai provider harus diubah menjadi internal data model yang konsisten.

### 11.4 Data Validation

Data harus diperiksa sebelum digunakan oleh analytics engines.

### 11.5 Data Integrity

Transaksi portofolio harus disimpan secara konsisten dan dapat ditelusuri.

### 11.6 Reproducibility

Hasil analisis harus memiliki metadata input, parameter, dan versi engine agar dapat diperiksa kembali.

# 12. Initial Development Scope

Pengembangan awal difokuskan pada fondasi sistem dan fitur yang paling penting.

## 12.1 MVP Scope

Fitur yang menjadi fokus MVP:

- Application foundation.
- Dashboard foundation.
- PostgreSQL integration.
- Portfolio management.
- Bybit market data integration.
- Historical market data.
- Real-time market updates.
- Lightweight Charts integration.
- Portfolio Performance Engine.
- Basic Risk Analysis Engine.
- Technical Analysis Engine.
- Basic Market Scanner.

## 12.2 Future Development

Fitur yang dikembangkan setelah fondasi MVP stabil:

- Finnhub integration.
- Alpaca integration.
- Indonesian stock data integration.
- Advanced allocation analytics.
- Correlation analysis.
- Market regime analysis.
- Fundamental analysis.
- Sentiment analysis.
- Macro analysis.
- Factor analysis.
- AI Research Assistant.
- Backtesting.
- Scenario analysis.
- Stress testing.
- Attribution analysis.

Pengembangan fitur masa depan tidak boleh menghambat stabilitas MVP.

# 13. Non-Goals

PIMS bukan dirancang sebagai:

- Cryptocurrency exchange.
- Stock brokerage platform.
- Trading execution platform.
- Custodial wallet.
- Public investment marketplace.
- Social trading platform.
- Automated fund management service.
- Guaranteed investment prediction system.

PIMS berfokus pada portfolio management, market monitoring, analytics, dan research support.

Fitur trading execution atau pengelolaan dana pihak ketiga memerlukan pembahasan, persetujuan, dan evaluasi keamanan serta regulasi tersendiri.

# 14. Security and Reliability Principles

PIMS harus menerapkan prinsip keamanan sejak tahap awal.

Ketentuan utama:

- API credentials disimpan di backend.
- Secrets tidak boleh dimasukkan ke source code.
- Environment variables digunakan untuk konfigurasi sensitif.
- Input harus divalidasi.
- Database operations harus menggunakan mekanisme yang aman.
- Error responses tidak boleh membocorkan secrets.
- Provider failures harus ditangani secara terkontrol.
- Data portofolio harus memiliki integritas.
- Operasi penting harus dapat diaudit.
- Backup dan recovery harus direncanakan.

Detail keamanan akan dijelaskan dalam `security-spec.md`.

# 15. Development Philosophy

Pengembangan PIMS mengikuti prinsip:

**Build Correctly Before Building Extensively.**

Artinya, fondasi sistem harus dibuat dengan benar sebelum menambahkan banyak fitur.

Prioritas pengembangan:

1. Architecture foundation.
2. Data foundation.
3. Portfolio foundation.
4. Market data integration.
5. Visualization.
6. Quantitative analytics.
7. Market Scanner.
8. AI Research.
9. Advanced analytics.

Setiap fitur harus memiliki spesifikasi, implementasi, pengujian, dan dokumentasi yang sesuai.

# 16. Success Criteria

PIMS dianggap berhasil mencapai fondasi MVP apabila:

- Pengguna dapat membuat dan mengelola beberapa portofolio.
- Transaksi dapat dicatat dan dihitung secara konsisten.
- Data pasar dapat diterima melalui provider yang telah diintegrasikan.
- Historical market data dapat ditampilkan pada chart.
- Streaming updates dapat diterima dan divisualisasikan apabila feed mendukung.
- Status freshness data ditampilkan secara benar.
- Portfolio performance dapat dihitung dan diverifikasi.
- Basic risk metrics dapat dihasilkan.
- Technical indicators dapat dihitung dan ditampilkan.
- Market Scanner dapat memproses market universe yang didukung.
- Kesalahan provider dan data dapat ditangani tanpa merusak seluruh sistem.
- Seluruh komponen utama dapat diuji secara terpisah.

# 17. Development Governance

OpenCode bertindak sebagai implementation agent.

Tanggung jawab OpenCode:

- Membaca seluruh dokumen proyek yang relevan.
- Menganalisis kebutuhan implementasi.
- Membuat implementation plan.
- Mengembangkan source code.
- Menjalankan testing.
- Melaporkan hasil implementasi.
- Mendokumentasikan perubahan.

OpenCode tidak boleh mengubah keputusan arsitektur, teknologi utama, database design, atau project scope tanpa persetujuan pengguna.

ChatGPT berperan sebagai architecture planner dan specification designer.

Pengguna bertindak sebagai Product Owner yang menyetujui keputusan produk dan perubahan penting.

# 18. Related Documents

Dokumen ini menjadi referensi awal untuk:

- `AGENTS.md`
- `README.md`
- `specifications/project/project-scope.md`
- `specifications/project/development-roadmap.md`
- `docs/architecture/system-architecture.md`
- `docs/architecture/application-architecture.md`
- `docs/architecture/data-flow.md`
- `docs/architecture/engine-architecture.md`
- `docs/database/database-design.md`
- `docs/decisions/technical-decisions.md`

---

# Final Statement

Personal Investment Management System dirancang sebagai platform pengelolaan dan analisis investasi personal yang mengintegrasikan portfolio management, market data, quantitative analytics, market screening, dan AI-assisted research.

Fokus utama pengembangan adalah membangun sistem yang modular, akurat, transparan, dan dapat dikembangkan secara bertahap.

Keberhasilan PIMS tidak hanya ditentukan oleh banyaknya fitur, tetapi juga oleh kualitas data, konsistensi perhitungan, keandalan sistem, dan kemampuan menyajikan informasi yang dapat dipahami serta diverifikasi.