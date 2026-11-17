# Chart Engine Specification
## Personal Investment Management System (PIMS)

**Document Version:** 1.0  
**Project Status:** Planning  
**Document Type:** Frontend Technical Specification  
**Last Updated:** November 2026

---

# 1. Purpose

Dokumen ini mendefinisikan spesifikasi teknis Chart Engine pada Personal Investment Management System (PIMS).

Chart Engine bertanggung jawab untuk menampilkan informasi harga instrumen finansial dalam bentuk visualisasi interaktif.

Chart Engine menjadi salah satu komponen utama PIMS karena pengguna membutuhkan visualisasi market data untuk melakukan pemantauan dan analisis instrumen.

Tujuan dokumen ini:

- Menentukan library chart.
- Mendefinisikan arsitektur chart.
- Menentukan jenis visualisasi.
- Mengatur historical market data.
- Mengatur realtime market updates.
- Menentukan timeframe.
- Mengatur technical indicators.
- Mendefinisikan interaksi chart.
- Mengatur sinkronisasi dengan backend.
- Menentukan standar performa dan pengujian.

# 2. Technology

## 2.1 Primary Chart Library

Library utama:

**TradingView Lightweight Charts**

Repository: https://github.com/tradingview/lightweight-charts

Dokumentasi: https://tradingview.github.io/lightweight-charts/

License: Apache License 2.0.

Lightweight Charts digunakan karena menyediakan visualisasi finansial yang ringan dan mendukung kebutuhan chart interaktif.

## 2.2 Library Responsibilities

Lightweight Charts bertanggung jawab terhadap:

- Candlestick rendering.
- Line chart rendering.
- Area chart rendering.
- Histogram rendering.
- Time scale.
- Price scale.
- Crosshair.
- Zoom and scroll.
- Chart interaction.
- Custom series.
- Streaming visual updates.

Lightweight Charts bukan market data provider dan tidak menyediakan data harga secara otomatis.

Seluruh data harus disediakan oleh backend PIMS.

## 2.3 Additional Dependencies

Library tambahan dapat dipertimbangkan untuk:

- Technical indicator calculations.
- Date formatting.
- Chart interaction utilities.
- Drawing tools.
- Data processing.

Dependency tambahan tidak boleh dipilih tanpa mengevaluasi kebutuhan dan kompleksitasnya.

# 3. Architecture

Chart Engine menggunakan frontend-backend architecture.

## 3.1 High-Level Architecture

```text
External Market Providers
          │
          ▼
Backend Provider Adapters
          │
          ▼
Market Data Ingestion
          │
          ▼
Normalization / Validation
          │
          ▼
Aggregation / Storage
          │
          ▼
Market Data Service
          │
          ├──────── REST API
          │
          └──────── WebSocket
                       │
                       ▼
                Frontend Data Layer
                       │
                       ▼
                  Chart Engine
                       │
                       ▼
             Lightweight Charts
                       │
                       ▼
                  User Interface
```

## 3.2 Backend Responsibilities

Backend bertanggung jawab terhadap:

- Market data acquisition.
- Historical candle retrieval.
- Candle normalization.
- Candle aggregation.
- Data validation.
- Timestamp normalization.
- Provider management.
- WebSocket broadcasting.
- Data freshness status.
- Technical indicator calculations.
- Market data persistence.

## 3.3 Frontend Responsibilities

Frontend bertanggung jawab terhadap:

- Chart initialization.
- Historical data rendering.
- Realtime visual updates.
- Timeframe selection.
- Chart type selection.
- Indicator display.
- Chart interaction.
- Chart resizing.
- Loading and error handling.
- Subscription management.

Frontend tidak boleh menjadi sumber kebenaran untuk market data atau financial calculations.

# 4. Supported Markets

Chart Engine harus mendukung beberapa kategori pasar.

| Market | Initial Provider |
|---|---|
| Cryptocurrency | Bybit |
| US Stocks | Finnhub / Alpaca |
| Indonesia Stocks | Yahoo Finance initially |

Ketersediaan historical data, realtime feeds, dan hak penggunaan data harus diverifikasi pada masing-masing provider.

Tidak semua provider memiliki kemampuan dan tingkat keterlambatan data yang sama.

