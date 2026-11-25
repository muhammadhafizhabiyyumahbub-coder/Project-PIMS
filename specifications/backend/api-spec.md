# API Specification
## Personal Investment Management System (PIMS)

**Document Version:** 1.0  
**Project Status:** Planning  
**Document Type:** Backend API Specification  
**Last Updated:** November 2026

---

# 1. Purpose

Dokumen ini mendefinisikan REST API contract untuk Personal Investment Management System (PIMS).

REST API menjadi jalur komunikasi utama antara frontend dan backend untuk pengambilan data, pengelolaan portofolio, transaksi, market data, analytics, Market Scanner, dan AI Research.

Tujuan dokumen ini:

- Mendefinisikan API architecture.
- Menentukan endpoint utama.
- Menentukan request dan response structure.
- Menetapkan format data.
- Menentukan validation rules.
- Mengatur pagination dan filtering.
- Menetapkan error handling.
- Mengatur API versioning.
- Menjaga konsistensi komunikasi frontend dan backend.

Dokumen ini menjadi acuan OpenCode dalam mengimplementasikan API PIMS.

# 2. API Architecture

PIMS menggunakan REST API berbasis HTTP dengan JSON sebagai format pertukaran data.

## 2.1 Base URL

Development:

```text
http://localhost:8000/api/v1
```

Production:

```text
https://api.example.com/api/v1
```

Production domain merupakan placeholder dan harus diganti ketika deployment ditentukan.

## 2.2 API Versioning

Semua endpoint awal menggunakan prefix:

`/api/v1`

Perubahan yang tidak kompatibel dengan kontrak versi sebelumnya harus menggunakan API version baru.

Perubahan yang kompatibel dapat dilakukan dalam versi yang sama.

## 2.3 HTTP Methods

| Method | Usage |
|---|---|
| GET | Retrieve resources |
| POST | Create resource or execute action |
| PUT | Replace resource |
| PATCH | Partially update resource |
| DELETE | Delete resource |

Gunakan HTTP methods sesuai tujuan operasi.

## 2.4 Content Type

Request dan response menggunakan:

`application/json`

Untuk request tanpa body, Content-Type tidak wajib dikirim.

# 3. API Design Principles

API harus mengikuti prinsip berikut:

- Consistent endpoint naming.
- Resource-oriented structure.
- Explicit request and response schemas.
- Predictable error handling.
- Strong input validation.
- Stable identifiers.
- Consistent timestamp formats.
- Decimal-safe financial values.
- Clear pagination behavior.
- Provider-independent data contracts.
- No direct database exposure.

API tidak boleh mengembalikan struktur internal database secara langsung tanpa response schema.

# 4. Response Structure

Response harus menggunakan format yang konsisten.

## 4.1 Successful Response

Contoh:

```json
{
  "data": {
    "id": "portfolio-uuid",
    "name": "Main Portfolio",
    "base_currency": "USD"
  },
  "meta": {
    "request_id": "request-uuid"
  }
}
```

## 4.2 Collection Response

```json
{
  "data": [
    {
      "id": "asset-uuid",
      "symbol": "BTCUSDT",
      "name": "Bitcoin"
    }
  ],
  "meta": {
    "request_id": "request-uuid",
    "pagination": {
      "limit": 20,
      "next_cursor": null,
      "has_more": false
    }
  }
}
```

## 4.3 Response Rules

- `data` berisi resource atau hasil operasi.
- `meta` berisi informasi tambahan.
- Collection response harus memiliki pagination metadata apabila endpoint mendukung pagination.
- Request ID harus dapat digunakan untuk menelusuri logs.
- Field yang tidak tersedia harus mengikuti kontrak nullability yang ditentukan.
- Jangan menggunakan nilai nol untuk menggantikan data yang tidak tersedia.

# 5. Data Format Standards

## 5.1 Identifier

Gunakan stable internal identifiers untuk resource.

