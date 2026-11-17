# Dashboard Specification
## Personal Investment Management System (PIMS)

**Document Version:** 1.0  
**Project Status:** Planning  
**Document Type:** Frontend Feature Specification  
**Last Updated:** November 2026

---

# 1. Purpose

Dokumen ini mendefinisikan spesifikasi dashboard utama Personal Investment Management System (PIMS).

Dashboard merupakan halaman utama yang memberikan gambaran menyeluruh mengenai kondisi portofolio, performa investasi, kondisi pasar, dan informasi analitis.

Tujuan utama dashboard adalah menyajikan informasi finansial yang relevan dalam satu interface tanpa mengharuskan pengguna membuka setiap modul secara terpisah.

Dokumen ini menjadi acuan OpenCode dalam mengimplementasikan dashboard berdasarkan frontend architecture dan design reference yang telah ditentukan.

# 2. Dashboard Objectives

Dashboard harus memenuhi beberapa tujuan:

1. Menampilkan ringkasan kondisi seluruh portofolio.
2. Menampilkan perkembangan nilai portofolio.
3. Menyajikan informasi keuntungan dan kerugian.
4. Memvisualisasikan alokasi aset.
5. Menampilkan kondisi pasar secara umum.
6. Menyediakan akses cepat ke market instruments.
7. Menampilkan informasi risiko.
8. Menampilkan hasil Market Scanner.
9. Menampilkan aktivitas transaksi terbaru.
10. Menyediakan akses menuju AI Research.

Dashboard harus mengutamakan informasi yang membantu pengguna memahami kondisi finansial, bukan sekadar menampilkan banyak angka.

# 3. Design Direction

Dashboard menggunakan pendekatan Modern Financial Dashboard dengan referensi visual institutional investment platforms dan professional trading terminals.

## 3.1 Design Characteristics

Karakteristik visual:

- Professional.
- Minimalist.
- Information-dense.
- Data-oriented.
- Clean typography.
- Consistent spacing.
- Restrained color palette.
- Clear visual hierarchy.

## 3.2 Design Principles

**Information Hierarchy**

Informasi paling penting harus mudah ditemukan tanpa melakukan banyak navigasi.

**Data Clarity**

Angka, persentase, grafik, dan status harus memiliki label yang jelas.

**Functional Density**

Dashboard boleh menampilkan banyak informasi selama tetap mudah dibaca.

**Consistency**

Semua widget harus mengikuti design system yang sama.

**Minimal Decoration**

Hindari gradient berlebihan, efek glassmorphism yang tidak diperlukan, dekorasi berlebihan, dan elemen visual yang tidak memberikan fungsi.

# 4. Dashboard Layout

Dashboard menggunakan responsive grid layout.

Struktur konseptual:

```text
┌──────────────────────────────────────────────────────────────┐
│ Sidebar │ Top Navigation                                      │
│         ├────────────────────────────────────────────────────┤
│         │ Dashboard Title / Portfolio Selector               │
│         ├────────────────────────────────────────────────────┤
│         │ Portfolio Value │ Total Return │ Daily P&L          │
│         ├───────────────────────────────────┬──────────────────┤
│         │                                   │                  │
│         │ Portfolio Performance Chart       │ Asset Allocation │
│         │                                   │                  │
│         ├───────────────────────────────────┴──────────────────┤
│         │ Market Overview                                      │
│         ├───────────────────────────────────┬──────────────────┤
│         │                                   │                  │
│         │ Holdings Overview                 │ Risk Overview    │
│         │                                   │                  │
│         ├───────────────────────────────────┴──────────────────┤
│         │ Market Scanner Highlights                             │
│         ├───────────────────────────────────┬──────────────────┤
│         │                                   │                  │
│         │ Recent Transactions               │ AI Research      │
│         │                                   │ Highlights       │
│         └───────────────────────────────────┴──────────────────┘
└──────────────────────────────────────────────────────────────┘
```