Chart Engine harus dapat bekerja dengan beberapa provider tanpa mengubah komponen chart utama.

# 5. Chart Types

Chart Engine mendukung beberapa jenis visualisasi.

## 5.1 Candlestick Chart

<text style="display:none"> </text>

Jenis utama untuk menampilkan pergerakan harga instrumen.

Data yang dibutuhkan:

- Open.
- High.
- Low.
- Close.
- Time.

Volume dapat ditampilkan pada panel terpisah.

## 5.2 Line Chart

Menampilkan perkembangan harga berdasarkan closing price atau nilai yang ditentukan.

Cocok untuk:

- Price trend.
- Portfolio performance.
- Benchmark comparison.

## 5.3 Area Chart

Menampilkan pergerakan harga menggunakan area yang terisi.

Dapat digunakan untuk visualisasi tren harga.

## 5.4 Bar Chart

Menampilkan informasi OHLC dalam bentuk bar.

## 5.5 Histogram

Digunakan untuk visualisasi:

- Trading volume.
- Indicator histogram.
- MACD histogram.

Jenis chart yang tersedia harus dapat dipilih melalui chart toolbar.

# 6. Chart Layout

Chart interface memiliki beberapa bagian utama.

```text
┌─────────────────────────────────────────────────────────────┐
│ Symbol Search       Timeframe       Chart Type       Settings │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    Main Price Chart                         │
│                                                             │
│                    Candlestick / Line                       │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                    Volume Panel                             │
├─────────────────────────────────────────────────────────────┤
│                    Indicator Panel                          │
├─────────────────────────────────────────────────────────────┤
│ Time Range       Data Status       Provider       Timestamp  │
└─────────────────────────────────────────────────────────────┘
```

Layout dapat dikembangkan dengan panel indikator tambahan.

Ketentuan:

- Main chart mendapatkan area terbesar.
- Volume panel memiliki skala tersendiri.
- Indicator panels tidak boleh mengganggu pembacaan harga.
- Toolbar harus mudah diakses.
- Status data harus terlihat jelas.

# 7. Chart Toolbar

Toolbar menyediakan kontrol utama chart.

Komponen:

| Component | Responsibility |
|---|---|
| Symbol Search | Select instrument |
| Timeframe Selector | Change interval |
| Chart Type Selector | Change visualization |
| Indicator Selector | Add or remove indicators |
| Chart Settings | Configure display |
| Reset Chart | Restore default viewport |
| Fullscreen | Expand chart |
| Refresh | Request historical data again |

Tidak semua fungsi harus tersedia pada MVP.

# 8. Instrument Selection

Pengguna dapat memilih instrumen dari berbagai market.

Contoh:

- BTCUSDT.
- ETHUSDT.
- AAPL.
- MSFT.
- BBCA.JK.

Setiap instrumen harus memiliki identitas internal yang konsisten.

Jangan hanya mengandalkan symbol string karena symbol yang sama dapat muncul pada provider atau market berbeda.

Instrument metadata minimal:

- Asset ID.
- Symbol.
- Display name.
- Market.
- Exchange.
- Currency.
- Provider mapping.

Ketika instrumen berubah:

1. Update selected instrument.
2. Unsubscribe dari stream sebelumnya jika tidak digunakan.
3. Request historical data instrumen baru.
4. Reset chart state yang tidak relevan.
5. Render historical data.
6. Subscribe ke stream instrumen baru.
7. Apply realtime updates.

# 9. Timeframe Management

Chart Engine harus mendukung berbagai timeframe.

## 9.1 Initial Timeframes

| Timeframe | Description |
|---|---|
| 1m | One minute |
| 5m | Five minutes |
| 15m | Fifteen minutes |
| 30m | Thirty minutes |
| 1h | One hour |
| 4h | Four hours |
| 1D | Daily |
| 1W | Weekly |
| 1M | Monthly |

Timeframe yang tersedia dapat berbeda berdasarkan kemampuan provider dan jenis instrumen.

## 9.2 Timeframe Switching

Ketika pengguna mengubah timeframe:

1. Request candle history yang sesuai.
2. Validate response.
3. Replace historical chart data.
4. Update volume data.
5. Update indicator data.
6. Adjust visible time range.
7. Update realtime subscription jika diperlukan.

## 9.3 Candle Aggregation

