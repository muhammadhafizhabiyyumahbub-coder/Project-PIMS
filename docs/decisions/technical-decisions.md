# Technical Decisions
## Personal Investment Management System (PIMS)

**Document Version:** 1.0  
**Status:** Architecture Decision Record  
**Last Updated:** November 2026

---

# 1. Purpose

Dokumen ini berisi keputusan teknis dan arsitektur yang digunakan dalam pengembangan Personal Investment Management System (PIMS).

Dokumen ini menjadi referensi bagi seluruh proses pengembangan agar pemilihan teknologi, struktur aplikasi, integrasi data, dan implementasi sistem tetap konsisten.

Setiap keputusan harus memiliki alasan teknis yang jelas dan mempertimbangkan:

- Maintainability.
- Scalability.
- Performance.
- Reliability.
- Data integrity.
- Security.
- Development complexity.
- Long-term extensibility.

Dokumen ini juga menjadi batasan bagi OpenCode ketika melakukan implementasi.

OpenCode tidak diperbolehkan mengubah keputusan arsitektur utama tanpa persetujuan pengguna.

# 2. Decision Status

Setiap keputusan memiliki salah satu status berikut:

| Status | Description |
|---|---|
| APPROVED | Keputusan telah disetujui dan menjadi acuan implementasi |
| PROPOSED | Rekomendasi teknis yang masih membutuhkan persetujuan |
| DEFERRED | Keputusan ditunda sampai kebutuhan lebih jelas |
| REJECTED | Alternatif yang tidak digunakan |
| SUPERSEDED | Keputusan telah digantikan keputusan baru |

Status pada dokumen ini harus diperbarui ketika keputusan telah disetujui atau berubah.

# 3. Technology Stack Decisions

## 3.1 Frontend Framework

**Decision:** Next.js + React + TypeScript.

**Status:** APPROVED

Alasan:

- Mendukung aplikasi berbasis React.
- Memiliki routing dan struktur aplikasi yang terorganisasi.
- Mendukung TypeScript.
- Cocok untuk dashboard dengan banyak komponen.
- Memiliki ekosistem yang luas.

Implementation rules:

- Gunakan TypeScript untuk seluruh komponen frontend.
- Gunakan `.tsx` untuk React components.
- Hindari penggunaan `any`.
- Pisahkan UI components, features, hooks, services, dan state management.
- Jangan menempatkan seluruh logika aplikasi di satu komponen.

## 3.2 Styling

**Decision:** Tailwind CSS.

**Status:** APPROVED

Alasan:

- Mempermudah konsistensi desain.
- Mendukung pengembangan komponen modular.
- Mempermudah responsive layout.
- Cocok untuk dashboard dengan banyak variasi komponen.

Implementation rules:

- Gunakan design tokens.
- Pertahankan konsistensi spacing, typography, colors, dan sizing.
- Hindari inline styling yang tidak diperlukan.
- Jangan membuat setiap komponen memiliki sistem desain sendiri.

## 3.3 Backend Framework

**Decision:** Python + FastAPI.

**Status:** APPROVED

Alasan:

- Python memiliki ekosistem quantitative computing yang kuat.
- FastAPI mendukung asynchronous endpoints.
- Mendukung validasi menggunakan Pydantic.
- Cocok untuk REST API dan WebSocket.
- Mudah diintegrasikan dengan library analisis finansial.

Implementation rules:

- Gunakan Pydantic untuk validasi request dan response.
- Pisahkan API layer dari business logic.
- Gunakan asynchronous processing apabila memang dibutuhkan.
- Jangan menempatkan seluruh business logic di endpoint.
- Gunakan dependency injection untuk pengelolaan dependency.

## 3.4 Primary Database

**Decision:** PostgreSQL.

**Status:** APPROVED

Alasan:

- Mendukung relational data.
- Memiliki transaction integrity.
- Mendukung indexing dan query kompleks.
- Cocok untuk transaksi dan data portofolio.
- Mendukung JSONB untuk metadata fleksibel.

Implementation rules:

- Gunakan relational schema.
- Gunakan foreign keys dan constraints.
- Gunakan NUMERIC untuk data finansial yang membutuhkan presisi.
- Gunakan TIMESTAMPTZ untuk timestamp absolut.
- Gunakan database migrations.
- Hindari penyimpanan seluruh data dalam satu tabel JSONB.