Format UUID direkomendasikan untuk resource yang memerlukan identifier unik.

## 5.2 Timestamp

Gunakan ISO 8601 dengan timezone.

Contoh:

```text
2026-11-17T00:30:00Z
```

Backend harus menyimpan timestamp secara konsisten dan menghindari timestamp tanpa timezone.

## 5.3 Financial Values

Nominal finansial harus menggunakan decimal-safe representation.

Untuk JSON API, nilai uang dan angka presisi tinggi direkomendasikan dikirim sebagai string numerik.

Contoh:

```json
{
  "market_value": "12500.750000",
  "currency": "USD"
}
```

Frontend bertanggung jawab terhadap formatting tampilan, bukan mengubah nilai sumber.

## 5.4 Percentage

Persentase harus memiliki definisi yang konsisten.

Contoh:

```json
{
  "return_percentage": "8.2500"
}
```

Nilai di atas berarti 8.25%, bukan 0.0825%.

## 5.5 Enumerations

Gunakan enum values yang konsisten dan terdokumentasi.

Contoh:

- `CRYPTO`
- `US_STOCK`
- `INDONESIA_STOCK`
- `LIVE`
- `DELAYED`
- `STALE`

Frontend tidak boleh mengasumsikan enum yang belum didefinisikan.

# 6. API Endpoint Overview

Endpoint dikelompokkan berdasarkan domain.

| Domain | Base Path | Responsibility |
|---|---|---|
| Health | `/health` | Application status |
| Portfolios | `/portfolios` | Portfolio management |
| Transactions | `/transactions` | Transaction management |
| Holdings | `/holdings` | Portfolio positions |
| Assets | `/assets` | Instrument metadata |
| Markets | `/markets` | Market information |
| Market Data | `/market-data` | Quotes and candles |
| Analytics | `/analytics` | Quantitative results |
| Scanner | `/scanner` | Market screening |
| Watchlist | `/watchlists` | Instrument monitoring |
| Research | `/research` | AI research reports |
| Dashboard | `/dashboard` | Dashboard aggregation |

# 7. Health API

Digunakan untuk memeriksa kondisi backend.

## 7.1 Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Basic health status |
| GET | `/health/ready` | Application readiness |

## 7.2 Example Response

```json
{
  "data": {
    "status": "healthy",
    "version": "1.0.0"
  }
}
```

Health endpoint tidak boleh mengekspos credentials atau informasi internal yang sensitif.

# 8. Portfolio API

Mengelola portofolio pengguna.

## 8.1 Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/portfolios` | Retrieve portfolio list |
| POST | `/portfolios` | Create portfolio |
| GET | `/portfolios/{portfolio_id}` | Retrieve portfolio detail |
| PATCH | `/portfolios/{portfolio_id}` | Update portfolio |
| DELETE | `/portfolios/{portfolio_id}` | Delete portfolio |

## 8.2 Create Portfolio

Request:

```json
{
  "name": "Main Portfolio",
  "description": "Long-term portfolio",
  "base_currency": "USD"
}
```

Response:

```json
{
  "data": {
    "id": "portfolio-uuid",
    "name": "Main Portfolio",
    "description": "Long-term portfolio",
    "base_currency": "USD",
    "created_at": "2026-11-17T00:30:00Z"
  }
}
```

## 8.3 Portfolio Detail

Portfolio detail dapat mencakup:

- Portfolio metadata.
- Base currency.
- Creation timestamp.
- Portfolio status.

Holdings dan analytics dapat diambil melalui endpoint khusus.

## 8.4 Portfolio Constraints

- Portfolio harus memiliki stable ID.
- Base currency harus valid.
- Penghapusan portfolio harus mempertimbangkan transaction history.
- Data historis tidak boleh hilang secara tidak sengaja.
- Portfolio yang memiliki transaksi harus mengikuti kebijakan archive atau deletion yang ditetapkan domain.

## 8.5 Portfolio Valuation