Jika provider tidak menyediakan timeframe tertentu, backend dapat melakukan candle aggregation dari timeframe yang lebih kecil apabila data sumber mencukupi.

Aturan aggregation:

- Open: first candle open.
- High: maximum high.
- Low: minimum low.
- Close: last candle close.
- Volume: sum of volume.

Aggregation harus mempertimbangkan market session dan timezone yang sesuai.

Frontend tidak boleh melakukan aggregation sebagai sumber data utama.

# 10. Historical Market Data

Historical candles dimuat melalui REST API.

## 10.1 Historical Data Requirements

Setiap candle harus memiliki:

- Timestamp.
- Open.
- High.
- Low.
- Close.
- Volume.

## 10.2 Data Loading

Alur:

```text
User selects instrument
          │
          ▼
Select timeframe
          │
          ▼
Request historical candles
          │
          ▼
Backend retrieves data
          │
          ▼
Frontend validates response
          │
          ▼
Chart receives historical data
          │
          ▼
Render chart
```

## 10.3 Initial Data Loading

Frontend harus memuat jumlah candle yang cukup untuk menampilkan chart dan indikator yang dipilih.

Jumlah candle ditentukan berdasarkan kebutuhan timeframe dan indikator.

## 10.4 Historical Pagination

Jika pengguna melakukan scroll ke periode yang lebih lama, frontend dapat meminta historical candles tambahan.

Ketentuan:

- Jangan meminta seluruh historical data sekaligus.
- Gunakan pagination berdasarkan timestamp.
- Hindari duplicate candles.
- Pastikan urutan data konsisten.
- Hindari mengganti seluruh dataset ketika hanya menambahkan historical range.

# 11. Realtime Market Data

Realtime updates menggunakan backend WebSocket.

## 11.1 Data Flow

```text
Market Provider WebSocket
          │
          ▼
Backend Ingestion
          │
          ▼
Normalize and Validate
          │
          ▼
Candle Update / Aggregation
          │
          ▼
Backend WebSocket Gateway
          │
          ▼
Frontend WebSocket Manager
          │
          ▼
Chart Data Adapter
          │
          ▼
Lightweight Charts
```

## 11.2 Realtime Update Method

Historical data dimuat menggunakan:

`series.setData(historicalData)`

Pembaruan candle terakhir menggunakan:

`series.update(lastBar)`

Ketentuan:

- Historical data harus diurutkan berdasarkan waktu.
- Timestamp harus sesuai format yang diterima Lightweight Charts.
- Update untuk candle yang sama harus memperbarui candle tersebut.
- Candle baru harus ditambahkan sesuai urutan waktu.
- Jangan mengirim data historis berulang sebagai update terbaru.
- Jangan mengasumsikan setiap provider mengirim event dalam format yang sama.

## 11.3 Centralized Subscription

Frontend harus menggunakan satu WebSocket manager terpusat.

Jangan membuat koneksi provider baru untuk setiap chart atau widget.

Subscription harus dikelola berdasarkan kebutuhan komponen yang aktif.

## 11.4 Connection Status

Status koneksi yang ditampilkan:

- CONNECTED.
- CONNECTING.
- RECONNECTING.
- DISCONNECTED.
- ERROR.

Status koneksi WebSocket harus dibedakan dari freshness market data.

Koneksi yang aktif tidak otomatis berarti data yang diterima masih live.

# 12. Data Freshness and Provider Information

Chart harus menampilkan informasi mengenai kualitas dan sumber data.

Informasi:

- Provider.
- Exchange or market.
- Last update timestamp.
- Data freshness.
- Market session.
- Delay status jika diketahui.

Status freshness mengikuti standar sistem:

| Status | Meaning |
|---|---|
| LIVE | Data memenuhi kriteria live |
| DELAYED | Data memiliki keterlambatan |
| STALE | Data tidak diperbarui sesuai batas |
| HISTORICAL | Data historis |
| UNAVAILABLE | Data tidak tersedia |
| UNKNOWN | Freshness tidak dapat dipastikan |

Jangan menampilkan label real-time hanya karena chart mengalami perubahan visual.

# 13. Volume Panel

Volume ditampilkan pada panel terpisah di bawah price chart.

Informasi:

- Volume per candle.
- Volume scale.
- Time alignment dengan price chart.

Ketentuan:

- Volume harus mengikuti candle yang sama.
- Volume harus menggunakan sumber data yang konsisten.
- Perubahan timeframe harus memperbarui volume.
- Jika volume tidak tersedia, tampilkan status unavailable.

# 14. Technical Indicators

Chart Engine harus mendukung visualisasi technical indicators.

Perhitungan utama indikator dilakukan oleh backend Technical Analysis Engine.

Frontend menerima hasil indikator dan menampilkannya.

## 14.1 Initial Indicators

| Indicator | Description | Display |
|---|---|---|
| SMA | Simple Moving Average | Overlay |
| EMA | Exponential Moving Average | Overlay |
| Bollinger Bands | Volatility bands | Overlay |
| VWAP | Volume Weighted Average Price | Overlay |
| RSI | Relative Strength Index | Separate panel |
| MACD | Moving Average Convergence Divergence | Separate panel |
| ATR | Average True Range | Separate panel |
| Stochastic | Stochastic Oscillator | Separate panel |

## 14.2 Indicator Configuration

Setiap indikator dapat memiliki:

- Indicator name.
- Parameters.
- Display settings.
- Visibility.
- Color configuration.
- Calculation status.

Parameter indikator harus divalidasi oleh backend.

## 14.3 Indicator Lifecycle

Ketika indikator ditambahkan:

1. Frontend mengirim permintaan indikator.
2. Backend menghitung indikator.
3. Backend mengembalikan time-series result.
4. Frontend memvalidasi data.
5. Chart menampilkan series yang sesuai.

Ketika timeframe berubah, hasil indikator harus mengikuti timeframe baru.

Ketika indikator dihapus, series visual terkait harus dilepas.

## 14.4 Indicator Calculation Boundary

Frontend tidak boleh menjadi sumber perhitungan indikator yang dianggap authoritative.

Jika perhitungan sementara dilakukan di frontend untuk alasan visual atau performa, hasil tersebut harus dibedakan dari hasil backend dan tidak boleh menggantikan hasil resmi.

# 15. Multiple Chart Panels

Chart Engine harus mendukung lebih dari satu panel visualisasi.

Contoh:

```text
┌─────────────────────────────────────┐
│ Price Chart                         │
│ Candlestick + SMA + EMA             │
├─────────────────────────────────────┤
│ Volume                              │
├─────────────────────────────────────┤
│ RSI                                 │
├─────────────────────────────────────┤
│ MACD                                │
└─────────────────────────────────────┘
```

Setiap panel harus memiliki:

- Independent price scale jika diperlukan.
- Shared time scale.
- Proper resizing.
- Clear labels.
- Consistent timestamp alignment.

MVP tidak harus menyediakan panel tanpa batas.

Jumlah panel dan indikator harus dibatasi secara wajar untuk menjaga performa.

# 16. Chart Interaction

Interaksi utama:

## 16.1 Crosshair

Pengguna dapat mengarahkan cursor untuk melihat nilai pada timestamp tertentu.

## 16.2 Zoom

Pengguna dapat memperbesar dan memperkecil rentang chart.

## 16.3 Scroll

Pengguna dapat melihat periode historis.

## 16.4 Time Range Navigation

Pengguna dapat memilih periode yang ingin ditampilkan.

## 16.5 Fullscreen

Chart dapat diperluas untuk analisis lebih detail.

## 16.6 Reset View

Mengembalikan chart ke tampilan default.

## 16.7 Responsive Resize

Chart harus menyesuaikan ukuran container secara otomatis.

# 17. Drawing Tools

Drawing tools dapat dikembangkan sebagai fitur lanjutan.

Contoh:

- Horizontal line.
- Trend line.
- Vertical line.
- Rectangle.
- Text annotation.

Ketentuan:

- Drawing state harus dipisahkan dari market data.
- Drawing tidak boleh mengubah historical candles.
- Drawing harus mengikuti koordinat waktu dan harga.
- Jika drawing persistence ditambahkan, penyimpanannya dilakukan melalui backend.
- Penggunaan custom series atau plugin harus dievaluasi terhadap maintainability.

Drawing tools bukan prioritas utama MVP.

# 18. Chart Data Contract

