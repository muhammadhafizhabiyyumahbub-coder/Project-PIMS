# Backend Specification
## Personal Investment Management System (PIMS)

**Document Version:** 1.0  
**Project Status:** Planning  
**Document Type:** Technical Specification  
**Last Updated:** November 2026

---

# 1. Purpose

Dokumen ini mendefinisikan spesifikasi teknis backend Personal Investment Management System (PIMS).

Backend merupakan pusat pemrosesan aplikasi yang bertanggung jawab terhadap business logic, data management, market data ingestion, quantitative calculations, API communication, dan integrasi AI.

Tujuan dokumen ini:

- Menentukan teknologi backend.
- Mendefinisikan arsitektur backend.
- Menentukan struktur aplikasi.
- Mengatur business logic.
- Mengatur database access.
- Mendefinisikan REST API dan WebSocket responsibilities.
- Mengatur market data processing.
- Mendefinisikan quantitative engines.
- Mengatur integrasi AI Research.
- Menetapkan standar keamanan, performa, dan testing.

Dokumen ini menjadi acuan utama OpenCode dalam mengimplementasikan backend PIMS.

# 2. Backend Overview

Backend PIMS menggunakan Python dan FastAPI dengan pendekatan Modular Monolith.

Backend bertanggung jawab terhadap seluruh proses yang membutuhkan pengolahan data, business rules, dan akses terhadap persistence layer.

Tanggung jawab utama:

1. Portfolio management.
2. Transaction processing.
3. Holdings calculation.
4. Market data acquisition.
5. Market data normalization.
6. Historical market data storage.
7. Realtime market data distribution.
8. Quantitative analysis.
9. Market Scanner processing.
10. AI Research orchestration.
11. Data validation.
12. API services.
13. Background processing.
14. Application monitoring.

Backend harus menjaga konsistensi data dan menjadi sumber kebenaran untuk seluruh perhitungan finansial.

# 3. Technology Stack

| Category | Technology | Status |
|---|---|---|
| Programming Language | Python | Approved |
| Backend Framework | FastAPI | Approved |
| Data Validation | Pydantic | Approved |
| Database | PostgreSQL | Approved |
| ORM | SQLAlchemy | Proposed |
| Migration | Alembic | Proposed |
| Data Processing | Pandas | Approved |
| Numerical Computing | NumPy | Approved |
| Scientific Computing | SciPy | Approved |
| Realtime Communication | WebSocket | Approved |
| Containerization | Docker | Approved |
| Cache | Redis | Deferred |
| Time-Series Extension | TimescaleDB | Deferred |

Library tambahan harus dievaluasi sebelum digunakan.

OpenCode tidak boleh menganggap teknologi berstatus Proposed atau Deferred sebagai keputusan final.

# 4. Backend Architecture

Backend menggunakan Modular Monolith Architecture.

Semua modul berjalan dalam satu aplikasi backend, tetapi setiap domain memiliki tanggung jawab dan batas dependency yang jelas.

## 4.1 Architectural Principles

Prinsip arsitektur:

- Modular Monolith.
- Separation of concerns.
- Domain-oriented design.
- Explicit service contracts.
- Provider independence.
- Centralized data processing.
- Deterministic financial calculations.
- Testable business logic.
- Controlled dependencies.
- Single source of truth.

## 4.2 Backend Layers

Backend dibagi menjadi beberapa lapisan konseptual.

| Layer | Responsibility |
|---|---|
| API Layer | REST and WebSocket interfaces |
| Application Layer | Use cases and orchestration |
| Domain Layer | Business rules and entities |
| Data Processing Layer | Ingestion and normalization |
| Intelligence Layer | Quantitative engines and AI |
| Persistence Layer | Database and repositories |
| Infrastructure Layer | External providers and runtime services |

## 4.3 Dependency Direction