Diagram tersebut merupakan susunan konseptual. Ukuran, rasio kolom, dan urutan akhir dapat disesuaikan dengan design reference selama hierarki informasi tetap terjaga.

# 5. Dashboard Header

Header dashboard menampilkan informasi kontekstual dan kontrol utama.

## 5.1 Dashboard Title

Menampilkan:

- Page title.
- Short contextual description.
- Last updated information jika relevan.

## 5.2 Portfolio Selector

Pengguna dapat memilih portofolio yang ingin dianalisis.

Pilihan:

- All Portfolios.
- Individual Portfolio.

Ketika satu portofolio dipilih, widget yang mendukung konteks portofolio harus menampilkan data portofolio tersebut.

Ketika All Portfolios dipilih, dashboard harus menggunakan agregasi yang valid.

Ketentuan:

- Jangan menjumlahkan nilai portofolio dalam mata uang berbeda tanpa konversi.
- Currency conversion harus menggunakan FX data yang tersedia.
- Tampilkan base currency yang digunakan.
- Jika data konversi tidak tersedia, tampilkan nilai terpisah atau status unavailable.

## 5.3 Time Range Selector

Digunakan untuk mengubah periode analisis pada widget yang mendukung historical data.

Pilihan awal:

- 1D.
- 1W.
- 1M.
- 3M.
- 6M.
- 1Y.
- ALL.

Periode yang dipilih harus diterapkan secara konsisten pada widget yang memang menggunakan time range tersebut.

# 6. Portfolio Summary

Portfolio Summary merupakan bagian paling penting pada dashboard.

Widget ini menampilkan ringkasan kondisi portofolio.

## 6.1 Portfolio Value

Menampilkan total nilai pasar portofolio.

Informasi:

- Current portfolio value.
- Base currency.
- Valuation timestamp.
- Data availability status.

Nilai harus berasal dari backend Portfolio Engine.

## 6.2 Total Return

Menampilkan performa portofolio dalam periode yang dipilih.

Informasi:

- Absolute return.
- Percentage return.
- Selected period.
- Benchmark comparison jika tersedia.

Metode perhitungan return harus ditentukan backend dan tidak boleh dibuat ulang oleh frontend.

## 6.3 Daily P&L

Menampilkan perubahan nilai portofolio untuk periode harian.

Informasi:

- Daily profit or loss.
- Daily percentage change.
- Reference timestamp.

## 6.4 Additional Metrics

Metrik tambahan yang dapat ditampilkan:

- Invested capital.
- Cash balance.
- Unrealized P&L.
- Realized P&L.

Ketersediaan metrik bergantung pada data yang tersedia.

## 6.5 Summary Card Behavior

Ketentuan:

- Semua angka harus menggunakan formatting konsisten.
- Positive dan negative values harus dapat dibedakan.
- Data yang belum tersedia tidak boleh ditampilkan sebagai nol.
- Perubahan nilai harus memiliki konteks periode.
- Tooltip dapat digunakan untuk menjelaskan definisi metrik.

# 7. Portfolio Performance Chart

Widget ini menampilkan perkembangan nilai portofolio dari waktu ke waktu.

## 7.1 Chart Type

Pilihan visualisasi:

- Area chart.
- Line chart.

Candlestick chart tidak digunakan sebagai representasi utama nilai portofolio karena nilai portofolio bukan market OHLC data.

## 7.2 Display Information

Chart menampilkan:

- Portfolio value history.
- Selected time range.
- Current value.
- Change percentage.
- Optional benchmark comparison.

## 7.3 Interactions

Pengguna dapat:

- Mengubah time range.
- Mengarahkan cursor untuk melihat nilai historis.
- Melakukan zoom jika didukung.
- Mengaktifkan atau menonaktifkan benchmark series.

## 7.4 Data Requirements

Historical portfolio valuation berasal dari backend.

Frontend hanya melakukan rendering dan interaksi visual.

Jika historical snapshots belum tersedia, dashboard harus menampilkan status data yang sesuai dan tidak membuat historical values palsu.

# 8. Asset Allocation Widget

