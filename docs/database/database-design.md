# Database Design
## Personal Investment Management System (PIMS)

**Document Version:** 1.0  
**Status:** Architecture Specification  
**Document Type:** Database Architecture  
**Last Updated:** November 2026

---

# 1. Purpose

Dokumen ini menjelaskan rancangan database untuk Personal Investment Management System (PIMS).

Database dirancang untuk mendukung pengelolaan beberapa portofolio, penyimpanan data pasar, pencatatan transaksi, pengelolaan aset, serta penyimpanan hasil analisis kuantitatif.

Rancangan database harus mendukung:

- Multiple portfolios.
- Crypto, US stocks, dan Indonesian stocks.
- Historical dan real-time market data.
- Portfolio performance tracking.
- Risk dan allocation analysis.
- Technical analysis.
- Market scanner.
- AI research dan analytical reports.
- Data provenance dan auditability.
- Pengembangan fitur lanjutan tanpa perubahan arsitektur besar.

Database menjadi sumber penyimpanan utama bagi backend. Perhitungan finansial dan analisis dilakukan oleh backend engine, bukan oleh frontend.

# 2. Database Architecture Principles

## 2.1 PostgreSQL as Primary Database

PostgreSQL digunakan sebagai database utama.

Alasan pemilihan:

- Mendukung relational data.
- Mendukung transaksi database.
- Memiliki integritas data yang kuat.
- Mendukung indexing dan query kompleks.
- Cocok untuk data portofolio dan transaksi.
- Dapat dikembangkan dengan extension apabila diperlukan.

TimescaleDB tidak diwajibkan pada tahap awal. Penggunaannya dapat dipertimbangkan apabila volume time-series data sudah membutuhkan optimasi khusus.

## 2.2 Data Integrity

Data finansial harus memiliki konsistensi dan integritas yang baik.

Aturan utama:

- Gunakan primary key pada setiap tabel.
- Gunakan foreign key untuk relasi antartabel.
- Gunakan constraint untuk mencegah data yang tidak valid.
- Hindari duplikasi instrumen.
- Transaksi yang sudah tercatat tidak boleh diubah tanpa mekanisme audit.
- Perubahan data penting harus dapat ditelusuri.

## 2.3 Separation of Data

Database dibagi berdasarkan tanggung jawab datanya:

1. Core entities.
2. Portfolio management.
3. Market data.
4. Analytics.
5. Market scanner.
6. AI research.
7. System operations.

Pemisahan ini bertujuan agar setiap kelompok data memiliki tanggung jawab yang jelas.

## 2.4 Provider Independence

Data instrumen tidak boleh bergantung pada satu provider.

Contohnya, satu saham dapat memiliki simbol berbeda pada beberapa penyedia data. Karena itu, identitas aset harus dipisahkan dari simbol yang digunakan oleh provider.

## 2.5 Data Provenance

Setiap data pasar dan hasil analisis harus dapat ditelusuri asalnya.

Informasi yang perlu diperhatikan:

- Data provider.
- Timestamp sumber.
- Timestamp penerimaan.
- Data interval.
- Status validasi.
- Waktu pemrosesan.
- Versi algoritma jika berasal dari engine.

# 3. Database Logical Architecture

Database dibagi menjadi beberapa domain utama.

```text
PostgreSQL
│
├── Core Entities
│   ├── Assets
│   ├── Markets
│   ├── Providers
│   └── Provider Instruments
│
├── Portfolio Management
│   ├── Portfolios
│   ├── Transactions
│   ├── Cash Ledger
│   └── Portfolio Snapshots
│
├── Market Data
│   ├── Market Candles
│   ├── Market Quotes
│   ├── Market Trades
│   ├── FX Rates
│   └── Data Ingestion Logs
│
├── Analytics
│   ├── Analytics Runs
│   ├── Performance Results
│   ├── Risk Results
│   ├── Allocation Results
│   ├── Correlation Results
│   └── Technical Results
│
├── Market Scanner
│   ├── Scanner Configurations
│   ├── Scanner Runs
│   └── Scanner Results
│
├── AI Research
│   ├── Research Reports
│   └── Research Sources
│
└── System Operations
    ├── System Settings
    ├── Audit Logs
    └── Job Execution Logs
```

Struktur tersebut merupakan pemisahan secara logis. Implementasi fisik dapat menggunakan PostgreSQL schemas atau pengelompokan tabel berdasarkan konvensi penamaan. Penggunaan PostgreSQL schema terpisah bukan persyaratan awal.