```text
API Layer
    │
    ▼
Application Layer
    │
    ├──────────────► Domain Layer
    │
    ├──────────────► Engine Interfaces
    │
    └──────────────► Repository Interfaces
                              │
                              ▼
                       Infrastructure
                              │
                              ▼
                         PostgreSQL
```

Ketentuan:

- Domain logic tidak boleh bergantung pada FastAPI.
- Domain logic tidak boleh bergantung langsung pada provider eksternal.
- Engine tidak boleh mengakses tabel database secara langsung.
- Application services mengatur koordinasi antar-modul.
- Repository bertanggung jawab terhadap persistence operations.
- External provider access harus melalui adapter.

# 5. Project Structure

Struktur backend yang direkomendasikan:

```text
backend/
├── app/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── rest/
│   │   ├── websocket/
│   │   ├── dependencies/
│   │   └── middleware/
│   │
│   ├── core/
│   │   ├── exceptions/
│   │   ├── logging/
│   │   ├── security/
│   │   └── lifecycle/
│   │
│   ├── config/
│   │   ├── settings.py
│   │   └── providers.py
│   │
│   ├── domain/
│   │   ├── portfolio/
│   │   ├── holdings/
│   │   ├── transactions/
│   │   ├── assets/
│   │   └── shared/
│   │
│   ├── application/
│   │   ├── portfolio/
│   │   ├── market/
│   │   ├── analytics/
│   │   ├── scanner/
│   │   └── research/
│   │
│   ├── data/
│   │   ├── providers/
│   │   │   ├── crypto/
│   │   │   ├── us_stocks/
│   │   │   └── indonesia/
│   │   ├── ingestion/
│   │   ├── normalization/
│   │   ├── validation/
│   │   ├── aggregation/
│   │   └── storage/
│   │
│   ├── engines/
│   │   ├── technical/
│   │   ├── scanner/
│   │   ├── portfolio/
│   │   ├── risk/
│   │   ├── allocation/
│   │   ├── correlation/
│   │   ├── market_regime/
│   │   ├── fundamental/
│   │   ├── sentiment/
│   │   ├── macro/
│   │   ├── factor/
│   │   ├── attribution/
│   │   ├── backtesting/
│   │   └── scenario/
│   │
│   ├── ai/
│   │   ├── providers/
│   │   ├── research/
│   │   ├── context_builder/
│   │   └── report_generator/
│   │
│   ├── database/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── migrations/
│   │   └── session.py
│   │
│   └── schemas/
│       ├── api/
│       ├── market/
│       ├── portfolio/
│       └── analytics/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── pyproject.toml
└── Dockerfile
```

Struktur ini merupakan target organisasi backend. OpenCode tidak perlu membuat seluruh folder kosong sejak awal.

Implementasi harus mengikuti kebutuhan fase roadmap.

# 6. API Layer

API Layer menjadi interface komunikasi antara frontend dan backend.

Terdapat dua jenis komunikasi utama:

1. REST API.
2. WebSocket.

## 6.1 REST API Responsibilities

REST API digunakan untuk:

- Portfolio management.
- Transaction management.
- Holdings retrieval.
- Historical market data.
- Historical analytics.
- Scanner configuration.
- Scanner results.
- AI Research requests.
- Application settings.

## 6.2 WebSocket Responsibilities

WebSocket digunakan untuk:

- Realtime market updates.
- Candle updates.
- Scanner notifications.
- Market events.
- Connection status.

## 6.3 API Design Principles

- Consistent endpoint naming.
- Explicit request and response schemas.
- Input validation.
- Predictable error responses.
- Versioned API structure.
- Clear HTTP status codes.
- Proper pagination.
- Explicit timestamps.
- Consistent numeric precision.

Detail endpoint dan payload akan didefinisikan dalam `api-spec.md` dan `websocket-spec.md`.

# 7. Application Layer

Application Layer mengatur use cases dan koordinasi antar-modul.

Contoh application services:

- Portfolio Application Service.
- Transaction Application Service.
- Market Data Application Service.
- Analytics Application Service.
- Scanner Application Service.
- Research Application Service.

Tanggung jawab:

- Validate business requests.
- Coordinate domain operations.
- Invoke required engines.
- Access repositories.
- Manage transaction boundaries.
- Return application results.

Application services tidak boleh menampung seluruh perhitungan finansial secara langsung.

Perhitungan harus berada pada domain logic atau engine yang sesuai.

# 8. Domain Layer

Domain Layer berisi business rules utama PIMS.

Domain awal:

## 8.1 Portfolio Domain

Mengatur:

- Portfolio creation.
- Portfolio updates.
- Portfolio status.
- Base currency.
- Portfolio metadata.

## 8.2 Transaction Domain

Mengatur:

- Buy transactions.
- Sell transactions.
- Deposits.
- Withdrawals.
- Fees.
- Dividends.
- Transaction validation.

Transaksi merupakan sumber kebenaran untuk menghitung holdings dan cash balances.

## 8.3 Holdings Domain

Mengatur:

- Position quantity.
- Cost basis.
- Position status.
- Holding calculations.
- Derived holdings snapshots.

Holdings bukan sumber kebenaran independen dari transaction history.

## 8.4 Asset Domain

Mengatur:

- Asset identity.
- Market classification.
- Instrument metadata.
- Currency.
- Provider mappings.

# 9. Market Data Infrastructure

Market Data Infrastructure bertanggung jawab terhadap pengambilan dan pengolahan market data.

## 9.1 Initial Providers

| Market | Provider | Integration |
|---|---|---|
| Crypto | Bybit | REST + WebSocket |
| US Stocks | Finnhub | REST + WebSocket where supported |
| US Stocks | Alpaca | REST + WebSocket where supported |
| Indonesia Stocks | Yahoo Finance | Initial data source |

Ketersediaan data, realtime entitlement, rate limits, dan redistribution rights harus diverifikasi.

Backend tidak boleh mengasumsikan semua provider memberikan data realtime atau memiliki hak distribusi yang sama.

## 9.2 Provider Adapter

Setiap provider harus diintegrasikan melalui adapter tersendiri.

Tanggung jawab:

- Provider authentication.
- API requests.
- WebSocket connections.
- Provider-specific payload parsing.
- Error mapping.
- Rate-limit handling.
- Retry policies.

Engine dan application services tidak boleh bergantung langsung pada format payload provider.

## 9.3 Data Ingestion

Alur ingestion:

```text
External Provider
       │
       ▼
Provider Adapter
       │
       ▼
Ingestion Service
       │
       ▼
Normalization
       │
       ▼
Validation
       │
       ▼
Aggregation
       │
       ▼
Storage / Distribution
```

## 9.4 Data Normalization

Market data harus dinormalisasi menjadi format internal yang konsisten.

Data standar:

- Instrument ID.
- Symbol.
- Market.
- Provider.
- Exchange.
- Currency.
- Timestamp.
- Open.
- High.
- Low.
- Close.
- Volume.

Format internal tidak boleh bergantung pada struktur data salah satu provider.

## 9.5 Data Validation

Validasi mencakup:

- Timestamp validity.
- OHLC relationships.
- Numeric values.
- Duplicate records.
- Missing fields.
- Instrument mapping.
- Data ordering.
- Provider response integrity.

Data yang gagal validasi harus ditangani secara eksplisit dan tidak langsung disebarkan sebagai data valid.

## 9.6 Candle Aggregation

Jika provider menyediakan trade-level data atau price updates, backend dapat mengagregasikannya menjadi OHLCV candles.

Aturan:

- Open: first trade.
- High: highest price.
- Low: lowest price.
- Close: latest price.
- Volume: accumulated volume.