Widget ini menunjukkan distribusi aset dalam portofolio.

## 8.1 Allocation Categories

Kategori awal:

- Crypto.
- US Stocks.
- Indonesia Stocks.
- Cash.
- Other Assets.

Kategori tambahan dapat digunakan apabila sistem mendukungnya.

## 8.2 Visualization

Visualisasi yang dapat digunakan:

- Donut chart.
- Horizontal allocation bars.

## 8.3 Display Information

Setiap kategori menampilkan:

- Asset category.
- Market value.
- Allocation percentage.
- Base currency.

## 8.4 Interaction

Pengguna dapat memilih kategori untuk membuka halaman Portfolio atau Analytics dengan filter yang sesuai.

## 8.5 Data Rules

- Persentase harus dihitung backend.
- Total allocation harus memiliki definisi yang jelas.
- Cash harus diperlakukan sebagai bagian dari allocation apabila termasuk dalam metode yang digunakan.
- Missing valuations harus ditandai.
- Jangan menganggap nilai aset yang tidak tersedia sebagai nol.

# 9. Market Overview

Market Overview menampilkan kondisi umum pasar yang didukung PIMS.

## 9.1 Supported Markets

Pasar awal:

- Cryptocurrency.
- US Stocks.
- Indonesia Stocks.

## 9.2 Display Information

Informasi yang dapat ditampilkan:

- Selected market indices.
- Major cryptocurrency prices.
- Market percentage changes.
- Market session status.
- Market data freshness.

Contoh kategori instrumen:

| Market | Example Instruments |
|---|---|
| Crypto | BTC, ETH |
| US Stocks | S&P 500, Nasdaq Composite |
| Indonesia Stocks | IHSG |

Daftar instrumen merupakan konfigurasi awal dan bukan batas permanen.

## 9.3 Market Status

Status pasar dapat berupa:

- OPEN.
- CLOSED.
- PRE-MARKET.
- POST-MARKET.
- CONTINUOUS.
- UNKNOWN.

Status harus berasal dari informasi market session yang tersedia.

## 9.4 Data Freshness

Setiap informasi pasar harus memiliki status freshness yang sesuai.

Status yang digunakan:

- LIVE.
- DELAYED.
- STALE.
- HISTORICAL.
- UNAVAILABLE.
- UNKNOWN.

Jangan menampilkan indikator LIVE apabila provider tidak memberikan data live yang terverifikasi.

# 10. Holdings Overview

Widget ini menampilkan aset yang dimiliki pengguna.

## 10.1 Display Information

Kolom yang direkomendasikan:

| Field | Description |
|---|---|
| Asset | Instrument name |
| Symbol | Instrument symbol |
| Quantity | Current holding quantity |
| Price | Latest available price |
| Market Value | Current market valuation |
| Allocation | Portfolio percentage |
| P&L | Unrealized profit or loss |

## 10.2 Sorting

Pengguna dapat melakukan sorting berdasarkan:

- Market value.
- Allocation.
- P&L.
- Asset name.

## 10.3 Navigation

Pemilihan instrumen dapat membuka instrument detail page.

## 10.4 Data Rules

Holdings merupakan hasil perhitungan backend berdasarkan transaksi dan data pendukung.

Frontend tidak boleh menjadi sumber kebenaran untuk quantity, cost basis, atau valuation.

# 11. Risk Overview

Risk Overview memberikan gambaran awal mengenai risiko portofolio.

## 11.1 Initial Metrics

Metrik yang dapat ditampilkan:

- Portfolio volatility.
- Maximum drawdown.
- Sharpe ratio.
- Asset concentration.

Metrik tambahan:

- Sortino ratio.
- Value at Risk.
- Beta.

Metrik tambahan ditampilkan apabila metode dan data yang diperlukan telah tersedia.

## 11.2 Display Rules

Setiap metrik harus memiliki:

- Metric name.
- Calculated value.
- Measurement period.
- Calculation status.
- Tooltip explanation.

## 11.3 Risk Interpretation

