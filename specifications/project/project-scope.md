# Project Scope
## Personal Investment Management System (PIMS)

**Document Version:** 1.0  
**Project Status:** Planning  
**Document Type:** Project Scope Specification  
**Last Updated:** November 2026

---

# 1. Purpose

Dokumen ini mendefinisikan ruang lingkup pengembangan Personal Investment Management System (PIMS).

Tujuannya adalah menentukan:

- Fitur yang termasuk dalam MVP.
- Fitur yang dikembangkan setelah MVP.
- Fitur yang tidak termasuk dalam proyek.
- Batasan teknis dan fungsional.
- Prioritas implementasi.
- Kriteria penerimaan setiap tahap pengembangan.

Dokumen ini menjadi acuan bagi OpenCode dalam menentukan pekerjaan yang harus dan tidak boleh dilakukan selama proses implementasi.

# 2. Project Scope Overview

PIMS dikembangkan sebagai aplikasi pengelolaan dan analisis investasi personal.

Ruang lingkup utama mencakup enam area:

1. Portfolio Management.
2. Market Data and Visualization.
3. Quantitative Analytics.
4. Market Scanner.
5. AI Research Assistant.
6. Application Infrastructure.

Pengembangan dilakukan secara bertahap menggunakan pendekatan MVP.

Fokus awal adalah menghasilkan aplikasi yang dapat digunakan untuk mencatat portofolio, mengambil data pasar, menampilkan chart, dan melakukan analisis dasar.

# 3. MVP Scope

MVP merupakan versi awal PIMS yang harus memiliki fondasi sistem dan fungsi utama yang dapat digunakan secara terintegrasi.

## 3.1 Application Foundation

<badge color="success">In Scope — MVP</badge>

Fitur:

- Monorepo project structure.
- Next.js frontend.
- FastAPI backend.
- PostgreSQL integration.
- Environment configuration.
- Docker development environment.
- REST API foundation.
- WebSocket foundation.
- Logging and error handling.
- Basic automated testing.

Batasan:

- Tidak membuat microservices.
- Tidak membuat infrastruktur deployment kompleks.
- Redis belum diwajibkan.
- Authentication tingkat lanjut belum menjadi prioritas MVP.

## 3.2 Dashboard

<badge color="success">In Scope — MVP</badge>

Fitur:

- Main dashboard layout.
- Sidebar navigation.
- Portfolio overview.
- Portfolio value.
- Basic performance summary.
- Market overview.
- Watchlist.
- Recent transactions.
- Basic risk summary.
- Data freshness indicators.

Dashboard harus menggunakan desain Modern Financial Dashboard.

Batasan:

- Tidak semua widget harus memiliki konfigurasi kustom.
- Tidak memerlukan dashboard builder.
- Tidak memerlukan drag-and-drop layout pada MVP.

## 3.3 Portfolio Management

<badge color="success">In Scope — MVP</badge>

Fitur:

- Create portfolio.
- Edit portfolio.
- Delete portfolio dengan validasi dan aturan integritas data.
- Multiple portfolios.
- Portfolio overview.
- Asset holdings.
- Transaction management.
- Cash balance.
- Transaction history.
- Basic portfolio valuation.

Jenis transaksi awal:

- Buy.
- Sell.
- Deposit.
- Withdrawal.

Ketentuan:

- Setiap transaksi harus terhubung dengan portofolio.
- Setiap transaksi harus memiliki asset atau cash movement yang sesuai.
- Holdings dihitung berdasarkan transaksi.
- Perubahan transaksi harus memicu pembaruan data turunan yang relevan.
- Perhitungan harus memiliki aturan yang terdokumentasi.

Batasan:

- Tidak ada integrasi broker.
- Tidak ada automatic trade execution.
- Tidak ada sinkronisasi akun investasi eksternal.
- Corporate actions kompleks belum termasuk MVP.

## 3.4 Market Data Integration

<badge color="success">In Scope — MVP</badge>

Provider awal:

- Bybit untuk cryptocurrency.

Fitur:

- Market instrument retrieval.
- Historical OHLCV retrieval.
- Latest price retrieval.
- WebSocket market stream.
- Market data normalization.
- Market data validation.
- Provider connection management.
- Data freshness tracking.

Ketentuan:

- Menggunakan provider adapter.
- API credentials disimpan di backend.
- Historical data dan streaming data harus memiliki jalur pemrosesan yang jelas.
- Provider limitations harus ditangani.
- Data yang tidak tersedia tidak boleh diganti dengan data palsu yang terlihat seperti data live.

Batasan:

- MVP tidak menjamin seluruh cryptocurrency tersedia.
- Tidak ada jaminan bahwa setiap timeframe tersedia dari provider.
- Tidak ada redistribusi data yang melanggar ketentuan provider.
- Integrasi US stocks dan IDX belum diwajibkan.

## 3.5 Chart Engine

<badge color="success">In Scope — MVP</badge>

Menggunakan TradingView Lightweight Charts.

Fitur:

- Candlestick chart.
- Line chart.
- Area chart.
- Volume histogram.
- Historical candle loading.
- Real-time candle updates.
- Timeframe selection.
- Crosshair.
- Zoom and scroll.
- Instrument selection.

Ketentuan:

- Historical data menggunakan REST API.
- Streaming updates menggunakan WebSocket.
- Chart hanya bertanggung jawab terhadap visualisasi.
- Backend menyediakan data yang telah dinormalisasi.
- Timestamp dan urutan candle harus konsisten.

Batasan:

- Advanced drawing tools belum termasuk MVP.
- Tidak membuat charting engine sendiri.
- Tidak menyalin keseluruhan fitur TradingView.
- Tidak menganggap Lightweight Charts sebagai penyedia data pasar.

## 3.6 Portfolio Performance Engine

<badge color="success">In Scope — MVP</badge>

Fitur:

- Portfolio valuation.
- Total portfolio value.
- Daily P&L.
- Realized P&L.
- Unrealized P&L.
- Basic return calculation.
- Portfolio performance history.

Ketentuan:

- Perhitungan menggunakan transaksi dan market prices.
- Metodologi perhitungan harus terdokumentasi.
- Hasil harus dapat diverifikasi menggunakan test cases.
- Perhitungan harus mempertimbangkan currency yang digunakan.

Batasan:

- Advanced performance attribution belum termasuk.
- Benchmark comparison dapat ditunda.
- Tax-adjusted performance belum termasuk.

## 3.7 Basic Risk Analysis Engine

<badge color="success">In Scope — MVP</badge>

Fitur:

- Historical volatility.
- Maximum drawdown.
- Basic Sharpe ratio.
- Portfolio concentration.
- Asset exposure.

Ketentuan:

- Menggunakan data return yang valid.
- Periode analisis harus jelas.
- Perhitungan harus menangani insufficient data.
- Hasil harus menyertakan status dan metadata.

Batasan:

- Advanced VaR dan CVaR dapat ditunda.
- Stress testing belum termasuk.
- Advanced factor risk belum termasuk.

## 3.8 Technical Analysis Engine

<badge color="success">In Scope — MVP</badge>

Indikator awal:

- SMA.
- EMA.
- RSI.
- MACD.
- Bollinger Bands.
- ATR.

Fitur:

- Indicator calculation.
- Configurable parameters.
- Historical indicator output.
- Chart indicator visualization.

Ketentuan:

- Perhitungan dilakukan di backend.
- Hasil harus konsisten untuk input dan parameter yang sama.
- Indicator warm-up period harus diperhitungkan.
- Data tidak mencukupi harus menghasilkan status yang jelas.

Batasan:

- Tidak membangun seluruh indikator teknikal yang tersedia di pasar.
- Tidak membuat sistem prediksi harga otomatis.

## 3.9 Basic Market Scanner

<badge color="success">In Scope — MVP</badge>

Fitur:

- Supported market universe.
- Instrument eligibility check.
- Basic technical filters.
- Momentum filters.
- Volume filters.
- Ranking.
- Scanner results.
- Scanner execution history.

Ketentuan:

- Scanner harus dapat memindai instrumen di luar portfolio holdings.
- Universe hanya mencakup instrumen yang didukung provider dan memiliki data memadai.
- Setiap hasil harus memiliki timestamp.
- Ranking harus menggunakan aturan yang terdokumentasi.

Batasan:

- Fundamental screening dapat ditunda.
- Anomaly detection lanjutan belum termasuk.
- Correlation screening dapat ditunda.
- Scanner tidak melakukan transaksi otomatis.

# 4. Post-MVP Scope

Fitur berikut direncanakan setelah MVP stabil.

## 4.1 Additional Market Providers

<badge color="info">Post-MVP</badge>

- Finnhub integration.
- Alpaca integration.
- Indonesian stock data integration.
- Additional crypto providers.
- Provider failover.
- Advanced market data source selection.

Setiap integrasi harus melalui evaluasi API access, pricing, data coverage, rate limits, licensing, dan real-time entitlements.

## 4.2 Advanced Portfolio Analytics