Frontend harus menerima data dengan struktur yang konsisten.

Kontrak konseptual historical candle:

```json
{
  "symbol": "BTCUSDT",
  "market": "CRYPTO",
  "provider": "BYBIT",
  "timeframe": "1m",
  "currency": "USDT",
  "candles": [
    {
      "time": 1794873600,
      "open": 95000.0,
      "high": 95100.0,
      "low": 94900.0,
      "close": 95050.0,
      "volume": 125.5
    }
  ],
  "freshness": "HISTORICAL"
}
```

Kontrak tersebut merupakan ilustrasi struktur, bukan API contract final.

Timestamp, numeric precision, dan field names harus diselaraskan dengan backend API specification.

## 18.1 Data Validation

Frontend harus memeriksa:

- Valid timestamp.
- Valid numeric values.
- Correct OHLC relationships.
- Ordered candles.
- Duplicate timestamps.
- Missing fields.
- Invalid volume values.

Data yang tidak valid tidak boleh langsung diteruskan ke chart.

# 19. Chart Component Architecture

Struktur komponen yang direkomendasikan:

```text
features/
└── charts/
    ├── components/
    │   ├── ChartContainer.tsx
    │   ├── ChartToolbar.tsx
    │   ├── PriceChart.tsx
    │   ├── VolumePanel.tsx
    │   ├── IndicatorPanel.tsx
    │   ├── TimeframeSelector.tsx
    │   ├── ChartTypeSelector.tsx
    │   └── ChartStatus.tsx
    │
    ├── hooks/
    │   ├── useChart.ts
    │   └── useChartData.ts
    │
    ├── services/
    │   └── chartDataAdapter.ts
    │
    ├── types/
    │   └── chart.types.ts
    │
    └── utils/
        ├── candleValidation.ts
        └── chartFormatting.ts
```

Struktur tersebut dapat berkembang sesuai kebutuhan implementasi.

## 19.1 Chart Container

Mengelola:

- Chart lifecycle.
- Container sizing.
- Child components.
- Chart configuration.

## 19.2 Chart Data Adapter

Mengelola:

- Backend response mapping.
- Data validation.
- Timestamp conversion.
- Series data preparation.

## 19.3 Chart Hooks

Mengelola lifecycle dan interaksi React dengan chart.

Pastikan chart instance tidak dibuat ulang pada setiap render.

# 20. Chart Lifecycle Management

Chart instance harus dikelola secara konsisten.

Ketika komponen dibuat:

- Initialize chart.
- Configure scales.
- Create required series.
- Load initial data.
- Attach interaction handlers.

Ketika data diperbarui:

- Update existing series.
- Avoid unnecessary reinitialization.
- Maintain viewport where appropriate.

Ketika komponen dihapus:

- Remove event listeners.
- Release chart resources.
- Unsubscribe relevant data streams.
- Remove chart instance.

Chart lifecycle yang tidak dikelola dengan benar dapat menyebabkan memory leaks dan performa buruk.

# 21. Performance Requirements

Chart Engine harus dirancang untuk menangani historical data dan streaming updates secara efisien.

Ketentuan:

- Gunakan incremental updates.
- Hindari mengganti seluruh historical dataset untuk setiap tick.
- Hindari membuat chart instance berulang.
- Batasi historical data sesuai kebutuhan.
- Gunakan centralized WebSocket subscriptions.
- Hindari excessive React re-renders.
- Gunakan efficient data transformation.
- Batasi jumlah indikator aktif sesuai kemampuan sistem.
- Gunakan responsive resizing.
- Hindari duplikasi data series.

Target performa akan ditentukan berdasarkan hasil pengujian pada lingkungan implementasi.

# 22. Error Handling

Chart harus dapat menangani:

- Historical data unavailable.
- Provider unavailable.
- WebSocket disconnected.
- Invalid candle data.
- Unsupported timeframe.
- Indicator calculation failure.
- Empty historical response.
- Request timeout.
- Data freshness expiration.

Error pada chart tidak boleh menyebabkan seluruh dashboard berhenti bekerja.

# 23. Testing Requirements

Pengujian minimal:

## 23.1 Component Tests

- Chart initialization.
- Chart type switching.
- Timeframe switching.
- Indicator display.
- Chart resizing.