Jika terdapat interpretasi risiko, frontend harus menampilkan penjelasan berdasarkan hasil backend.

Jangan menetapkan label risiko secara sembarangan hanya berdasarkan angka tanpa metodologi yang disetujui.

# 12. Market Scanner Highlights

Widget ini menampilkan hasil Market Scanner yang dianggap relevan.

## 12.1 Display Information

Informasi:

- Instrument.
- Market.
- Scanner category.
- Signal or condition.
- Ranking.
- Detection timestamp.

## 12.2 Scanner Categories

Kategori awal:

- Technical.
- Momentum.
- Volume.
- Volatility.
- Fundamental.
- Market Trend.
- Anomaly.
- Correlation.

## 12.3 Interaction

Pengguna dapat:

- Membuka instrument detail.
- Melihat detail scanner result.
- Membuka halaman Market Scanner.
- Mengubah kategori melalui halaman scanner.

## 12.4 Data Rules

- Hasil harus berasal dari backend Scanner Engine.
- Ranking harus menggunakan hasil perhitungan backend.
- Tampilkan timestamp hasil pemindaian.
- Hasil lama harus ditandai.
- Scanner result bukan jaminan pergerakan harga berikutnya.

# 13. Recent Transactions

Widget ini menampilkan aktivitas transaksi terbaru.

## 13.1 Display Information

Kolom:

- Date.
- Portfolio.
- Asset.
- Transaction type.
- Quantity.
- Price.
- Total value.

## 13.2 Transaction Types

Jenis transaksi dapat meliputi:

- BUY.
- SELL.
- DEPOSIT.
- WITHDRAWAL.
- FEE.
- DIVIDEND.

Jenis transaksi final mengikuti domain dan database specification.

## 13.3 Interaction

Pengguna dapat:

- Membuka transaction detail.
- Membuka portfolio terkait.
- Membuka transaction history lengkap.

Dashboard hanya menampilkan ringkasan aktivitas terbaru.

# 14. AI Research Highlights

Widget ini memberikan akses cepat ke hasil AI Research.

## 14.1 Display Information

Informasi:

- Research title.
- Related instrument or portfolio.
- Research category.
- Creation timestamp.
- Research status.

## 14.2 Research Categories

Contoh:

- Instrument Research.
- Portfolio Review.
- Market Summary.
- Risk Interpretation.
- Macro Research.

## 14.3 Interaction

Pengguna dapat membuka laporan lengkap pada halaman AI Research.

## 14.4 Data Rules

- AI Research harus menggunakan data dan konteks yang tersedia.
- Tampilkan sumber referensi apabila tersedia.
- Bedakan data aktual dari interpretasi AI.
- Jangan menampilkan AI-generated content sebagai fakta terverifikasi.
- Dashboard tidak boleh membuat kesimpulan finansial otomatis tanpa dasar data yang jelas.

# 15. Watchlist Widget

Watchlist dapat digunakan untuk memantau instrumen yang belum dimiliki.

## 15.1 Display Information

- Instrument.
- Symbol.
- Latest price.
- Price change.
- Percentage change.
- Data freshness.

## 15.2 Interaction

Pengguna dapat:

- Membuka instrument detail.
- Menghapus instrumen dari watchlist.
- Menambahkan instrumen baru melalui market search.

Watchlist merupakan fitur pemantauan, bukan bagian otomatis dari portfolio holdings.

# 16. Dashboard Data Architecture

Dashboard mengambil data dari backend melalui REST API dan WebSocket.

## 16.1 Data Sources

| Widget | Backend Source |
|---|---|
| Portfolio Summary | Portfolio Application Service |
| Performance Chart | Portfolio Performance Engine |
| Asset Allocation | Allocation Engine |
| Market Overview | Market Data Service |
| Holdings | Portfolio Domain |
| Risk Overview | Risk Engine |
| Scanner Highlights | Scanner Engine |
| Recent Transactions | Transaction Service |
| AI Research | AI Research Service |
| Watchlist | Watchlist Service |

## 16.2 REST API