- Advanced performance attribution.
- Benchmark comparison.
- Advanced allocation analysis.
- Currency exposure analysis.
- Portfolio contribution analysis.
- Advanced portfolio reporting.

## 4.3 Advanced Risk Analysis

- Value at Risk.
- Conditional Value at Risk.
- Beta analysis.
- Rolling volatility.
- Advanced drawdown analysis.
- Stress testing.
- Scenario analysis.
- Liquidity analysis.

## 4.4 Advanced Market Analysis

- Correlation matrix.
- Rolling correlation.
- Market regime detection.
- Fundamental analysis.
- Sentiment analysis.
- Macro analysis.
- Factor analysis.

## 4.5 Advanced Market Scanner

- Fundamental screening.
- Volatility screening.
- Anomaly detection.
- Correlation screening.
- Custom scanner configurations.
- Advanced ranking models.
- Scanner alerts.
- Advanced scheduling.

## 4.6 AI Research Assistant

- AI-assisted market research.
- Portfolio research.
- Technical analysis interpretation.
- Fundamental research summaries.
- Market news summarization.
- Research report generation.
- Multi-model provider support.
- Research history.

AI Research akan dikembangkan setelah data pipeline dan quantitative engines memiliki output yang cukup stabil.

## 4.7 Advanced Infrastructure

- Redis caching.
- Background job processing.
- Advanced monitoring.
- Authentication and authorization improvements.
- Deployment automation.
- Advanced backup and recovery.
- Performance optimization.

# 5. Out of Scope

Fitur berikut tidak termasuk dalam ruang lingkup proyek saat ini.

| Feature | Reason |
|---|---|
| Brokerage integration | Bukan fokus awal PIMS |
| Automatic trading execution | Memerlukan evaluasi keamanan dan regulasi terpisah |
| Custodial wallet | Bukan tujuan produk |
| Public marketplace | Tidak diperlukan untuk penggunaan personal |
| Social trading | Di luar kebutuhan utama |
| Public multi-tenant SaaS | Produk awal berfokus pada penggunaan personal |
| Fund management for third parties | Di luar ruang lingkup awal |
| Guaranteed price prediction | Tidak dapat dijamin secara ilmiah |
| Autonomous investment execution | Tidak termasuk dalam desain awal |

Fitur di luar ruang lingkup hanya dapat ditambahkan melalui perubahan scope yang disetujui.

# 6. Functional Scope Summary

| Module | MVP | Post-MVP |
|---|---|---|
| Application Foundation | Yes | Improvements |
| Dashboard | Basic | Advanced customization |
| Portfolio Management | Core features | Advanced accounting |
| Crypto Market Data | Bybit | Additional providers |
| US Stock Data | No | Finnhub / Alpaca |
| IDX Market Data | No | Provider evaluation |
| Chart Engine | Core charting | Advanced tools |
| Performance Engine | Basic | Advanced attribution |
| Risk Engine | Basic | Advanced risk metrics |
| Technical Analysis | Core indicators | Additional indicators |
| Allocation Engine | Basic exposure | Advanced allocation |
| Correlation Engine | Deferred | Full implementation |
| Market Regime Engine | Deferred | Full implementation |
| Market Scanner | Basic | Advanced screening |
| AI Research | No | Full implementation |
| Backtesting | No | Future |
| Scenario Analysis | No | Future |

# 7. Non-Functional Scope

Selain fitur utama, PIMS memiliki kebutuhan non-functional.

## 7.1 Performance

- API harus memiliki response time yang wajar.
- Market updates harus didistribusikan secara efisien.
- Historical chart loading harus memperhatikan jumlah data.
- Analytics tidak boleh memblokir seluruh aplikasi.
- Database queries harus menggunakan indexing yang sesuai.

Target performa kuantitatif akan ditetapkan dalam testing requirements setelah baseline pengukuran tersedia.

## 7.2 Reliability

- Provider connection harus memiliki reconnect handling.
- Database errors harus ditangani.
- Data validation harus diterapkan.
- Analytics failures harus memberikan status yang jelas.
- Partial provider failure tidak boleh menghentikan seluruh sistem.

## 7.3 Security

- API credentials tidak boleh berada di frontend.
- Secrets harus menggunakan environment configuration.
- Input validation harus diterapkan.
- Database access harus terkontrol.
- Sensitive information tidak boleh muncul dalam logs.

## 7.4 Maintainability

- Modul harus memiliki tanggung jawab yang jelas.
- Business logic harus terpisah dari presentation.
- Provider integration harus menggunakan adapter.
- Engines harus dapat diuji secara independen.
- Perubahan schema harus menggunakan migration.

## 7.5 Data Integrity