Jika provider sudah menyediakan candle dengan timeframe yang sesuai, gunakan data tersebut tanpa melakukan aggregation yang tidak diperlukan.

Aggregation harus memperhatikan market session dan batas interval.

# 10. Realtime Processing

Backend mengelola koneksi market data secara terpusat.

## 10.1 Centralized Provider Connections

Prinsip utama:

- Provider connections dikelola backend.
- Frontend tidak terhubung langsung ke provider.
- Satu sumber data digunakan bersama oleh banyak consumer.
- Subscription dikelola secara terpusat.
- Reconnection mengikuti kebijakan provider adapter.

## 10.2 Realtime Data Flow

```text
Provider WebSocket
        │
        ▼
Provider Adapter
        │
        ▼
Ingestion Pipeline
        │
        ▼
Normalization / Validation
        │
        ▼
Market Data Service
        │
        ├────────► Market Data Storage
        │
        ├────────► Technical Analysis
        │
        └────────► WebSocket Gateway
                         │
                         ▼
                      Frontend
```

## 10.3 Freshness Management

Backend harus menentukan freshness status berdasarkan timestamp dan kebijakan sumber data.

Status:

- LIVE.
- DELAYED.
- STALE.
- HISTORICAL.
- UNAVAILABLE.
- UNKNOWN.

Freshness tidak boleh ditentukan hanya berdasarkan kondisi koneksi WebSocket.

# 11. Quantitative Engines

Quantitative engines bertanggung jawab terhadap perhitungan analitis PIMS.

Setiap engine harus memiliki:

- Defined inputs.
- Defined outputs.
- Independent calculation logic.
- Validation.
- Test coverage.
- Explicit error handling.

## 11.1 Portfolio Performance Engine

Tanggung jawab:

- Portfolio valuation.
- Daily P&L.
- Realized P&L.
- Unrealized P&L.
- Total return.
- Historical performance.
- CAGR.
- Benchmark comparison.

## 11.2 Risk Engine

Tanggung jawab:

- Volatility.
- Maximum drawdown.
- Sharpe ratio.
- Sortino ratio.
- Value at Risk.
- Conditional Value at Risk.
- Beta.
- Concentration risk.

## 11.3 Allocation Engine

Tanggung jawab:

- Asset allocation.
- Market exposure.
- Sector exposure.
- Currency exposure.
- Instrument concentration.

## 11.4 Technical Analysis Engine

Tanggung jawab:

- SMA.
- EMA.
- RSI.
- MACD.
- Bollinger Bands.
- ATR.
- Stochastic.
- VWAP.

## 11.5 Correlation Engine

Tanggung jawab:

- Pairwise correlation.
- Correlation matrix.
- Rolling correlation.
- Data alignment.
- Diversification analysis.

## 11.6 Market Regime Engine

Tanggung jawab:

- Bullish regime.
- Bearish regime.
- Sideways regime.
- High-volatility regime.
- Low-volatility regime.

## 11.7 Market Scanner Engine

Tanggung jawab:

- Market universe processing.
- Eligibility checks.
- Screening rules.
- Filter evaluation.
- Instrument ranking.
- Scanner results.
- Scanner scheduling.

Scanner harus mampu memproses market universe yang tersedia, bukan hanya instrumen yang dimiliki pengguna.

## 11.8 Additional Engines

Dikembangkan secara bertahap:

- Fundamental Analysis.
- Sentiment Analysis.
- Macro Analysis.
- Factor Analysis.
- Attribution.
- Backtesting.
- Scenario Analysis.
- Stress Testing.
- Liquidity Analysis.
- Tax and Fee Analysis.

Engine tambahan tidak termasuk kewajiban implementasi awal MVP.

# 12. Engine Execution Management

Engine dapat dijalankan melalui beberapa mekanisme.

| Execution Type | Example |
|---|---|
| Request-driven | Portfolio analytics request |
| Scheduled | Periodic scanner execution |
| Event-driven | Market data update |
| On-demand | Backtesting or scenario analysis |