# 4. Core Entities

Core entities menyimpan identitas dasar aset, pasar, dan penyedia data.

## 4.1 Assets

Tabel `assets` menyimpan identitas setiap instrumen yang dapat digunakan dalam sistem.

Contoh:

- Bitcoin.
- Ethereum.
- Apple.
- Microsoft.
- Saham perusahaan yang terdaftar di Bursa Efek Indonesia.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| name | VARCHAR | Nama aset |
| asset_type | VARCHAR | CRYPTO, STOCK, ETF, dan lainnya |
| base_currency | VARCHAR | Mata uang dasar instrumen |
| market_id | UUID | Referensi pasar |
| exchange | VARCHAR | Bursa atau exchange |
| country_code | VARCHAR | Negara pasar |
| is_active | BOOLEAN | Status instrumen |
| created_at | TIMESTAMP | Waktu pembuatan |
| updated_at | TIMESTAMP | Waktu perubahan |

**Catatan desain:**

`assets` menjadi identitas utama instrumen. Simbol provider tidak disimpan sebagai identitas tunggal aset.

## 4.2 Markets

Tabel `markets` menyimpan informasi pasar tempat instrumen diperdagangkan.

Contoh:

- Cryptocurrency Market.
- US Stock Market.
- Indonesian Stock Market.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| name | VARCHAR | Nama pasar |
| market_code | VARCHAR | Kode pasar |
| country_code | VARCHAR | Negara |
| timezone | VARCHAR | Zona waktu |
| trading_calendar | JSONB | Referensi kalender perdagangan |
| is_active | BOOLEAN | Status pasar |

## 4.3 Data Providers

Tabel `data_providers` menyimpan identitas penyedia data.

Contoh:

- Bybit.
- Finnhub.
- Alpaca.
- Yahoo Finance.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| name | VARCHAR | Nama provider |
| provider_type | VARCHAR | REST, WEBSOCKET, atau kombinasi |
| market_coverage | JSONB | Cakupan pasar |
| is_active | BOOLEAN | Status provider |
| created_at | TIMESTAMP | Waktu pembuatan |

API key dan credential tidak boleh disimpan sebagai data biasa dalam tabel ini. Credential harus dikelola melalui environment variables atau secret management yang sesuai.

## 4.4 Provider Instruments

Tabel `provider_instruments` menghubungkan identitas aset dengan simbol yang digunakan oleh provider.

Contoh:

Satu aset dapat memiliki beberapa identitas eksternal:

- BTCUSDT pada Bybit.
- AAPL pada Finnhub.
- AAPL pada Alpaca.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| asset_id | UUID | Referensi aset |
| provider_id | UUID | Referensi provider |
| provider_symbol | VARCHAR | Simbol dari provider |
| provider_market | VARCHAR | Bursa atau kategori pasar provider |
| is_active | BOOLEAN | Status mapping |
| created_at | TIMESTAMP | Waktu pembuatan |

**Constraint:**

Kombinasi provider, provider symbol, dan konteks pasar harus memiliki aturan uniqueness yang jelas agar mapping tidak ambigu.

# 5. Portfolio Management

Domain ini menyimpan informasi portofolio dan aktivitas finansial yang dicatat pengguna.

## 5.1 Portfolios

Tabel `portfolios` menyimpan informasi setiap portofolio.

Sistem harus mendukung beberapa portofolio yang terpisah.

Contoh:

- Long-Term Portfolio.
- Crypto Portfolio.
- Research Portfolio.
- US Stocks Portfolio.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| name | VARCHAR | Nama portofolio |
| description | TEXT | Deskripsi |
| base_currency | VARCHAR | Mata uang pelaporan |
| initial_capital | NUMERIC | Modal awal jika digunakan |
| status | VARCHAR | ACTIVE atau ARCHIVED |
| created_at | TIMESTAMP | Waktu pembuatan |
| updated_at | TIMESTAMP | Waktu perubahan |

Setiap portofolio harus memiliki identitas tersendiri. Data transaksi dan hasil analisis harus dapat difilter berdasarkan `portfolio_id`.

## 5.2 Transactions

Tabel `transactions` menyimpan aktivitas portofolio.

Jenis transaksi yang perlu didukung:

- BUY.
- SELL.
- DEPOSIT.
- WITHDRAWAL.
- DIVIDEND.
- FEE.
- TAX.
- ADJUSTMENT.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| portfolio_id | UUID | Referensi portofolio |
| asset_id | UUID | Referensi aset, nullable untuk transaksi kas |
| transaction_type | VARCHAR | Jenis transaksi |
| quantity | NUMERIC | Jumlah unit |
| unit_price | NUMERIC | Harga per unit |
| currency | VARCHAR | Mata uang transaksi |
| fee_amount | NUMERIC | Biaya transaksi |
| tax_amount | NUMERIC | Pajak |
| transaction_date | TIMESTAMP | Waktu transaksi |
| notes | TEXT | Catatan |
| created_at | TIMESTAMP | Waktu pencatatan |
| updated_at | TIMESTAMP | Waktu perubahan |

**Aturan penting:**

1. Transaksi menjadi sumber utama untuk merekonstruksi aktivitas portofolio.
2. Data transaksi harus dapat diaudit.
3. Jangan menghapus transaksi yang sudah digunakan dalam perhitungan historis tanpa mekanisme koreksi.
4. Koreksi transaksi sebaiknya menggunakan reversal atau adjustment yang dapat ditelusuri.
5. Validasi quantity, price, currency, dan jenis transaksi harus dilakukan backend.

Kolom tambahan dapat diperlukan untuk menyimpan external reference, status transaksi, serta informasi corporate action.

## 5.3 Cash Ledger

Tabel `cash_ledger` menyimpan perubahan saldo kas dalam setiap portofolio.

Contoh aktivitas:

- Deposit.
- Withdrawal.
- Pembelian aset.
- Penjualan aset.
- Dividend.
- Fee.
- Tax.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| portfolio_id | UUID | Referensi portofolio |
| transaction_id | UUID | Referensi transaksi |
| currency | VARCHAR | Mata uang |
| amount | NUMERIC | Perubahan saldo |
| entry_type | VARCHAR | Jenis perubahan |
| created_at | TIMESTAMP | Waktu pencatatan |

Ledger harus memiliki aturan debit dan kredit yang konsisten.

Saldo kas sebaiknya dapat direkonstruksi dari ledger, bukan hanya bergantung pada satu angka saldo yang dapat berubah tanpa jejak.

## 5.4 Holdings

Holdings menunjukkan jumlah aset yang dimiliki dalam suatu portofolio.

Ada dua pendekatan:

**A. Fully derived holdings**

Jumlah kepemilikan dihitung dari seluruh transaksi.

Kelebihan:
- Konsisten dengan histori transaksi.
- Tidak memiliki sumber data ganda.

Kekurangan:
- Query dapat menjadi berat ketika transaksi semakin banyak.

**B. Materialized holdings snapshot**

Sistem menyimpan hasil perhitungan kepemilikan dalam bentuk snapshot atau tabel hasil rekonsiliasi.

Kelebihan:
- Query dashboard lebih cepat.
- Memudahkan pengambilan data terkini.

Kekurangan:
- Membutuhkan mekanisme sinkronisasi dan rekonsiliasi.

**Rekomendasi arsitektur:**

Transaksi tetap menjadi sumber kebenaran utama. Holdings dapat disimpan sebagai hasil perhitungan atau snapshot yang dapat dibangun ulang dari transaksi.

## 5.5 Portfolio Snapshots

Tabel `portfolio_snapshots` menyimpan kondisi portofolio pada waktu tertentu.

Contoh:

- Total portfolio value.
- Total cash.
- Total asset value.
- Daily P&L.
- Unrealized P&L.
- Realized P&L.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| portfolio_id | UUID | Referensi portofolio |
| snapshot_time | TIMESTAMP | Waktu snapshot |
| total_value | NUMERIC | Total nilai |
| cash_value | NUMERIC | Nilai kas |
| asset_value | NUMERIC | Nilai aset |
| daily_pnl | NUMERIC | Perubahan nilai harian |
| unrealized_pnl | NUMERIC | P&L belum terealisasi |
| realized_pnl | NUMERIC | P&L terealisasi |
| currency | VARCHAR | Mata uang pelaporan |

Snapshot merupakan data turunan dan harus dapat ditelusuri ke data transaksi serta harga yang digunakan dalam valuasi.

# 6. Market Data

Market data merupakan salah satu domain dengan volume data paling besar.

Struktur harus mendukung berbagai instrumen, provider, dan timeframe.