## 3.5 ORM and Database Access

**Decision:** SQLAlchemy sebagai ORM utama dan Alembic untuk database migrations.

**Status:** APPROVED (2026-11-17, Project Owner)

Alasan:

- Memiliki integrasi yang baik dengan FastAPI.
- Mendukung relational mapping.
- Mendukung asynchronous database access.
- Alembic mempermudah versioning schema.
- Sudah dipakai dan teruji: vertical slice (market data, engines, scanner, research) dan portfolio Stage A berjalan di atas SQLAlchemy 2.0 + Alembic dengan 67 test lulus terhadap PostgreSQL nyata.

Implementation rules setelah disetujui:

- Gunakan SQLAlchemy models untuk pemetaan database.
- Gunakan Alembic untuk perubahan schema.
- Hindari perubahan database manual yang tidak tercatat dalam migration.
- Pisahkan repository dan database models dari business logic.
- Jangan membuat query database tersebar di seluruh engine.

## 3.6 Cache and Message Infrastructure

**Decision:** Redis sebagai teknologi opsional.

**Status:** DEFERRED

Redis dapat digunakan untuk:

- Latest market prices.
- Temporary market data state.
- Caching.
- WebSocket distribution.
- Job coordination.
- Temporary analytical results.

Redis tidak wajib digunakan pada MVP sebelum terdapat kebutuhan yang jelas.

Jangan menjadikan Redis sebagai pengganti PostgreSQL untuk penyimpanan permanen transaksi atau histori portofolio.

## 3.7 Containerization

**Decision:** Docker + Docker Compose.

**Status:** APPROVED

Alasan:

- Mempermudah development environment.
- Memisahkan environment frontend, backend, dan database.
- Mempermudah setup dan reproduksi environment.
- Menjadi dasar untuk deployment berikutnya.

# 4. Frontend Architecture Decisions

## 4.1 Feature-Oriented Architecture

**Decision:** Feature-oriented frontend structure.

**Status:** APPROVED

Frontend harus dikelompokkan berdasarkan fitur.

Contoh:

```text
frontend/src/
├── app/
├── components/
├── features/
│   ├── dashboard/
│   ├── portfolio/
│   ├── market/
│   ├── scanner/
│   ├── analytics/
│   └── research/
├── hooks/
├── services/
├── stores/
├── types/
├── utils/
└── config/
```

Tujuannya adalah menjaga modularitas dan mencegah frontend menjadi kumpulan komponen yang saling bergantung tanpa struktur.

## 4.2 Chart Library

**Decision:** TradingView Lightweight Charts.

**Status:** APPROVED

Alasan:

- Ringan.
- Mendukung candlestick charts.
- Mendukung line dan area charts.
- Mendukung real-time updates.
- Cocok untuk financial dashboard.

Important distinction:

Lightweight Charts merupakan library visualisasi, bukan penyedia data pasar.

Data harus diperoleh dari backend melalui API atau WebSocket.

Implementation rules:

- Chart component tidak boleh mengakses provider secara langsung.
- Historical data diperoleh melalui backend.
- Real-time updates diterima melalui backend WebSocket.
- Pisahkan chart rendering dari market data service.
- Gunakan dokumentasi dan lisensi resmi library.
- Sertakan attribution sesuai ketentuan lisensi.

## 4.3 Dashboard Design System

**Decision:** Institutional financial dashboard design direction.

**Status:** APPROVED

Karakteristik desain:

- Professional.
- Modern.
- Data-dense.
- Consistent.
- Desktop-first.
- Responsive.
- Minimal visual decoration.

Hindari:

- Generic AI-generated SaaS appearance.
- Excessive gradients.
- Unnecessary glassmorphism.
- Excessive rounded cards.
- Oversized typography.
- Decorative elements yang mengganggu pembacaan data.
- Fake real-time indicators.

Dashboard harus mengutamakan informasi, keterbacaan, dan efisiensi penggunaan ruang.

# 5. Backend Architecture Decisions

## 5.1 Modular Monolith

**Decision:** Modular Monolith.

**Status:** APPROVED

Alasan:

- Lebih sederhana untuk pengembangan awal.
- Tidak membutuhkan infrastruktur microservices.
- Memudahkan debugging.
- Memiliki batas domain yang jelas.
- Dapat dikembangkan secara bertahap.

Backend harus memiliki modul yang terpisah berdasarkan tanggung jawab.

Modul utama:

- Portfolio.
- Market Data.
- Technical Analysis.
- Market Scanner.
- Risk Analysis.
- Allocation.
- Correlation.
- Market Regime.
- AI Research.

Modular Monolith bukan berarti seluruh kode berada dalam satu modul. Setiap domain harus memiliki batas tanggung jawab dan dependency yang jelas.

## 5.2 API Architecture

**Decision:** REST API + WebSocket.

**Status:** APPROVED

REST digunakan untuk:

- Portfolio management.
- Transaction management.
- Historical market data.
- Analytics requests.
- Scanner configurations.
- Scanner results.
- Research reports.
- Application settings.

WebSocket digunakan untuk:

- Live market updates.
- Latest price updates.
- Live candle updates.
- Scanner notifications.
- Realtime dashboard events.

Jangan menggunakan WebSocket untuk seluruh jenis komunikasi apabila REST sudah mencukupi.

## 5.3 Domain and Application Separation

**Decision:** Separate domain logic from application orchestration.

**Status:** APPROVED

Aturan:

- Domain berisi business rules dan konsep utama.
- Application layer mengatur use cases.
- API layer menangani komunikasi.
- Data layer menangani external providers dan persistence.
- Engine layer menjalankan perhitungan analitis.

Business logic tidak boleh bergantung langsung pada HTTP request atau frontend components.

# 6. Market Data Decisions

## 6.1 Provider Adapter Pattern

**Decision:** Provider Adapter Architecture.

**Status:** APPROVED

Setiap provider harus diintegrasikan melalui adapter tersendiri.

Provider awal:

| Market | Provider | Intended Role |
|---|---|---|
| Crypto | Bybit | Market data REST and WebSocket |
| US Stocks | Finnhub | Market data integration |
| US Stocks | Alpaca | Market data integration |
| Indonesia Stocks | Yahoo Finance | Initial research and data integration |

Daftar tersebut merupakan target integrasi, bukan jaminan bahwa setiap provider menyediakan seluruh data yang dibutuhkan.

Implementasi wajib memverifikasi:

- API availability.
- Market coverage.
- Rate limits.
- Historical data availability.
- Streaming availability.
- Data freshness.
- Licensing and redistribution rights.

## 6.2 Provider Independence

**Decision:** Normalize data before it enters analytical engines.

**Status:** APPROVED

Engine tidak boleh bergantung pada format respons asli provider.

Alur:

```text
External Provider
       │
       ▼
Provider Adapter
       │
       ▼
Normalization
       │
       ▼
Validation
       │
       ▼
Internal Market Data Model
       │
       ▼
Storage / Distribution
       │
       ▼
Analytics Engines
```

Tujuannya adalah agar pergantian provider tidak membutuhkan perubahan besar pada seluruh engine.

## 6.3 Real-Time Data Architecture

**Decision:** Centralized market data connections.

**Status:** APPROVED

Backend bertanggung jawab atas koneksi provider dan distribusi data ke frontend.

Frontend tidak boleh membuat koneksi langsung ke setiap provider untuk setiap chart.

Aturan:

- Gunakan centralized provider connections.
- Gunakan shared subscriptions.
- Distribusikan update melalui backend WebSocket.
- Pisahkan historical REST requests dari streaming updates.
- Validasi timestamp dan kualitas data.
- Kelola reconnect dan subscription lifecycle.

## 6.4 Data Freshness

**Decision:** Explicit data freshness indicators.

**Status:** APPROVED

Sistem harus membedakan status:

- LIVE.
- DELAYED.
- STALE.
- HISTORICAL.
- UNAVAILABLE.
- UNKNOWN.

Jangan menampilkan data sebagai LIVE jika provider tidak menjamin data real-time.

Setiap data pasar harus memiliki informasi waktu sumber dan waktu penerimaan jika tersedia.

# 7. Quantitative Engine Decisions

## 7.1 Deterministic Calculation