REST digunakan untuk:

- Initial dashboard data.
- Historical portfolio performance.
- Holdings.
- Allocation.
- Risk metrics.
- Transactions.
- Scanner results.
- Research reports.
- Watchlist.

## 16.3 WebSocket

WebSocket digunakan untuk data yang membutuhkan pembaruan berkelanjutan.

Contoh:

- Latest market prices.
- Active instrument updates.
- Relevant scanner notifications.
- Connection status.

Tidak semua widget perlu menggunakan WebSocket.

Portfolio analytics tidak perlu dihitung ulang setiap kali harga bergerak apabila interval perhitungannya belum memerlukan pembaruan tersebut.

## 16.4 Data Refresh Strategy

| Data | Update Strategy |
|---|---|
| Portfolio Summary | Initial load and controlled refresh |
| Performance History | REST request |
| Market Prices | WebSocket when available |
| Asset Allocation | Backend refresh or invalidation |
| Holdings | Backend refresh after relevant changes |
| Risk Metrics | Scheduled or request-driven |
| Scanner Results | Scanner execution schedule |
| Transactions | Refresh after transaction changes |
| AI Research | Request-driven |
| Watchlist Prices | Shared market data stream |

# 17. Multi-Portfolio Aggregation

Dashboard harus mendukung beberapa portofolio terpisah.

## 17.1 All Portfolios View

Menampilkan agregasi portofolio yang dipilih atau seluruh portofolio.

Agregasi harus mempertimbangkan:

- Base currency.
- Valuation timestamps.
- FX conversion.
- Missing asset prices.
- Portfolio inclusion status.

## 17.2 Individual Portfolio View

Menampilkan data hanya dari satu portofolio.

Widget yang mendukung portfolio context harus memperbarui datanya sesuai portfolio selection.

## 17.3 Aggregation Constraints

- Jangan menjumlahkan nominal dengan mata uang berbeda secara langsung.
- Jangan menggabungkan historical returns tanpa metodologi agregasi yang benar.
- Jangan menghitung portfolio return hanya dari rata-rata persentase return setiap portofolio.
- Tampilkan status apabila data tidak cukup untuk melakukan agregasi.
- Gunakan backend sebagai sumber perhitungan agregasi.

# 18. Loading and Error Handling

Setiap widget harus memiliki state sendiri.

## 18.1 Loading

Widget menampilkan loading indicator ketika data sedang diminta.

## 18.2 Error

Jika request gagal, widget menampilkan error state tanpa membuat seluruh dashboard tidak dapat digunakan.

## 18.3 Empty

Jika belum terdapat data, widget menampilkan empty state yang sesuai.

## 18.4 Stale Data

Jika data tidak diperbarui sesuai batas freshness yang ditentukan backend, tampilkan status stale.

## 18.5 Partial Availability

Dashboard harus tetap menampilkan widget yang datanya tersedia meskipun sebagian layanan mengalami kegagalan.

# 19. Dashboard Performance

Ketentuan performa:

- Widget harus memiliki data dependencies yang jelas.
- Hindari request berulang untuk data yang sama.
- Gunakan shared data subscriptions.
- Jangan membuat WebSocket connection untuk setiap widget.
- Batasi jumlah historical points sesuai kebutuhan visualisasi.
- Gunakan pagination untuk tabel besar.
- Hindari rendering ulang seluruh dashboard ketika satu nilai berubah.
- Gunakan lazy loading untuk bagian yang tidak diperlukan saat initial render.

# 20. Responsive Behavior

## 20.1 Desktop

Desktop merupakan prioritas utama.

- Gunakan multi-column grid.
- Portfolio Summary berada di bagian atas.
- Performance Chart mendapatkan ruang visual yang cukup.
- Tabel dapat menampilkan kolom penting secara lengkap.

## 20.2 Tablet

- Grid dapat berubah menjadi dua kolom.
- Beberapa widget dapat dipindahkan ke baris berikutnya.
- Navigation dapat menggunakan compact layout.