## 6.1 Market Candles

Tabel `market_candles` menyimpan data OHLCV.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID / BIGINT | Primary key |
| asset_id | UUID | Referensi aset |
| provider_id | UUID | Referensi provider |
| timeframe | VARCHAR | Interval candle |
| candle_time | TIMESTAMP | Waktu awal candle |
| open | NUMERIC | Harga pembukaan |
| high | NUMERIC | Harga tertinggi |
| low | NUMERIC | Harga terendah |
| close | NUMERIC | Harga penutupan |
| volume | NUMERIC | Volume |
| currency | VARCHAR | Mata uang harga |
| received_at | TIMESTAMP | Waktu penerimaan |
| quality_status | VARCHAR | Status kualitas data |

Timeframe yang dapat didukung:

- 1m.
- 5m.
- 15m.
- 30m.
- 1h.
- 4h.
- 1d.
- 1w.
- 1M.

Daftar timeframe harus mengikuti kemampuan provider.

**Aturan uniqueness:**

Satu kombinasi aset, provider, timeframe, dan candle time harus memiliki identitas yang unik.

Data dari dua provider tidak boleh tercampur menjadi satu tanpa proses normalisasi dan pemilihan sumber yang eksplisit.

## 6.2 Market Quotes

Tabel `market_quotes` menyimpan data harga pasar terbaru.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID / BIGINT | Primary key |
| asset_id | UUID | Referensi aset |
| provider_id | UUID | Referensi provider |
| bid_price | NUMERIC | Harga bid |
| ask_price | NUMERIC | Harga ask |
| last_price | NUMERIC | Harga terakhir |
| quote_time | TIMESTAMP | Timestamp sumber |
| received_at | TIMESTAMP | Waktu diterima |

Karena volume quote dapat sangat tinggi, penyimpanan historis seluruh update tidak harus dilakukan pada MVP.

Untuk kebutuhan dashboard real-time, harga terbaru dapat disimpan sebagai state terkini di cache atau mekanisme penyimpanan yang sesuai.

## 6.3 Market Trades

Tabel `market_trades` bersifat opsional untuk tahap awal.

Tabel ini digunakan apabila sistem membutuhkan histori transaksi pasar individual.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID / BIGINT | Primary key |
| asset_id | UUID | Referensi aset |
| provider_id | UUID | Referensi provider |
| provider_trade_id | VARCHAR | ID transaksi dari provider |
| price | NUMERIC | Harga |
| quantity | NUMERIC | Jumlah |
| trade_time | TIMESTAMP | Waktu transaksi |
| received_at | TIMESTAMP | Waktu penerimaan |

Penyimpanan trade-level dapat menghasilkan volume data yang besar. Aktifkan hanya jika benar-benar diperlukan.

## 6.4 FX Rates

Tabel `fx_rates` menyimpan nilai tukar antar mata uang.

Contoh:

- USD/IDR.
- USD/EUR.
- USDT/USD.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID / BIGINT | Primary key |
| base_currency | VARCHAR | Mata uang dasar |
| quote_currency | VARCHAR | Mata uang pembanding |
| rate | NUMERIC | Nilai tukar |
| provider_id | UUID | Referensi provider |
| rate_time | TIMESTAMP | Waktu sumber |
| received_at | TIMESTAMP | Waktu penerimaan |

Nilai tukar harus memiliki timestamp dan sumber yang jelas agar perhitungan portofolio lintas mata uang dapat direproduksi.

## 6.5 Market Data Ingestion Logs

Tabel `market_data_ingestion_logs` menyimpan aktivitas pengambilan data.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| provider_id | UUID | Provider |
| data_type | VARCHAR | Jenis data |
| status | VARCHAR | SUCCESS, FAILED, PARTIAL |
| records_received | INTEGER | Jumlah data |
| started_at | TIMESTAMP | Waktu mulai |
| completed_at | TIMESTAMP | Waktu selesai |
| error_message | TEXT | Informasi error |

Tujuan tabel ini adalah mempermudah monitoring dan debugging proses ingestion.

# 7. Analytics Data

Analytics domain menyimpan hasil perhitungan engine.

Hasil analisis harus memiliki informasi waktu, parameter, serta versi algoritma.

## 7.1 Analytics Runs