**Decision:** Financial calculations must be deterministic.

**Status:** APPROVED

Perhitungan finansial dilakukan oleh backend quantitative engines.

Contoh:

- Portfolio return.
- Volatility.
- Drawdown.
- Sharpe ratio.
- RSI.
- MACD.
- Correlation.
- Asset allocation.

AI tidak boleh menggantikan perhitungan matematis tersebut.

## 7.2 Engine Independence

**Decision:** Independent analytical modules.

**Status:** APPROVED

Setiap engine harus memiliki:

- Defined inputs.
- Defined outputs.
- Validation.
- Error handling.
- Unit tests.
- Version information where relevant.

Engine tidak boleh mengakses implementasi internal engine lain secara sembarangan.

Komunikasi antarmodul harus menggunakan application contracts atau interface yang telah ditentukan.

## 7.3 Initial Engine Priority

**Decision:** Incremental engine implementation.

**Status:** APPROVED

Prioritas awal:

1. Portfolio Performance Engine.
2. Risk Analysis Engine.
3. Asset Allocation Engine.
4. Technical Analysis Engine.
5. Correlation Analysis Engine.
6. Market Regime Engine.
7. Market Scanner.
8. AI Research Engine.

Prioritas tersebut merupakan urutan pengembangan yang disepakati secara konseptual. Detail urutan MVP dapat disesuaikan melalui roadmap setelah dependensi teknis dievaluasi.

Engine lanjutan seperti Backtesting, Factor Analysis, Attribution, dan Stress Testing tidak perlu dibuat pada tahap awal.

## 7.4 Portfolio Cost Basis Methodology

**Decision:** WEIGHTED AVERAGE COST (moving average) sebagai cost basis methodology.

**Status:** APPROVED (2026-11-17, Project Owner)

Alasan:

- Konsisten dengan kolom `average_cost` / `cost_basis` pada `specifications/database/schema-spec.md` §5.4.
- Deterministik dan mudah diuji (replay transaksi menghasilkan state yang sama).
- FIFO ditunda dan tidak diimplementasikan pada tahap ini.

Aturan yang disetujui bersama metodologi:

- Seluruh aritmetika memakai `Decimal`, tanpa rounding di dalam engine; quantize ke NUMERIC(30,12) hanya saat penulisan ke DB.
- Fee BUY dikapitalisasi ke cost basis: TotalCost = qty×price + fee (portfolio-engine-spec §4.3).
- Fee SELL mengurangi proceeds: NetProceeds = qty×price − fee (portfolio-engine-spec §4.4).
- Average cost tidak berubah saat SELL; realized P&L = net proceeds − (avg_cost × qty sold).
- Realized P&L dan unrealized P&L dihitung dan dilaporkan terpisah (portfolio-engine-spec §9).

Implementasi: `backend/app/engines/portfolio/cost_basis.py`.

## 7.5 Portfolio Schema Deviations (Approved, Additive)

**Status:** APPROVED (2026-11-17, Project Owner) — perubahan aditif, tidak menghapus fungsionalitas.

1. `scanner_results` memiliki kolom tambahan di luar schema-spec §8.3: `timeframe`, `freshness_status`, `data_timestamp`.
   - Beda dari spec: spec mendefinisikan hasil scanner tanpa identitas waktu-data per baris.
   - Alasan: dashboard dan qualification membutuhkan freshness per result; tanpa kolom ini status data yang ditampilkan hanya akurat pada saat scan berjalan.
   - Dampak: additif; tidak mengubah tabel/kolom lain; konsisten dengan aturan freshness di `data/validation/freshness.py`.

2. `risk_results` dipakai dengan scope aset (`asset_id` + `risk_classification`) pada vertical slice, sedangkan schema-spec §7.3 mendefinisikan risk portfolio-scope.
   - Beda dari spec: spec mengaitkan risk_results ke portfolio; implementasi saat ini menghitung risk per aset.
   - Alasan: qualification per instrumen (gating scanner + AI research) membutuhkan risk level aset; portfolio-scope menunggu Phase 3/4.
   - Dampak: ketika portfolio risk diimplementasikan, harus diputuskan memakai kolom nullable tambahan atau tabel terpisah. Kolom `portfolio_id` pada spec §7.3 belum ada di tabel saat ini dan akan ditambahkan lewat migration saat dibutuhkan.