Endpoint tambahan yang telah disetujui (APPROVED, lihat technical-decisions §7.6):

`GET /portfolios/{id}/valuation`

Bentuk response mengikuti portfolio-engine-spec §8 (status model) dan §5.3 (money as decimal string).

Semantik null vs nol (APPROVED, wajib dijaga semua konsumen API):

- `invested_value` = `"0"` hanya bila portfolio tidak memiliki posisi sama sekali — nol sungguhan.
- `invested_value` = `null` bila ada posisi tetapi harga tidak tersedia (PARTIAL/STALE).
- `total_value` dan `unrealized_pnl` hanya diisi saat status `COMPLETE`; selain itu `null`.
- `null` berarti "tidak tersedia", bukan nol. Klien tidak boleh menampilkan null sebagai 0.

# 9. Transaction API

Mengelola aktivitas finansial portofolio.

## 9.1 Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/transactions` | Retrieve transactions |
| POST | `/transactions` | Create transaction |
| GET | `/transactions/{transaction_id}` | Retrieve transaction detail |
| PATCH | `/transactions/{transaction_id}` | Update transaction |
| DELETE | `/transactions/{transaction_id}` | Delete transaction |

## 9.2 Create Transaction

Request konseptual:

```json
{
  "portfolio_id": "portfolio-uuid",
  "asset_id": "asset-uuid",
  "transaction_type": "BUY",
  "quantity": "0.25000000",
  "price": "95000.00",
  "fee": "2.50",
  "currency": "USDT",
  "executed_at": "2026-11-17T00:30:00Z",
  "notes": "Example transaction"
}
```

Response:

```json
{
  "data": {
    "id": "transaction-uuid",
    "portfolio_id": "portfolio-uuid",
    "asset_id": "asset-uuid",
    "transaction_type": "BUY",
    "quantity": "0.25000000",
    "price": "95000.00",
    "fee": "2.50",
    "currency": "USDT",
    "executed_at": "2026-11-17T00:30:00Z"
  }
}
```

## 9.3 Transaction Types

Jenis transaksi awal:

- `BUY`
- `SELL`
- `DEPOSIT`
- `WITHDRAWAL`
- `FEE`
- `DIVIDEND`

Setiap jenis transaksi harus memiliki validation rules sendiri.

## 9.4 Transaction Validation

Backend harus memvalidasi:

- Portfolio existence.
- Asset existence.
- Transaction type.
- Quantity.
- Price.
- Fee.
- Currency.
- Execution timestamp.
- Required fields.

Backend juga harus menangani validasi domain seperti posisi yang tidak mencukupi untuk transaksi SELL, sesuai accounting policy yang disetujui.

## 9.5 Transaction Integrity

Transaksi merupakan sumber kebenaran holdings.

Setiap operasi create, update, atau delete harus mempertahankan konsistensi antara:

- Transaction records.
- Cash ledger.
- Derived holdings.
- Related portfolio snapshots.

Operasi yang saling bergantung harus dijalankan dalam database transaction yang sesuai.

Perubahan transaksi tidak boleh menghasilkan duplikasi efek finansial.

# 10. Holdings API

Menyediakan informasi posisi aset dalam portofolio.

## 10.1 Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/portfolios/{portfolio_id}/holdings` | Portfolio holdings |
| GET | `/portfolios/{portfolio_id}/holdings/{asset_id}` | Holding detail |

## 10.2 Example Response

```json
{
  "data": [
    {
      "asset_id": "asset-uuid",
      "symbol": "BTCUSDT",
      "quantity": "0.25000000",
      "average_cost": "90000.00",
      "market_price": "95000.00",
      "market_value": "23750.00",
      "unrealized_pnl": "1250.00",
      "currency": "USDT",
      "valuation_timestamp": "2026-11-17T00:30:00Z"
    }
  ]
}
```

## 10.3 Holdings Rules