Tabel `analytics_runs` menyimpan informasi setiap eksekusi engine.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| engine_name | VARCHAR | Nama engine |
| portfolio_id | UUID | Portofolio terkait, nullable |
| asset_id | UUID | Aset terkait, nullable |
| engine_version | VARCHAR | Versi algoritma |
| parameters | JSONB | Parameter perhitungan |
| input_timestamp | TIMESTAMP | Waktu input |
| started_at | TIMESTAMP | Waktu mulai |
| completed_at | TIMESTAMP | Waktu selesai |
| status | VARCHAR | Status eksekusi |

Tabel ini menjadi referensi untuk hasil perhitungan yang dihasilkan engine.

## 7.2 Performance Results

Menyimpan hasil Portfolio Performance Engine.

Contoh informasi:

- Total return.
- Daily return.
- CAGR.
- Realized P&L.
- Unrealized P&L.
- Benchmark comparison.

Data dapat disimpan dalam bentuk tabel terstruktur atau hasil agregasi sesuai kebutuhan query.

## 7.3 Risk Results

Menyimpan hasil Risk Analysis Engine.

Contoh:

- Volatility.
- Maximum drawdown.
- Sharpe ratio.
- Sortino ratio.
- Beta.
- VaR.
- CVaR.
- Concentration risk.

Setiap hasil harus memiliki periode perhitungan dan metode yang digunakan.

## 7.4 Allocation Results

Menyimpan distribusi portofolio berdasarkan:

- Asset class.
- Market.
- Sector.
- Individual asset.
- Currency.

Hasil allocation harus menyertakan timestamp valuasi dan total nilai yang menjadi dasar persentase.

## 7.5 Correlation Results

Menyimpan hasil analisis korelasi.

Informasi yang dibutuhkan:

- Asset pair.
- Correlation value.
- Analysis period.
- Return frequency.
- Calculation method.
- Calculation timestamp.

Untuk matriks korelasi, struktur penyimpanan harus mendukung pengambilan hasil berdasarkan satu analytical run.

## 7.6 Technical Results

Menyimpan hasil indikator teknikal apabila persistence dibutuhkan.

Contoh:

- RSI.
- MACD.
- SMA.
- EMA.
- Bollinger Bands.
- ATR.
- VWAP.

Tidak semua nilai indikator harus disimpan permanen. Perhitungan ulang dari data candle dapat dilakukan apabila lebih efisien.

Keputusan penyimpanan harus mempertimbangkan frekuensi query, volume data, dan biaya komputasi.

# 8. Market Scanner

Market Scanner membutuhkan penyimpanan konfigurasi dan hasil screening.

## 8.1 Scanner Configurations

Tabel ini menyimpan aturan scanner.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| name | VARCHAR | Nama konfigurasi |
| category | VARCHAR | Kategori scanner |
| filters | JSONB | Kriteria screening |
| ranking_config | JSONB | Pengaturan ranking |
| universe_config | JSONB | Cakupan instrumen |
| is_active | BOOLEAN | Status konfigurasi |
| created_at | TIMESTAMP | Waktu pembuatan |

## 8.2 Scanner Runs

Menyimpan setiap proses screening.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| configuration_id | UUID | Konfigurasi |
| started_at | TIMESTAMP | Waktu mulai |
| completed_at | TIMESTAMP | Waktu selesai |
| status | VARCHAR | Status eksekusi |
| scanned_count | INTEGER | Jumlah instrumen |
| eligible_count | INTEGER | Jumlah instrumen lolos |

## 8.3 Scanner Results

Menyimpan hasil screening per instrumen.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| scanner_run_id | UUID | Referensi scanner run |
| asset_id | UUID | Instrumen |
| score | NUMERIC | Nilai ranking |
| matched_conditions | JSONB | Kondisi terpenuhi |
| metrics | JSONB | Nilai metrik |
| rank | INTEGER | Peringkat |
| created_at | TIMESTAMP | Waktu hasil dibuat |

Hasil scanner harus dapat ditelusuri ke konfigurasi, data input, dan waktu pemrosesan.

# 9. AI Research

AI Research menyimpan laporan dan sumber informasi yang digunakan.

## 9.1 Research Reports

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| title | VARCHAR | Judul laporan |
| report_type | VARCHAR | Jenis laporan |
| asset_id | UUID | Aset terkait, nullable |
| portfolio_id | UUID | Portofolio terkait, nullable |
| model_provider | VARCHAR | Penyedia model |
| model_name | VARCHAR | Nama model |
| prompt_version | VARCHAR | Versi prompt |
| context_metadata | JSONB | Metadata konteks |
| report_content | TEXT / JSONB | Isi laporan |
| created_at | TIMESTAMP | Waktu pembuatan |