## 20.3 Mobile

- Widget ditampilkan secara vertikal.
- Metric cards menggunakan grid yang lebih kecil.
- Tabel menggunakan horizontal scrolling atau alternatif yang sesuai.
- Chart harus tetap dapat dibaca.
- Informasi penting tidak boleh terpotong.

# 21. Dashboard State Management

Dashboard memiliki beberapa state utama:

| State | Description |
|---|---|
| Selected Portfolio | Portfolio context |
| Selected Time Range | Historical period |
| Dashboard Data | Loaded widget data |
| Market Stream | Realtime market updates |
| Widget Loading | Individual loading status |
| Widget Errors | Individual failure status |
| Watchlist | Selected instruments |

Ketentuan:

- Portfolio selection harus konsisten antar-widget.
- Time range tidak boleh mengubah widget yang tidak bergantung pada historical period.
- Realtime data harus menggunakan shared subscription.
- Widget harus dapat memperbarui state secara independen.
- Hindari menyimpan data yang sama pada beberapa state stores tanpa kebutuhan.

# 22. Dashboard Testing Requirements

Pengujian minimal:

## 22.1 Functional Testing

- Portfolio selector.
- Time range selector.
- Widget navigation.
- Holdings sorting.
- Watchlist interaction.
- Transaction navigation.
- Scanner navigation.

## 22.2 Data Testing

- Correct currency formatting.
- Correct percentage formatting.
- Missing data handling.
- Stale data indication.
- Portfolio aggregation.
- Historical data rendering.

## 22.3 Realtime Testing

- WebSocket connection.
- Market price update.
- Reconnection behavior.
- Subscription cleanup.
- Duplicate event handling.

## 22.4 Visual Testing

- Desktop layout.
- Tablet layout.
- Mobile layout.
- Typography consistency.
- Widget alignment.
- Loading and error states.

# 23. Acceptance Criteria

Dashboard dinyatakan memenuhi spesifikasi apabila:

- Dashboard dapat diakses melalui route utama.
- Portfolio selector berfungsi.
- Portfolio Summary menampilkan data backend.
- Performance Chart dapat menampilkan historical data.
- Asset Allocation menampilkan distribusi aset.
- Market Overview menampilkan status dan freshness.
- Holdings Overview menampilkan data portofolio.
- Risk Overview menampilkan metrik yang tersedia.
- Scanner Highlights menampilkan hasil backend.
- Recent Transactions menampilkan aktivitas terbaru.
- AI Research Highlights dapat membuka laporan.
- Watchlist dapat menampilkan instrumen terpilih.
- Widget memiliki loading, error, dan empty states.
- Multi-portfolio aggregation mengikuti aturan currency.
- Realtime updates tidak membuat koneksi berlebihan.
- Dashboard dapat digunakan pada desktop dan layar kecil.
- Tidak terdapat mock data yang disamarkan sebagai data aktual.

# 24. Related Documents

- `AGENTS.md`
- `specifications/frontend/frontend-spec.md`
- `specifications/frontend/chart-engine-spec.md`
- `specifications/backend/backend-spec.md`
- `specifications/backend/api-spec.md`
- `specifications/backend/websocket-spec.md`
- `specifications/engines/portfolio-engine-spec.md`
- `specifications/engines/risk-engine-spec.md`
- `specifications/engines/allocation-engine-spec.md`
- `specifications/engines/market-scanner-spec.md`
- `specifications/engines/ai-research-spec.md`
- `docs/architecture/data-flow.md`
- `docs/architecture/engine-architecture.md`
- `docs/database/database-design.md`

---

# Final Principle

Dashboard PIMS harus menjadi pusat pemantauan kondisi portofolio dan pasar.

Setiap widget harus memiliki tujuan yang jelas, menggunakan data yang dapat dipertanggungjawabkan, dan memberikan informasi yang relevan.

Prioritas utama bukan jumlah widget atau kompleksitas visual, melainkan akurasi informasi, konsistensi data, keterbacaan, dan kemudahan navigasi.