- Transaksi harus konsisten.
- Holdings harus dapat direkonstruksi.
- Market data harus memiliki source metadata.
- Analytics harus memiliki calculation metadata.
- Timestamp harus menggunakan standar yang konsisten.

# 8. Implementation Priority

Urutan pengembangan MVP:

| Phase | Scope | Priority |
|---|---|---|
| 1 | Project foundation and database | Critical |
| 2 | Backend API and domain foundation | Critical |
| 3 | Portfolio management | Critical |
| 4 | Bybit market data integration | Critical |
| 5 | Market data normalization and validation | Critical |
| 6 | Historical chart integration | High |
| 7 | Real-time WebSocket updates | High |
| 8 | Portfolio performance | High |
| 9 | Basic risk analysis | High |
| 10 | Technical analysis | High |
| 11 | Basic Market Scanner | High |
| 12 | Dashboard integration and stabilization | High |

Tahapan dapat disesuaikan berdasarkan dependency teknis, tetapi perubahan prioritas harus didokumentasikan.

# 9. Scope Change Management

Setiap perubahan scope harus mengikuti proses berikut:

1. Perubahan kebutuhan diidentifikasi.
2. Dampak terhadap arsitektur dianalisis.
3. Dampak terhadap database dan API diperiksa.
4. Dampak terhadap jadwal dan kompleksitas dievaluasi.
5. Perubahan diajukan kepada Product Owner.
6. Implementasi dilakukan setelah mendapatkan persetujuan.

OpenCode tidak boleh memperluas scope secara otomatis hanya karena menemukan kemungkinan fitur tambahan.

Fitur tambahan dapat diajukan sebagai proposal terpisah.

# 10. Acceptance Criteria

MVP dapat dianggap memenuhi ruang lingkup apabila:

- Aplikasi dapat dijalankan melalui development environment yang terdokumentasi.
- Pengguna dapat membuat dan mengelola beberapa portofolio.
- Transaksi dapat dicatat dan diproses secara konsisten.
- Portfolio holdings dapat dihitung dari transaksi.
- Bybit market data dapat diambil melalui integrasi backend.
- Historical candles dapat ditampilkan pada chart.
- Streaming updates dapat ditampilkan jika tersedia dari provider.
- Data freshness ditampilkan dengan benar.
- Performance metrics dapat dihitung dan diuji.
- Basic risk metrics dapat dihasilkan.
- Technical indicators dapat dihitung dan divisualisasikan.
- Market Scanner dapat melakukan screening terhadap supported market universe.
- Error handling tersedia untuk kegagalan utama.
- Automated tests tersedia untuk business logic dan data processing.
- Dokumentasi implementasi diperbarui.

Fitur tidak dianggap selesai hanya karena tampil di frontend. Backend processing, data integrity, dan pengujian harus tersedia sesuai kebutuhan fitur.

# 11. Assumptions and Constraints

## 11.1 Assumptions

- PIMS dikembangkan untuk penggunaan personal.
- Pengembangan awal dilakukan dengan pendekatan Modular Monolith.
- Bybit menjadi provider pertama untuk market data.
- PostgreSQL menjadi primary database.
- Lightweight Charts menjadi chart visualization library.
- Quantitative calculations dilakukan di backend.
- AI Research dikembangkan setelah fondasi analytics stabil.

## 11.2 Constraints

- Data provider memiliki keterbatasan akses dan lisensi.
- Tidak semua market menyediakan real-time data secara gratis.
- API rate limits harus diperhatikan.
- Kualitas analytics bergantung pada kualitas data.
- Satu pengembang memiliki keterbatasan waktu dan kapasitas.
- Fitur lanjutan harus mengikuti kesiapan fondasi sistem.

# 12. Related Documents

- `AGENTS.md`
- `specifications/project/project-overview.md`
- `specifications/project/development-roadmap.md`
- `docs/architecture/system-architecture.md`
- `docs/architecture/application-architecture.md`
- `docs/architecture/data-flow.md`
- `docs/architecture/engine-architecture.md`
- `docs/database/database-design.md`
- `docs/decisions/technical-decisions.md`
- `specifications/testing/testing-requirements.md`

---

# Final Principle

Ruang lingkup PIMS harus tetap terkontrol selama pengembangan.

Prioritas utama adalah membangun fondasi yang benar, mengintegrasikan data pasar dengan baik, menjaga integritas portofolio, dan menghasilkan analisis yang dapat diverifikasi.

Fitur tambahan hanya dikembangkan setelah kebutuhan utama MVP terpenuhi dan sistem memiliki stabilitas yang memadai.