## 9.2 Research Sources

Menyimpan referensi sumber yang digunakan dalam laporan.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| report_id | UUID | Referensi laporan |
| source_type | VARCHAR | NEWS, MARKET_DATA, ANALYTICS |
| source_name | VARCHAR | Nama sumber |
| source_reference | TEXT | URL atau referensi |
| published_at | TIMESTAMP | Waktu publikasi |
| retrieved_at | TIMESTAMP | Waktu pengambilan |

AI Research harus menyimpan informasi sumber dan konteks analisis agar laporan dapat ditelusuri.

Laporan AI tidak boleh dianggap sebagai pengganti data transaksi, data harga, atau hasil perhitungan kuantitatif.

# 10. System Operations

## 10.1 Audit Logs

Menyimpan aktivitas penting yang memengaruhi data.

Contoh:

- Pembuatan portofolio.
- Pencatatan transaksi.
- Koreksi transaksi.
- Perubahan konfigurasi.
- Perubahan pengaturan sistem.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| entity_type | VARCHAR | Jenis entitas |
| entity_id | UUID | ID entitas |
| action | VARCHAR | Jenis aktivitas |
| old_values | JSONB | Data sebelum perubahan |
| new_values | JSONB | Data sesudah perubahan |
| created_at | TIMESTAMP | Waktu aktivitas |

Audit log tidak boleh menyimpan API key, password, token, atau credential sensitif.

## 10.2 Job Execution Logs

Digunakan untuk memonitor pekerjaan terjadwal.

Contoh:

- Market data ingestion.
- Scanner execution.
- Analytics calculation.
- Data cleanup.
- Snapshot generation.

Kolom konseptual:

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| job_name | VARCHAR | Nama job |
| job_type | VARCHAR | Jenis job |
| status | VARCHAR | Status |
| started_at | TIMESTAMP | Waktu mulai |
| completed_at | TIMESTAMP | Waktu selesai |
| error_message | TEXT | Informasi error |

# 11. Relationships

Relasi utama database:

```text
MARKETS
   │
   └── ASSETS
          │
          ├── PROVIDER_INSTRUMENTS
          │       │
          │       └── DATA_PROVIDERS
          │
          ├── MARKET_CANDLES
          ├── MARKET_QUOTES
          ├── MARKET_TRADES
          └── FX / MARKET ANALYTICS

PORTFOLIOS
   │
   ├── TRANSACTIONS
   │       │
   │       └── ASSETS
   │
   ├── CASH_LEDGER
   ├── PORTFOLIO_SNAPSHOTS
   └── ANALYTICS_RUNS

ANALYTICS_RUNS
   │
   ├── PERFORMANCE_RESULTS
   ├── RISK_RESULTS
   ├── ALLOCATION_RESULTS
   ├── CORRELATION_RESULTS
   └── TECHNICAL_RESULTS

SCANNER_CONFIGURATIONS
   │
   └── SCANNER_RUNS
          │
          └── SCANNER_RESULTS
                 │
                 └── ASSETS

RESEARCH_REPORTS
   │
   └── RESEARCH_SOURCES
```

Relasi ini merupakan logical relationship. Foreign key dan cardinality final harus ditentukan pada schema implementation specification.

# 12. Indexing Strategy

Indexing diperlukan untuk menjaga performa query.

Prioritas index:

| Table | Index |
|---|---|
| assets | asset_type, market_id, is_active |
| provider_instruments | provider_id, provider_symbol |
| transactions | portfolio_id, transaction_date |
| cash_ledger | portfolio_id, created_at |
| portfolio_snapshots | portfolio_id, snapshot_time |
| market_candles | asset_id, provider_id, timeframe, candle_time |
| market_quotes | asset_id, provider_id, quote_time |
| fx_rates | base_currency, quote_currency, rate_time |
| analytics_runs | portfolio_id, engine_name, started_at |
| scanner_runs | configuration_id, started_at |
| scanner_results | scanner_run_id, rank |
| research_reports | portfolio_id, asset_id, created_at |

Untuk tabel time-series, pertimbangkan composite indexes berdasarkan pola query yang benar-benar digunakan.

Index harus diuji dengan query plan. Jangan membuat index berlebihan karena dapat memperlambat operasi insert dan update.