- Holdings berasal dari transaction processing.
- Market value menggunakan harga yang tersedia.
- Unrealized P&L mengikuti accounting methodology.
- Missing prices harus ditandai.
- Holdings tidak boleh dihitung ulang secara independen oleh frontend.

# 11. Asset API

Mengelola instrument metadata.

## 11.1 Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/assets` | Search asset universe |
| GET | `/assets/{asset_id}` | Retrieve asset detail |
| GET | `/assets/search` | Search instruments |

## 11.2 Search Parameters

- `query`
- `market`
- `exchange`
- `asset_type`
- `limit`
- `cursor`

## 11.3 Example Response

```json
{
  "data": [
    {
      "id": "asset-uuid",
      "symbol": "BTCUSDT",
      "name": "Bitcoin",
      "market": "CRYPTO",
      "exchange": "BYBIT",
      "quote_currency": "USDT"
    }
  ]
}
```

Asset identity internal harus dibedakan dari provider-specific symbol mapping.

# 12. Market API

Menyediakan informasi pasar dan instrumen.

## 12.1 Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/markets` | Supported markets |
| GET | `/markets/{market_id}` | Market detail |
| GET | `/markets/status` | Market session information |

## 12.2 Market Information

Informasi dapat mencakup:

- Market identifier.
- Market name.
- Supported exchanges.
- Supported instruments.
- Market session.
- Data availability.

Status market harus dibedakan dari status koneksi provider.

# 13. Market Data API

Menyediakan historical dan snapshot market data.

## 13.1 Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/market-data/quotes` | Latest available quotes |
| GET | `/market-data/candles` | Historical OHLCV |
| GET | `/market-data/instruments/{asset_id}/quote` | Instrument quote |
| GET | `/market-data/instruments/{asset_id}/candles` | Instrument historical candles |

## 13.2 Candle Query Parameters

- `asset_id`
- `timeframe`
- `start_time`
- `end_time`
- `limit`
- `cursor` jika pagination diterapkan.

## 13.3 Example Request

```text
GET /api/v1/market-data/instruments/asset-uuid/candles?timeframe=1h&limit=500
```

## 13.4 Example Response

```json
{
  "data": {
    "asset_id": "asset-uuid",
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "provider": "BYBIT",
    "currency": "USDT",
    "candles": [
      {
        "time": 1794873600,
        "open": "95000.00",
        "high": "95200.00",
        "low": "94800.00",
        "close": "95100.00",
        "volume": "125.50"
      }
    ],
    "freshness": "HISTORICAL"
  },
  "meta": {
    "request_id": "request-uuid"
  }
}
```

## 13.5 Quote Response

Quote dapat berisi:

- Asset ID.
- Symbol.
- Last price.
- Bid.
- Ask.
- Price change.
- Percentage change.
- Currency.
- Provider.
- Timestamp.
- Freshness.

Field bid dan ask hanya tersedia jika provider menyediakan data tersebut.

## 13.6 Market Data Rules

- Data harus menggunakan internal asset ID.
- Provider harus dapat diidentifikasi.
- Timestamp harus jelas.
- Currency harus eksplisit.
- Freshness harus disertakan.
- Missing values tidak boleh diganti dengan angka nol.
- Historical candles harus terurut berdasarkan waktu.
- Provider-specific payload tidak boleh diekspos langsung.

# 14. Dashboard API

Dashboard API menyediakan data agregat untuk halaman utama.

## 14.1 Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/dashboard/overview` | Main dashboard data |
| GET | `/dashboard/market-overview` | Market summary |
| GET | `/dashboard/activity` | Recent transactions |
| GET | `/dashboard/scanner-highlights` | Scanner highlights |
| GET | `/dashboard/research-highlights` | Recent research |

## 14.2 Overview Parameters

- `portfolio_id` (optional).
- `time_range` (optional).
- `base_currency` (optional only if supported by aggregation rules).

Jika `portfolio_id` tidak diberikan, endpoint dapat mengembalikan agregasi seluruh portofolio sesuai aturan backend.

## 14.3 Example Response