## 23.2 Data Tests

- Historical candle mapping.
- Timestamp conversion.
- OHLC validation.
- Duplicate candle handling.
- Volume mapping.
- Indicator data mapping.

## 23.3 Realtime Tests

- Initial historical loading.
- Latest candle updates.
- New candle insertion.
- Reconnection behavior.
- Subscription cleanup.
- Out-of-order update handling.

## 23.4 Performance Tests

- Large historical datasets.
- Continuous market updates.
- Multiple active indicators.
- Multiple chart panels.
- Chart navigation responsiveness.

# 24. Implementation Roadmap

## Phase 1: Chart Foundation

- Install and configure Lightweight Charts.
- Create reusable chart container.
- Implement chart lifecycle.
- Implement responsive resizing.
- Create chart data adapter.

## Phase 2: Historical Chart

- Connect REST API.
- Load historical candles.
- Implement candlestick.
- Implement line and area chart.
- Add timeframe selector.

## Phase 3: Volume and Interaction

- Add volume panel.
- Add crosshair.
- Add zoom and scroll.
- Add reset view.
- Add fullscreen.

## Phase 4: Realtime Integration

- Connect centralized WebSocket manager.
- Subscribe to selected instrument.
- Process candle updates.
- Handle reconnection.
- Display freshness and connection status.

## Phase 5: Technical Indicators

- Connect Technical Analysis Engine.
- Add SMA and EMA.
- Add Bollinger Bands.
- Add RSI.
- Add MACD.
- Add additional indicators incrementally.

## Phase 6: Advanced Chart Features

- Multiple indicator panels.
- Advanced chart configuration.
- Drawing tools.
- Additional annotations.

Advanced features harus dikerjakan setelah fondasi historical dan realtime chart stabil.

# 25. Acceptance Criteria

Chart Engine dinyatakan memenuhi spesifikasi apabila:

- Lightweight Charts berhasil diintegrasikan.
- Historical candles dapat dimuat dari backend.
- Candlestick chart dapat ditampilkan.
- Line dan area chart dapat digunakan.
- Timeframe selector berfungsi.
- Volume panel dapat ditampilkan.
- WebSocket updates dapat memperbarui chart.
- Realtime subscriptions dikelola secara terpusat.
- Data freshness dapat ditampilkan.
- Provider information tersedia.
- Indicator data dapat divisualisasikan.
- Chart dapat melakukan zoom dan scroll.
- Chart dapat menyesuaikan ukuran container.
- Error handling tersedia.
- Chart tidak membuat koneksi berlebihan.
- Tidak terjadi unnecessary chart reinitialization.
- Tidak ada mock data yang ditampilkan seolah data pasar aktual.

# 26. Licensing and Attribution

TradingView Lightweight Charts menggunakan Apache License 2.0.

OpenCode harus:

- Mempertahankan copyright notices yang diwajibkan.
- Menyertakan lisensi sesuai ketentuan distribusi.
- Mengikuti persyaratan attribution yang berlaku.
- Memeriksa versi dan ketentuan lisensi yang digunakan.
- Tidak menganggap penggunaan Lightweight Charts memberikan akses ke market data TradingView.

Hak penggunaan chart library dan hak penggunaan market data merupakan dua hal yang berbeda.

# 27. Related Documents

- `AGENTS.md`
- `specifications/frontend/frontend-spec.md`
- `specifications/frontend/dashboard-spec.md`
- `specifications/backend/backend-spec.md`
- `specifications/backend/api-spec.md`
- `specifications/backend/websocket-spec.md`
- `specifications/data/market-data-spec.md`
- `specifications/data/provider-integration-spec.md`
- `specifications/data/normalization-spec.md`
- `specifications/engines/technical-analysis-spec.md`
- `docs/architecture/data-flow.md`
- `docs/architecture/engine-architecture.md`
- `docs/decisions/technical-decisions.md`

---

# Final Principle

Chart Engine PIMS harus menjadi lapisan visualisasi market data yang akurat, responsif, dan konsisten.

Historical data, realtime updates, serta technical indicators harus memiliki sumber yang jelas dan terintegrasi dengan backend.

Prioritas pengembangan adalah membangun historical chart dan realtime chart yang stabil sebelum menambahkan fitur visualisasi lanjutan.