Ketentuan:

- Engine tidak boleh dijalankan tanpa kebutuhan.
- Perhitungan berat tidak boleh menghambat API request yang tidak terkait.
- Hasil analisis harus memiliki calculation timestamp.
- Engine failures harus dapat diisolasi.
- Hasil yang dapat direproduksi harus memiliki calculation parameters dan data references.

Background job infrastructure dapat diperkenalkan setelah kebutuhan implementasi jelas.

# 13. Market Scanner Architecture

Market Scanner merupakan modul backend independen.

Pipeline:

```text
Market Universe
       │
       ▼
Eligibility Check
       │
       ▼
Data Availability Check
       │
       ▼
Scanner Processor
       │
       ▼
Rule Evaluation
       │
       ▼
Ranking Engine
       │
       ▼
Scanner Results
       │
       ▼
API / WebSocket
```

Kategori scanner:

- Technical.
- Momentum.
- Volume.
- Volatility.
- Fundamental.
- Market Trend.
- Anomaly.
- Correlation.

Scanner harus memiliki batas data yang jelas dan tidak boleh melakukan request provider secara terpisah untuk setiap instrumen jika shared data infrastructure dapat digunakan.

# 14. AI Research Infrastructure

AI Research merupakan lapisan interpretasi dan penyusunan laporan.

## 14.1 Responsibilities

- Research request handling.
- Context building.
- Engine result retrieval.
- External AI provider integration.
- Report generation.
- Output validation.
- Research history.

## 14.2 AI Provider Adapter

AI provider harus diakses melalui abstraction layer.

Hal ini memungkinkan penggantian atau penambahan AI provider tanpa mengubah seluruh research module.

## 14.3 Context Builder

Context Builder mengumpulkan:

- Instrument metadata.
- Historical market data references.
- Technical analysis results.
- Fundamental data.
- Risk metrics.
- Portfolio context.
- Relevant news sources.

Hanya data yang relevan dan tersedia yang boleh dimasukkan.

## 14.4 Calculation Boundary

AI tidak boleh menggantikan deterministic financial calculations.

Contoh:

- Risk Engine menghitung volatility.
- Portfolio Engine menghitung return.
- Technical Engine menghitung RSI.
- AI Research menjelaskan dan menginterpretasikan hasil.

AI output harus dibedakan dari hasil perhitungan sistem.

# 15. Database Integration

PostgreSQL merupakan primary database PIMS.

Backend menggunakan persistence layer untuk mengelola akses database.

## 15.1 Database Responsibilities

- Portfolio persistence.
- Transaction persistence.
- Cash ledger persistence.
- Holdings snapshots.
- Market data storage.
- Analytics results.
- Scanner results.
- Research reports.
- Audit records.
- Job execution records.

## 15.2 Repository Pattern

Database access harus diorganisasi melalui repository atau mekanisme persistence abstraction yang setara.

Engine tidak boleh melakukan SQL queries secara langsung.

## 15.3 Transaction Management

Operasi yang mengubah data finansial harus memiliki transaction boundaries yang jelas.

Contoh:

- Create transaction.
- Update transaction.
- Delete transaction.
- Cash ledger update.
- Holdings recalculation.

Jika terjadi kegagalan, operasi yang saling bergantung tidak boleh menghasilkan kondisi data setengah selesai.

## 15.4 Data Integrity

- Gunakan constraints yang sesuai.
- Gunakan decimal-safe numeric types untuk nominal finansial.
- Gunakan timezone-aware timestamps.
- Gunakan stable internal identifiers.
- Hindari floating-point arithmetic untuk penyimpanan nominal uang.
- Pastikan transaksi dapat diaudit.

# 16. Caching Strategy

Redis belum menjadi dependency wajib MVP.

Caching dapat diperkenalkan jika hasil pengukuran menunjukkan kebutuhan.