```json
{
  "data": {
    "portfolio": {
      "total_value": "25000.00",
      "currency": "USD",
      "total_return": "8.2500",
      "daily_pnl": "125.00"
    },
    "allocation": [],
    "holdings": [],
    "risk_summary": {},
    "market_overview": [],
    "updated_at": "2026-11-17T00:30:00Z"
  }
}
```

Response final harus disesuaikan dengan dashboard data model dan ketersediaan data.

Dashboard API tidak boleh menghitung ulang engine results dengan metodologi yang berbeda.

# 15. Analytics API

Menyediakan hasil quantitative analysis.

## 15.1 Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/analytics/performance` | Portfolio performance |
| GET | `/analytics/risk` | Portfolio risk |
| GET | `/analytics/allocation` | Asset allocation |
| GET | `/analytics/correlation` | Correlation analysis |
| GET | `/analytics/technical` | Technical analysis |
| GET | `/analytics/market-regime` | Market regime |

## 15.2 Common Parameters

- `portfolio_id`
- `asset_id`
- `start_time`
- `end_time`
- `benchmark_id`
- `timeframe`

Parameter yang digunakan bergantung pada jenis analisis.

## 15.3 Performance Response

Dapat mencakup:

- Total return.
- Daily return.
- CAGR.
- Historical portfolio values.
- Benchmark comparison.
- Calculation timestamp.

## 15.4 Risk Response

Dapat mencakup:

- Volatility.
- Maximum drawdown.
- Sharpe ratio.
- Sortino ratio.
- VaR.
- CVaR.
- Beta.
- Concentration.

Setiap metrik harus memiliki measurement period dan calculation status.

## 15.5 Allocation Response

Dapat mencakup:

- Asset class.
- Market.
- Sector.
- Instrument.
- Market value.
- Allocation percentage.

## 15.6 Correlation Response

Dapat mencakup:

- Asset identifiers.
- Correlation matrix.
- Measurement period.
- Observation count.
- Calculation status.

## 15.7 Technical Analysis Response

Dapat mencakup:

- Indicator name.
- Parameters.
- Timestamp series.
- Indicator values.
- Timeframe.
- Calculation status.

## 15.8 Analytics Rules

- Semua perhitungan utama berasal dari backend.
- Missing data harus ditandai.
- Observation count harus tersedia jika relevan.
- Calculation methodology harus konsisten.
- Results harus memiliki timestamp.
- Frontend tidak boleh menganggap nilai unavailable sebagai nol.

# 16. Market Scanner API

Menyediakan akses terhadap konfigurasi dan hasil Market Scanner.

## 16.1 Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/scanner/categories` | Scanner categories |
| GET | `/scanner/configurations` | Retrieve configurations |
| POST | `/scanner/configurations` | Create configuration |
| PATCH | `/scanner/configurations/{id}` | Update configuration |
| DELETE | `/scanner/configurations/{id}` | Delete configuration |
| POST | `/scanner/run` | Execute scanner |
| GET | `/scanner/results` | Retrieve results |
| GET | `/scanner/runs/{run_id}` | Retrieve run detail |

## 16.2 Scanner Categories

- TECHNICAL.
- MOMENTUM.
- VOLUME.
- VOLATILITY.
- FUNDAMENTAL.
- MARKET_TREND.
- ANOMALY.
- CORRELATION.

## 16.3 Scanner Request

Contoh konseptual:

```json
{
  "category": "MOMENTUM",
  "market": "CRYPTO",
  "filters": {},
  "sort_by": "momentum_score",
  "sort_order": "DESC"
}
```

## 16.4 Scanner Result

Dapat mencakup:

- Run ID.
- Asset ID.
- Symbol.
- Market.
- Category.
- Matched conditions.
- Ranking.
- Detection timestamp.
- Data freshness.

## 16.5 Scanner Rules