# 13. Data Types and Precision

Data finansial harus menggunakan tipe numerik dengan presisi yang sesuai.

Rekomendasi:

- Gunakan `NUMERIC` atau `DECIMAL` untuk harga, jumlah aset, nilai uang, dan hasil perhitungan finansial yang membutuhkan presisi.
- Hindari penggunaan floating-point untuk pencatatan transaksi keuangan.
- Gunakan `TIMESTAMPTZ` untuk timestamp yang merepresentasikan waktu absolut.
- Gunakan UUID untuk identitas entitas utama.
- Gunakan JSONB untuk konfigurasi atau metadata yang fleksibel, bukan untuk menggantikan struktur relasional yang penting.

Precision dan scale final harus ditentukan berdasarkan karakteristik masing-masing aset dan provider. Jangan menggunakan satu skala desimal untuk seluruh instrumen.

# 14. Data Retention Strategy

Data yang disimpan harus memiliki kebijakan retensi.

| Data | Retention Consideration |
|---|---|
| Transactions | Permanent, subject to audit policy |
| Portfolio snapshots | Long-term |
| Daily candles | Long-term |
| Intraday candles | Configurable |
| Market quotes | Limited or latest-state only |
| Market trades | Optional and volume-dependent |
| Scanner results | Configurable |
| Analytics results | Long-term or versioned |
| AI research reports | Configurable |
| Ingestion logs | Configurable |
| Job logs | Configurable |

Kebijakan retensi harus mempertimbangkan kapasitas penyimpanan, kebutuhan analisis historis, serta lisensi provider.

Penghapusan data pasar tidak boleh menghapus histori transaksi atau informasi yang diperlukan untuk merekonstruksi valuasi portofolio.

# 15. Database Security

Aturan keamanan:

1. Credential provider tidak disimpan dalam tabel biasa.
2. Gunakan environment variables atau secret manager.
3. Backend menjadi satu-satunya komponen yang mengakses database secara langsung.
4. Frontend tidak boleh memiliki database credentials.
5. Gunakan parameterized queries atau ORM yang aman.
6. Terapkan least-privilege database permissions.
7. Validasi seluruh input sebelum disimpan.
8. Lakukan backup secara berkala.
9. Hindari menyimpan data sensitif yang tidak diperlukan.
10. Audit aktivitas penting.

Jika sistem berkembang menjadi multi-user, setiap tabel yang menyimpan data pengguna harus memiliki ownership model dan kontrol akses yang konsisten.

# 16. Database Performance Strategy

Optimasi dilakukan secara bertahap.

## Phase 1 — Initial

- PostgreSQL sebagai database utama.
- Relational schema yang terstruktur.
- Index berdasarkan query utama.
- Penyimpanan OHLCV.
- Portfolio transaction ledger.
- Portfolio snapshots.
- Tidak mewajibkan TimescaleDB.
- Tidak mewajibkan Redis.

## Phase 2 — Growth

- Evaluasi ukuran tabel market data.
- Optimasi composite indexes.
- Evaluasi partitioning berdasarkan waktu.
- Tambahkan caching jika query membutuhkan.
- Evaluasi materialized views untuk agregasi yang sering digunakan.

## Phase 3 — Advanced

- Evaluasi TimescaleDB.
- Evaluasi continuous aggregates.
- Optimasi penyimpanan time-series.
- Evaluasi archival storage.
- Optimasi query analytics berskala besar.

Teknologi tambahan hanya digunakan jika terdapat kebutuhan performa yang terukur.

# 17. Backup and Recovery

Database harus memiliki strategi pemulihan.

Persyaratan:

- Backup berkala.
- Uji restore secara berkala.
- Backup tidak disimpan hanya pada lokasi yang sama dengan database utama.
- Dokumentasikan prosedur recovery.
- Tentukan target Recovery Point Objective (RPO) dan Recovery Time Objective (RTO) sesuai kebutuhan penggunaan.

Untuk MVP, backup terjadwal dan prosedur restore yang telah diuji merupakan prioritas.

# 18. Data Consistency Rules

Aturan konsistensi utama:

1. Satu aset memiliki satu identitas internal.
2. Satu aset dapat memiliki beberapa provider instrument mappings.
3. Data candle harus memiliki identitas provider dan timeframe.
4. Timestamp sumber dan timestamp penerimaan harus dibedakan.
5. Transaksi harus terhubung dengan portofolio.
6. Transaksi aset harus terhubung dengan identitas aset yang valid.
7. Cash ledger harus konsisten dengan transaksi terkait.
8. Holdings harus dapat direkonstruksi dari transaksi.
9. Portfolio snapshots harus menyimpan timestamp valuasi.
10. Hasil analytics harus menyimpan versi algoritma dan metadata input.
11. Scanner results harus terhubung dengan scanner run.
12. AI reports harus menyimpan provenance sumber dan konteks yang relevan.

# 19. Important Design Decisions Requiring Approval

Beberapa keputusan belum boleh dianggap final hanya berdasarkan dokumen ini.

| Decision | Current Direction | Status |
|---|---|---|
| Primary database | PostgreSQL | Proposed |
| Time-series extension | TimescaleDB optional | Deferred |
| Cache | Redis optional | Deferred |
| Portfolio accounting | Transaction ledger as source of truth | Proposed |
| Holdings storage | Derived with optional snapshots | Proposed |
| Market quote persistence | Latest state or limited history | Proposed |
| Market candle retention | Long-term, subject to provider rights | Proposed |
| Multi-user support | Not required for initial personal-use design unless scope changes | Pending |
| Authentication | To be defined in security specification | Pending |
| Corporate actions | Future specification required | Pending |
| Tax and fee accounting | Future specification required | Pending |
| Benchmark data | Future specification required | Pending |

Keputusan yang memengaruhi struktur tabel, relasi, atau integritas data harus dikonfirmasi sebelum implementasi permanen.

# 20. Implementation Guidelines for OpenCode

OpenCode harus mengikuti dokumen ini ketika merancang dan mengimplementasikan database.

Urutan implementasi:

1. Review seluruh dokumen arsitektur.
2. Identifikasi kebutuhan database MVP.
3. Susun physical database schema.
4. Tampilkan ERD dan relasi antartabel.
5. Identifikasi constraint, index, dan tipe data.
6. Periksa konsistensi schema dengan domain architecture.
7. Laporkan keputusan yang belum ditentukan.
8. Tunggu persetujuan untuk perubahan arsitektur yang berdampak besar.
9. Implementasikan migration.
10. Buat model dan repository sesuai arsitektur backend.
11. Jalankan migration dan database tests.
12. Dokumentasikan hasil implementasi.

OpenCode tidak boleh langsung membuat seluruh tabel untuk semua fitur masa depan. Implementasikan hanya tabel yang diperlukan untuk tahap pengembangan yang sedang dikerjakan.

Jangan membuat tabel kosong hanya untuk mengikuti daftar konseptual.

# 21. Acceptance Criteria

Rancangan database dinyatakan memenuhi kebutuhan arsitektur apabila:

- Mendukung beberapa portofolio yang terpisah.
- Mendukung aset dari crypto, US stocks, dan IDX.
- Mendukung satu aset dengan beberapa provider mappings.
- Mendukung penyimpanan OHLCV historis.
- Mendukung pencatatan transaksi dan cash ledger.
- Holdings dapat direkonstruksi dari transaksi.
- Mendukung penyimpanan snapshot portofolio.
- Mendukung penyimpanan hasil analytics.
- Mendukung konfigurasi dan hasil Market Scanner.
- Mendukung AI research reports dan source references.
- Memiliki aturan integritas dan indexing.
- Memiliki strategi backup dan data retention.
- Tidak mengharuskan penggunaan teknologi tambahan tanpa kebutuhan yang jelas.

# 22. Related Documents

Dokumen ini harus dibaca bersama:

- `docs/architecture/system-architecture.md`
- `docs/architecture/application-architecture.md`
- `docs/architecture/data-flow.md`
- `docs/architecture/engine-architecture.md`
- `specifications/database/schema-spec.md`
- `specifications/backend/backend-spec.md`
- `specifications/data/market-data-spec.md`
- `specifications/security/security-spec.md`

---

**Final Principle**

Database PIMS harus dirancang berdasarkan integritas data, keterlacakan, konsistensi, dan kemampuan pengembangan jangka panjang.

Transaksi menjadi sumber utama histori portofolio, provider menjadi sumber data pasar, sedangkan analytics dan AI research menghasilkan informasi turunan.

Database tidak boleh menjadi tempat mencampur semua tanggung jawab aplikasi. Setiap domain harus memiliki struktur dan kepemilikan data yang jelas.