Kandidat data:

- Latest market quotes.
- Active market subscriptions.
- Frequently accessed market metadata.
- Reusable analytics results.
- Scanner results.

Cache tidak boleh menjadi sumber kebenaran untuk transaksi atau portfolio records.

Setiap cache harus memiliki expiration dan invalidation policy yang jelas.

# 17. Configuration Management

Konfigurasi backend harus dikelola melalui environment variables dan application settings.

Kategori konfigurasi:

- Database connection.
- Provider credentials.
- AI provider credentials.
- API settings.
- WebSocket settings.
- Logging.
- Runtime environment.

Ketentuan:

- Secrets tidak boleh disimpan di source code.
- Gunakan `.env.example` untuk dokumentasi konfigurasi.
- Jangan commit file `.env` berisi credentials.
- Validate required settings saat startup.
- Jangan menampilkan secrets pada logs.

# 18. Security Requirements

Backend harus menerapkan:

## 18.1 Input Validation

Semua input eksternal harus divalidasi.

## 18.2 Secrets Management

Provider credentials dan AI API keys harus berada di backend.

## 18.3 Database Security

- Use parameterized queries.
- Protect database credentials.
- Limit database privileges.
- Avoid exposing internal database errors.

## 18.4 API Security

- Define CORS policy.
- Apply request validation.
- Handle rate limits where necessary.
- Protect sensitive operations.
- Use authentication and authorization if introduced.

## 18.5 Logging Security

Logs tidak boleh menyimpan:

- API secrets.
- Passwords.
- Authentication tokens.
- Sensitive personal data.

Authentication architecture harus mengikuti security specification tersendiri ketika fitur tersebut ditetapkan.

# 19. Error Handling

Backend harus menggunakan standardized error handling.

Kategori:

- Validation errors.
- Business rule errors.
- Provider errors.
- Database errors.
- Engine calculation errors.
- WebSocket errors.
- AI provider errors.
- Internal application errors.

Ketentuan:

- Error harus memiliki kategori yang jelas.
- Internal stack traces tidak boleh dikirim ke frontend.
- Provider failures harus dapat diisolasi.
- Retry hanya dilakukan untuk kegagalan yang memang dapat dipulihkan.
- Financial operations tidak boleh diulang secara sembarangan sehingga menimbulkan duplikasi transaksi.
- Logs harus menyediakan konteks yang cukup untuk debugging.

# 20. Logging and Monitoring

Backend harus menyediakan observability dasar.

Informasi yang dicatat:

- Application startup.
- API request status.
- Provider connection status.
- Data ingestion failures.
- Data validation failures.
- WebSocket connection events.
- Engine execution status.
- Database failures.
- Background job execution.
- AI request failures.

Log harus memiliki timestamp dan severity level.

Metrics yang dapat dikembangkan:

- API latency.
- Provider latency.
- WebSocket connection count.
- Data freshness.
- Ingestion throughput.
- Engine execution duration.
- Error rate.

# 21. Performance Requirements

Backend harus dirancang agar dapat memproses data pasar dan analisis portofolio secara efisien.

Ketentuan:

- Gunakan shared provider connections.
- Hindari repeated external API requests.
- Batasi historical data retrieval.
- Gunakan database indexes yang relevan.
- Hindari blocking operations pada event loop.
- Pisahkan heavy calculations dari request handling jika diperlukan.
- Gunakan pagination.
- Hindari redundant calculations.
- Terapkan controlled concurrency.
- Monitor penggunaan memory dan CPU.

Target numerik untuk latency dan throughput ditentukan melalui performance testing setelah implementasi awal tersedia.

# 22. Testing Requirements

Backend harus memiliki pengujian bertingkat.

## 22.1 Unit Tests

Menguji:

- Domain rules.
- Financial calculations.
- Market data normalization.
- Candle aggregation.
- Data validation.
- Indicator calculations.
- Scanner filters.