# 7.6 Portfolio API & Frontend Decisions (Stage B/C)

**Status:** APPROVED (2026-11-17, Project Owner) — seluruh item di bawah ini disetujui setelah review Stage B.

1. **Nama field currency portfolio: `base_currency` di API ↔ `reporting_currency` di DB.**
   - Alasan: api-spec §8.2 memakai `base_currency` sebagai kontrak publik; kolom DB mengikuti schema-spec §5.1 (`reporting_currency`). Mapping dilakukan di layer API, schema tidak berubah.

2. **Nama field fee: `fee` di API ↔ `fee_amount` di DB.**
   - Alasan: api-spec §9.2 memakai `fee`; kolom DB `fee_amount` (schema-spec §5.2). Mapping di layer API.

3. **Endpoint valuation baru `GET /api/v1/portfolios/{id}/valuation`.**
   - Alasan: api-spec §8–§10 tidak mendefinisikan endpoint valuation, padahal dashboard dan halaman portfolio membutuhkannya (dashboard-spec §6: nilai portfolio berasal dari Portfolio Engine). Bentuk response mengikuti portfolio-engine-spec §8 (status model COMPLETE/PARTIAL/STALE/UNAVAILABLE) + api-spec §5.3 (money as decimal string).

4. **DELETE portfolio yang memiliki transaksi → HTTP 409; arsip lewat `PATCH status=ARCHIVED`.**
   - Alasan: riwayat finansial tidak boleh hilang diam-diam (api-spec §8.4, schema-spec §14). Portfolio tanpa transaksi tetap bisa dihapus.

5. **Semantik null vs nol pada valuation: `invested_value` = `"0"` hanya bila tidak ada posisi sama sekali (nol sungguhan); `null` bila ada posisi tetapi harga tidak tersedia (PARTIAL/STALE). `total_value` dan `unrealized_pnl` hanya diisi saat COMPLETE.**
   - Alasan: api-spec §4.3 melarang nilai nol menggantikan data yang tidak tersedia; nol hanya dipakai ketika memang benar-benar nol. Perbedaan ini ditulis eksplisit di docstring `value_portfolio` dan harus dijaga oleh setiap konsumen API.

6. **Idempotency key yang sudah dipakai dengan payload berbeda → HTTP 409 `CONFLICT` (bukan 422).**
   - Alasan: api-spec §22 mewajibkan penanganan konflik key/payload; konflik adalah kesalahan klien pada resource yang sama (409 Conflict), bukan pelanggaran validasi bisnis (422). Replay dengan payload sama tetap 200 + `idempotent_replay: true`.

7. **Withdrawal melebihi saldo cash → 422 `BUSINESS_RULE_ERROR` (`INSUFFICIENT_CASH`).**
   - Alasan: aturan MVP — tidak ada overdraft. Ini aturan MVP, bukan aturan abadi; revisi menunggu keputusan credit/margin di Phase lanjutan.

# 7.7 Asset API & AssetPicker Decisions (Stage D)

**Status:** APPROVED (2026-11-17, Project Owner) — item 1–2 dikoreksi langsung oleh Project Owner dari draft implementasi.

1. **`exchange` pada response asset = `markets.code` via `assets.market_id`; `null` hanya bila `assets.market_id` memang null.**
   - Koreksi atas draft awal yang selalu mengirim `null`. Schema sudah memuat relasi `assets.market_id -> markets.id`, jadi kode market adalah sumber data yang sah untuk field exchange (api-spec §11.3).
   - Catatan semantik: `market` dan `exchange` saat ini mengirim nilai yang sama (`markets.code`) karena belum ada entitas venue terpisah di schema (schema-spec §4.2 hanya mendefinisikan markets). `data_providers` adalah penyedia data, bukan venue, jadi tidak dipakai sebagai exchange. Bila venue sebenarnya (BYBIT, IDX, NASDAQ) dibutuhkan sebagai field terpisah, itu berarti perubahan schema dan menunggu keputusan baru.