- Scanner memproses market universe yang didukung.
- Scanner tidak terbatas pada holdings.
- Filter harus divalidasi backend.
- Ranking harus dihitung backend.
- Run status harus dapat diperiksa.
- Scanner result harus memiliki referensi waktu dan data.
- Hasil scanner bukan jaminan pergerakan harga.

# 17. Watchlist API

Mengelola daftar instrumen yang ingin dipantau.

> **STATUS: DEFERRED (2026-11-25, keputusan owner via audit).**
> Kontrak endpoint di bawah tetap berlaku (tidak diubah), tapi **belum diimplement** pada fase
> hardening. Alasan: `schema-spec` tidak mendefinisikan tabel `watchlists`/`watchlist_items`,
> dan PIMS saat ini **single-user** (tak ada tabel `users`, `portfolios` tak punya `user_id`).
> Implementasi menunggu keputusan owner + desain skema (lihat `docs/decisions/technical-decisions.md`).
> Kriteria aktivasi: selesai hardening P2/P3, owner setujui skema dua-tabel, lalu migration + model + endpoint + test.

## 17.1 Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/watchlists` | Retrieve watchlists |
| POST | `/watchlists` | Create watchlist |
| GET | `/watchlists/{id}` | Retrieve watchlist detail |
| PATCH | `/watchlists/{id}` | Update watchlist |
| DELETE | `/watchlists/{id}` | Delete watchlist |
| POST | `/watchlists/{id}/items` | Add instrument |
| DELETE | `/watchlists/{id}/items/{asset_id}` | Remove instrument |

## 17.2 Watchlist Rules

- Instrumen harus memiliki valid asset ID.
- Duplicate items harus ditangani.
- Watchlist tidak boleh mengubah portfolio holdings.
- Latest prices dapat diambil dari shared market data infrastructure.

# 18. AI Research API

Menyediakan interface untuk AI Research.

## 18.1 Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/research` | Create research request |
| GET | `/research` | Retrieve research history |
| GET | `/research/{report_id}` | Retrieve research report |
| DELETE | `/research/{report_id}` | Delete research report |

## 18.2 Research Request

Contoh:

```json
{
  "research_type": "INSTRUMENT_ANALYSIS",
  "asset_id": "asset-uuid",
  "portfolio_id": null,
  "focus_areas": [
    "TECHNICAL",
    "RISK",
    "MARKET_CONTEXT"
  ]
}
```

## 18.3 Research Response

Jika proses berlangsung asynchronous, backend mengembalikan status request terlebih dahulu.

Contoh:

```json
{
  "data": {
    "id": "research-uuid",
    "status": "PENDING",
    "created_at": "2026-11-17T00:30:00Z"
  }
}
```

Frontend dapat mengambil status atau hasil melalui report endpoint.

## 18.4 Research Report

Dapat berisi:

- Research metadata.
- Research type.
- Subject.
- Data references.
- Sources.
- AI-generated interpretation.
- Generation timestamp.
- Status.

## 18.5 Research Rules

- AI provider credentials hanya berada di backend.
- Research harus menggunakan structured context.
- AI tidak boleh menggantikan deterministic calculations.
- Output harus dibedakan dari verified data.
- Research failure harus memiliki status yang jelas.

# 19. Pagination

Collection endpoints harus menggunakan pagination ketika jumlah data dapat berkembang besar.

## 19.1 Cursor Pagination

Cursor pagination direkomendasikan untuk dataset yang dapat terus berubah.

Parameter:

- `limit`
- `cursor`

Contoh:

```text
GET /api/v1/transactions?limit=20&cursor=opaque-cursor
```

Response:

```json
{
  "data": [],
  "meta": {
    "pagination": {
      "limit": 20,
      "next_cursor": "opaque-cursor",
      "has_more": true
    }
  }
}
```

Cursor harus diperlakukan sebagai opaque value oleh frontend.

## 19.2 Pagination Rules