## 22.2 Integration Tests

Menguji:

- Database repositories.
- API endpoints.
- Provider adapters.
- WebSocket handling.
- Application services.
- Engine integration.

## 22.3 End-to-End Tests

Menguji alur utama:

- Create portfolio.
- Record transaction.
- Calculate holdings.
- Retrieve portfolio valuation.
- Retrieve historical market data.
- Receive realtime updates.
- Run scanner.
- Generate AI research report.

## 22.4 Data Accuracy Tests

Perhitungan finansial harus memiliki test cases dengan expected results yang diketahui.

Setiap engine harus menguji:

- Normal inputs.
- Boundary values.
- Missing data.
- Invalid data.
- Zero values.
- Negative values jika relevan.
- Insufficient historical observations.

# 23. Implementation Roadmap

Implementasi backend mengikuti development roadmap utama.

| Phase | Backend Component | Priority |
|---|---|---|
| 1 | FastAPI foundation | Critical |
| 2 | Configuration and database foundation | Critical |
| 3 | Domain and repository foundation | Critical |
| 4 | Portfolio and transaction services | High |
| 5 | Market data provider adapters | High |
| 6 | Normalization and storage | High |
| 7 | REST API integration | High |
| 8 | WebSocket infrastructure | High |
| 9 | Portfolio analytics engines | High |
| 10 | Technical Analysis Engine | High |
| 11 | Market Scanner Engine | High |
| 12 | Additional providers | Medium |
| 13 | Advanced analytics | Medium |
| 14 | AI Research infrastructure | Medium |

Fase dapat memiliki pekerjaan paralel apabila dependency yang diperlukan telah tersedia.

# 24. Acceptance Criteria

Backend specification dianggap telah diimplementasikan apabila:

- FastAPI application berjalan.
- Modular Monolith structure tersedia.
- Configuration management berfungsi.
- PostgreSQL terintegrasi.
- Database access terorganisasi.
- Portfolio domain berfungsi.
- Transaction processing memiliki integrity.
- Holdings dapat dihitung dari transaksi.
- Provider adapters dapat digunakan.
- Market data dinormalisasi.
- Market data validation tersedia.
- Historical market data dapat diakses.
- WebSocket gateway berfungsi.
- Data freshness dapat ditentukan.
- Quantitative engines dapat dijalankan.
- Scanner dapat memproses market universe yang didukung.
- AI Research memiliki provider abstraction.
- Error handling tersedia.
- Logging tersedia.
- Unit dan integration tests berjalan.
- Tidak ada provider secrets yang terekspos.

# 25. Related Documents

- `AGENTS.md`
- `README.md`
- `docs/architecture/system-architecture.md`
- `docs/architecture/application-architecture.md`
- `docs/architecture/data-flow.md`
- `docs/architecture/engine-architecture.md`
- `docs/database/database-design.md`
- `docs/decisions/technical-decisions.md`
- `specifications/project/project-overview.md`
- `specifications/project/project-scope.md`
- `specifications/project/development-roadmap.md`
- `specifications/backend/api-spec.md`
- `specifications/backend/websocket-spec.md`
- `specifications/data/market-data-spec.md`
- `specifications/data/provider-integration-spec.md`
- `specifications/data/normalization-spec.md`
- `specifications/security/security-spec.md`
- `specifications/testing/testing-requirements.md`

---

# Final Principle

Backend PIMS harus menjadi pusat pengelolaan data dan perhitungan finansial.

Setiap modul harus memiliki tanggung jawab yang jelas, setiap data harus memiliki sumber yang dapat ditelusuri, dan setiap perhitungan harus dapat diuji serta direproduksi.

Prioritas utama adalah membangun backend yang akurat, konsisten, modular, dan dapat dikembangkan secara bertahap tanpa menciptakan kompleksitas arsitektur yang tidak diperlukan.