2. **Filter `exchange` pada `GET /assets` dan `GET /assets/search` = filter `markets.code`; nilai yang tidak cocok mengembalikan daftar kosong (HTTP 200), bukan error.**
   - Koreksi atas draft awal yang menolak filter dengan 422. Filter yang tidak dikenal diperlakukan sama seperti filter lain yang tidak match: hasil kosong.

3. **Asset identity tetap internal (`assets.symbol` + `assets.id`); provider symbol mapping (Bybit `BTCUSDT`, Yahoo `BTC-USD`) tetap internal di `provider_instruments` dan tidak pernah tampil di Asset API.** (schema-spec §4.1)

4. **`/assets/search` dideklarasikan sebelum `/assets/{asset_id}` supaya literal `search` tidak tertangkap sebagai id; dibuktikan dengan test `test_route_order_search_is_not_an_id`.**

5. **`AssetPicker` frontend mencari lewat `GET /assets/search` dengan debounce 250 ms, minimal 2 karakter, dan menampilkan simbol + nama + market/exchange + quote currency.** Pencarian gagal/kosong ditampilkan apa adanya (empty/error state), tanpa fallback data palsu.

# 8. Market Scanner Decisions

## 8.1 Independent Scanner Engine

**Decision:** Market Scanner is an independent backend engine.

**Status:** APPROVED

Market Scanner bukan sekadar halaman dashboard atau fitur tambahan Technical Analysis.

Scanner harus dapat memproses instrumen dari market universe yang didukung, bukan hanya aset yang dimiliki dalam portofolio.

## 8.2 Scanner Categories

Kategori awal:

- Technical.
- Momentum.
- Volume.
- Volatility.
- Fundamental.
- Market Trend.
- Anomaly.
- Correlation.

Setiap kategori dapat memiliki filter dan ranking rules tersendiri.

## 8.3 Scanner Processing

**Decision:** Scheduled and event-driven processing.

**Status:** APPROVED

Scanner dapat dijalankan berdasarkan:

- Candle close.
- Scheduled intervals.
- Relevant market events.

Tidak semua indikator membutuhkan perhitungan setiap detik.

Scanner harus menggunakan centralized market data infrastructure dan tidak membuat koneksi provider terpisah untuk setiap instrumen.

# 9. AI Research Decisions

## 9.1 AI as Research Assistant

**Decision:** AI supports research and interpretation.

**Status:** APPROVED

AI Research digunakan untuk:

- Menjelaskan hasil analisis.
- Merangkum informasi pasar.
- Membandingkan beberapa aset.
- Menyusun research reports.
- Menginterpretasikan hasil quantitative engines.

AI tidak boleh menjadi sumber kebenaran untuk harga pasar atau hasil perhitungan matematis.

## 9.2 Context-Based Analysis

**Decision:** AI receives structured analytical context.

**Status:** APPROVED

AI harus menerima konteks yang telah disiapkan oleh backend.

Contoh:

- Market data.
- Technical indicators.
- Portfolio metrics.
- Risk metrics.
- Fundamental information.
- Relevant research sources.

AI tidak boleh mengarang data yang tidak tersedia.

Jika data tidak lengkap, AI harus menjelaskan keterbatasan tersebut.

## 9.3 Model Provider Independence

**Decision:** AI provider abstraction.

**Status:** APPROVED

AI integration harus memiliki abstraction layer agar provider model dapat diganti tanpa perubahan besar pada research engine.

Nama model, provider, prompt version, dan sumber konteks harus dapat ditelusuri.

# 10. Development and Infrastructure Decisions

## 10.1 Monorepo

**Decision:** Monorepo.

**Status:** APPROVED

Frontend, backend, infrastructure, documentation, dan specifications berada dalam satu repository.

Alasan:

- Memudahkan pengelolaan proyek.
- Menjaga konsistensi dokumentasi.
- Memudahkan perubahan lintas modul.
- Cocok untuk pengembangan oleh tim kecil atau satu developer.

## 10.2 Testing Strategy

**Decision:** Multi-level testing.

**Status:** APPROVED

Jenis pengujian:

- Unit testing.
- Integration testing.
- API testing.
- Database testing.
- WebSocket testing.
- End-to-end testing.

Financial calculations harus memiliki test cases dengan expected outputs yang jelas.

## 10.3 Environment Configuration