- Tetapkan maximum page size.
- Gunakan deterministic ordering.
- Hindari duplicate records antarhalaman.
- Tangani invalid cursor.
- Jangan mengandalkan offset pagination untuk dataset yang berubah cepat tanpa mempertimbangkan konsistensi.

# 20. Filtering and Sorting

Endpoint collection dapat menyediakan filtering sesuai kebutuhan.

Parameter umum:

- `search`
- `market`
- `asset_type`
- `transaction_type`
- `start_time`
- `end_time`
- `sort_by`
- `sort_order`

Ketentuan:

- Setiap endpoint harus mendokumentasikan parameter yang didukung.
- Backend harus memvalidasi sort fields.
- Jangan memasukkan parameter langsung ke SQL query.
- Filter yang tidak didukung harus menghasilkan validation error.

# 21. Error Handling

Semua error harus menggunakan struktur yang konsisten.

## 21.1 Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": [
      {
        "field": "quantity",
        "message": "Quantity must be greater than zero."
      }
    ],
    "request_id": "request-uuid"
  }
}
```

## 21.2 Error Categories

| Error Code | HTTP Status | Description |
|---|---:|---|
| VALIDATION_ERROR | 422 | Invalid request |
| NOT_FOUND | 404 | Resource not found |
| CONFLICT | 409 | Resource conflict |
| BUSINESS_RULE_ERROR | 422 | Business rule violation |
| UNAUTHORIZED | 401 | Authentication required |
| FORBIDDEN | 403 | Access denied |
| RATE_LIMITED | 429 | Too many requests |
| PROVIDER_ERROR | 502 | External provider failure |
| SERVICE_UNAVAILABLE | 503 | Service unavailable |
| INTERNAL_ERROR | 500 | Internal application error |

Status code harus mencerminkan jenis kegagalan yang sebenarnya.

## 21.3 Error Rules

- Jangan mengembalikan raw stack traces.
- Jangan mengungkap credentials.
- Error details harus aman untuk frontend.
- Request ID harus tersedia untuk troubleshooting.
- Error provider harus dibedakan dari error business logic.

# 22. Idempotency and Financial Operations

Operasi finansial memerlukan perlindungan terhadap request duplikat.

Untuk operasi create transaction, backend harus mendukung idempotency mechanism sebelum operasi tersebut digunakan dalam workflow yang berisiko mengalami retry.

Contoh header:

```text
Idempotency-Key: unique-operation-key
```

Ketentuan:

- Key harus memiliki scope dan expiration policy yang jelas.
- Request duplikat dengan key yang sama tidak boleh membuat transaksi baru.
- Konflik antara key dan request payload harus ditangani.
- Idempotency record harus konsisten dengan hasil operasi finansial.
- Retry tidak boleh menghasilkan double booking pada ledger.

# 23. Rate Limiting

Rate limiting dapat diterapkan pada endpoint yang memerlukan pembatasan.

Kandidat:

- Research generation.
- Scanner execution.
- Instrument search.
- Historical market data requests.
- Resource-intensive analytics.

Ketentuan:

- Batas harus disesuaikan dengan penggunaan aplikasi.
- Berikan HTTP 429 jika limit terlampaui.
- Jangan menerapkan pembatasan sembarangan pada seluruh endpoint tanpa evaluasi.

# 24. Security Requirements

API harus mengikuti security specification.

Ketentuan:

- Validate all incoming requests.
- Do not expose provider credentials.
- Do not expose AI provider keys.
- Use CORS allowlist.
- Avoid sensitive information in error responses.
- Protect state-changing operations.
- Validate resource ownership jika authentication diterapkan.
- Do not trust client-side validation.
- Avoid unsafe query construction.

Authentication dan authorization policy akan ditetapkan secara terpisah sebelum implementasinya menjadi requirement final.

# 25. API Documentation

FastAPI OpenAPI documentation digunakan sebagai dokumentasi teknis API.

Development documentation dapat tersedia melalui:

- `/docs`
- `/redoc`
- `/openapi.json`

Dokumentasi production harus mengikuti security policy deployment.

Setiap endpoint harus memiliki:

- Summary.
- Description.
- Request schema.
- Response schema.
- Error responses.
- Query parameters.
- Required fields.
- Example payloads.

OpenCode harus memperbarui dokumentasi ketika kontrak API berubah.

# 26. Testing Requirements

API harus memiliki pengujian:

## 26.1 Endpoint Tests

- Correct HTTP methods.
- Correct status codes.
- Request validation.
- Response schema.
- Error response format.

## 26.2 Business Integration Tests

- Portfolio creation.
- Transaction creation.
- Holdings calculation.
- Portfolio analytics.
- Market data retrieval.
- Scanner execution.
- Research request.

## 26.3 Data Integrity Tests

- Invalid transaction handling.
- Duplicate request handling.
- Currency consistency.
- Missing market data.
- Invalid asset references.
- Pagination consistency.

## 26.4 Contract Tests

Frontend dan backend harus menggunakan kontrak API yang sama.

Perubahan schema harus dapat dideteksi melalui testing atau OpenAPI contract validation.

# 27. Implementation Priority

| Phase | API Domain | Priority |
|---|---|---|
| 1 | Health | Critical |
| 2 | Portfolio | High |
| 3 | Transactions | High |
| 4 | Holdings | High |
| 5 | Assets | High |
| 6 | Market Data | High |
| 7 | Dashboard | High |
| 8 | Analytics | High |
| 9 | Scanner | High |
| 10 | Watchlist | Medium |
| 11 | AI Research | Medium |

Endpoint harus dibuat ketika domain service dan kebutuhan konsumen tersedia.

Jangan membuat endpoint kosong hanya untuk memenuhi daftar dokumentasi.

# 28. Acceptance Criteria

API specification dinyatakan terpenuhi apabila:

- API menggunakan `/api/v1`.
- Response format konsisten.
- Request schemas memiliki validation.
- Portfolio endpoints berfungsi.
- Transaction endpoints menjaga integrity.
- Holdings dapat diakses.
- Asset search berfungsi.
- Historical market data dapat diakses.
- Quote data dapat diakses.
- Dashboard API menyediakan data agregat.
- Analytics endpoints dapat mengakses hasil engine.
- Scanner endpoints berfungsi.
- Watchlist endpoints berfungsi ketika modul diimplementasikan.
- Research endpoints dapat mengelola research requests.
- Pagination tersedia pada collection yang membutuhkannya.
- Error format konsisten.
- Financial operations memiliki idempotency protection.
- API documentation tersedia.
- Automated tests berjalan.

# 29. Related Documents

- `AGENTS.md`
- `specifications/backend/backend-spec.md`
- `specifications/backend/websocket-spec.md`
- `specifications/frontend/frontend-spec.md`
- `specifications/frontend/dashboard-spec.md`
- `specifications/frontend/chart-engine-spec.md`
- `specifications/data/market-data-spec.md`
- `specifications/data/provider-integration-spec.md`
- `specifications/data/normalization-spec.md`
- `specifications/engines/portfolio-engine-spec.md`
- `specifications/engines/risk-engine-spec.md`
- `specifications/engines/allocation-engine-spec.md`
- `specifications/engines/market-scanner-spec.md`
- `specifications/engines/ai-research-spec.md`
- `docs/database/database-design.md`
- `docs/architecture/data-flow.md`
- `docs/decisions/technical-decisions.md`

---

# Final Principle

REST API PIMS harus menjadi kontrak komunikasi yang stabil, konsisten, dan dapat diuji antara frontend dan backend.

Setiap endpoint harus memiliki tanggung jawab yang jelas, setiap response harus memiliki struktur yang dapat diprediksi, dan seluruh operasi finansial harus menjaga integritas data.

API harus berkembang mengikuti kebutuhan domain tanpa menciptakan ketergantungan yang tidak diperlukan antara frontend, backend, dan external providers.