**Decision:** Environment-based configuration.

**Status:** APPROVED

Gunakan environment variables untuk:

- Database connection.
- Provider API credentials.
- AI API credentials.
- Application environment.
- External service configuration.

File `.env.example` hanya berisi nama variabel dan contoh nilai non-rahasia.

Credential asli tidak boleh dimasukkan ke Git repository.

# 11. Decisions Deferred for Future Evaluation

Keputusan berikut belum perlu ditentukan pada tahap awal.

| Area | Future Evaluation |
|---|---|
| Time-series database | PostgreSQL vs TimescaleDB |
| Caching | Redis implementation |
| Background jobs | Task queue technology |
| Authentication | Single-user vs multi-user architecture |
| Deployment | VPS, cloud, or managed infrastructure |
| Monitoring | Metrics, logs, and alerting stack |
| Fundamental data | Provider and licensing |
| IDX data | Reliable market data provider |
| Corporate actions | Dividend, split, and adjustment handling |
| Benchmark data | Market index integration |
| Backtesting | Historical simulation architecture |
| Multi-currency accounting | Valuation and FX methodology |

Keputusan tersebut harus dibuat berdasarkan kebutuhan aktual, bukan sekadar menambahkan teknologi karena populer.

# 12. Architecture Change Management

Perubahan terhadap keputusan teknis harus melalui proses berikut:

1. Identifikasi masalah atau kebutuhan baru.
2. Jelaskan keputusan yang ingin diubah.
3. Evaluasi alternatif.
4. Jelaskan dampak terhadap arsitektur.
5. Jelaskan dampak terhadap database dan data compatibility.
6. Jelaskan dampak terhadap performa dan kompleksitas.
7. Ajukan rekomendasi.
8. Tunggu persetujuan pengguna.
9. Perbarui dokumen keputusan.
10. Implementasikan perubahan.

OpenCode boleh memberikan rekomendasi perubahan, tetapi tidak boleh secara sepihak mengganti keputusan utama yang telah disetujui.

Setiap keputusan yang berubah harus mencatat:

- Decision ID.
- Date.
- Previous decision.
- New decision.
- Reason.
- Alternatives considered.
- Consequences.

# 13. OpenCode Implementation Rules

OpenCode harus membaca dokumen ini sebelum melakukan implementasi.

Aturan utama:

- Jangan mengganti framework utama tanpa persetujuan.
- Jangan mengubah Modular Monolith menjadi Microservices tanpa persetujuan.
- Jangan mengganti PostgreSQL tanpa persetujuan.
- Jangan mengganti Lightweight Charts tanpa persetujuan.
- Jangan membuat provider integration yang melewati adapter architecture.
- Jangan menempatkan financial calculations di frontend.
- Jangan menjadikan AI sebagai pengganti quantitative engines.
- Jangan mengimplementasikan seluruh future engines sekaligus.
- Jangan menambahkan dependency besar tanpa alasan teknis.
- Jangan mengabaikan lisensi dan ketentuan provider.
- Jangan mengklaim data real-time tanpa bukti freshness.

Jika menemukan kebutuhan yang tidak dapat dipenuhi oleh keputusan saat ini, OpenCode harus menjelaskan masalah dan mengajukan alternatif sebelum mengubah arsitektur.

# 14. Related Documents

Dokumen ini berkaitan dengan:

- `AGENTS.md`
- `README.md`
- `docs/architecture/system-architecture.md`
- `docs/architecture/application-architecture.md`
- `docs/architecture/data-flow.md`
- `docs/architecture/engine-architecture.md`
- `docs/database/database-design.md`
- `specifications/project/project-overview.md`
- `specifications/project/development-roadmap.md`
- `specifications/database/schema-spec.md`
- `specifications/security/security-spec.md`

---

# Final Principle

Technical decisions harus didasarkan pada kebutuhan sistem, bukan tren teknologi.

PIMS harus dibangun dengan arsitektur yang sederhana tetapi memiliki fondasi yang kuat untuk dikembangkan.

Setiap teknologi harus memiliki fungsi yang jelas, setiap modul harus memiliki tanggung jawab yang terpisah, dan setiap perubahan arsitektur harus memiliki alasan teknis yang dapat dipertanggungjawabkan.