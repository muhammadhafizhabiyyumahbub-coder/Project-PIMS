# Frontend Specification
## Personal Investment Management System (PIMS)

**Document Version:** 1.0  
**Project Status:** Planning  
**Document Type:** Technical Specification  
**Last Updated:** November 2026

---

# 1. Purpose

Dokumen ini mendefinisikan spesifikasi teknis pengembangan frontend Personal Investment Management System (PIMS).

Frontend merupakan lapisan presentasi yang bertanggung jawab terhadap interaksi pengguna, visualisasi data, navigasi, dan komunikasi dengan backend.

Tujuan dokumen ini:

- Menentukan teknologi frontend.
- Mendefinisikan struktur aplikasi.
- Menentukan standar pengembangan komponen.
- Mendefinisikan routing dan navigasi.
- Mengatur komunikasi REST API dan WebSocket.
- Menentukan pengelolaan state.
- Menentukan standar visualisasi data.
- Menetapkan aturan keamanan dan performa.
- Menjadi panduan implementasi bagi OpenCode.

# 2. Frontend Overview

PIMS menggunakan frontend berbasis Next.js, React, dan TypeScript.

Frontend dirancang sebagai aplikasi financial dashboard yang menyediakan akses ke berbagai modul pengelolaan dan analisis investasi.

Tanggung jawab utama frontend:

1. Menampilkan dashboard.
2. Menampilkan informasi portofolio.
3. Menyediakan interface pencatatan transaksi.
4. Menampilkan market data.
5. Menampilkan interactive charts.
6. Menampilkan hasil quantitative analytics.
7. Menyediakan interface Market Scanner.
8. Menampilkan AI Research reports.
9. Mengelola interaksi dan navigasi pengguna.
10. Menangani loading, error, dan data freshness states.

Frontend tidak bertanggung jawab terhadap perhitungan finansial utama, pengelolaan provider credentials, maupun penyimpanan data secara langsung ke database.

# 3. Technology Stack

Teknologi utama:

| Category | Technology | Status |
|---|---|---|
| Framework | Next.js | Approved |
| UI Library | React | Approved |
| Language | TypeScript | Approved |
| Styling | Tailwind CSS | Approved |
| Chart Library | TradingView Lightweight Charts | Approved |
| API Communication | HTTP REST | Approved |
| Realtime Communication | WebSocket | Approved |
| State Management | To be evaluated | Not decided |
| Form Validation | To be evaluated | Not decided |
| Testing | To be evaluated | Not decided |
| Component Testing | To be evaluated | Not decided |

OpenCode tidak boleh menambahkan library utama baru tanpa alasan teknis yang jelas.

Jika diperlukan library tambahan, OpenCode harus menjelaskan:

- Library yang diusulkan.
- Masalah yang ingin diselesaikan.
- Alternatif yang tersedia.
- Dampak terhadap bundle size.
- Dampak terhadap maintainability.
- Alasan pemilihan.

Keputusan penggunaan library tambahan yang memengaruhi arsitektur harus mendapatkan persetujuan.

# 4. Frontend Architecture

Frontend menggunakan pendekatan Feature-Oriented Architecture.

Struktur aplikasi dibagi berdasarkan fitur bisnis, bukan hanya berdasarkan jenis file.

Tujuannya adalah menjaga setiap modul tetap terorganisasi dan dapat dikembangkan secara independen.

## 4.1 Architectural Principles

Prinsip utama:

- Feature-oriented structure.
- Component reusability.
- Separation of concerns.
- Type safety.
- Centralized API communication.
- Centralized WebSocket management.
- Consistent design system.
- Explicit loading and error states.
- Backend-driven business logic.

## 4.2 Frontend Layers

Frontend memiliki beberapa lapisan konseptual:

| Layer | Responsibility |
|---|---|
| App Layer | Routing and application layout |
| Feature Layer | Business feature interfaces |
| Component Layer | Reusable UI components |
| Service Layer | REST and WebSocket communication |
| State Layer | Shared application state |
| Hook Layer | Reusable React logic |
| Utility Layer | Formatting and helper functions |
| Type Layer | Shared TypeScript contracts |

## 4.3 Dependency Direction

Arah dependency:

```text
App Layer
   │
   ▼
Feature Layer
   │
   ├── Components
   ├── Hooks
   ├── Services
   ├── Stores
   └── Types

Shared Components
   │
   ▼
Design System

Services
   │
   ├── REST API Client
   └── WebSocket Client
```

Ketentuan:

- Shared components tidak boleh bergantung pada business features.
- Feature modules tidak boleh saling mengakses internal implementation secara sembarangan.
- API communication tidak boleh tersebar dalam setiap komponen UI.
- Business calculations tidak boleh dipindahkan ke frontend hanya untuk mempermudah visualisasi.
- Shared types harus memiliki sumber definisi yang konsisten.

# 5. Project Structure

Struktur frontend yang direkomendasikan:

```text
frontend/
├── public/
│   ├── images/
│   ├── icons/
│   └── fonts/
│
├── src/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── globals.css
│   │   │
│   │   ├── dashboard/
│   │   ├── portfolio/
│   │   ├── markets/
│   │   ├── scanner/
│   │   ├── analytics/
│   │   └── research/
│   │
│   ├── components/
│   │   ├── ui/
│   │   ├── layout/
│   │   ├── navigation/
│   │   ├── feedback/
│   │   └── data-display/
│   │
│   ├── features/
│   │   ├── dashboard/
│   │   ├── portfolio/
│   │   ├── markets/
│   │   ├── charts/
│   │   ├── scanner/
│   │   ├── analytics/
│   │   └── research/
│   │
│   ├── hooks/
│   │
│   ├── services/
│   │   ├── api/
│   │   ├── websocket/
│   │   └── adapters/
│   │
│   ├── stores/
│   │
│   ├── types/
│   │   ├── api/
│   │   ├── market/
│   │   ├── portfolio/
│   │   └── common/
│   │
│   ├── utils/
│   │   ├── formatting/
│   │   ├── date/
│   │   └── validation/
│   │
│   └── config/
│
├── tests/
├── package.json
└── Dockerfile
```

Struktur tersebut merupakan target organisasi, bukan kewajiban untuk membuat seluruh folder kosong sejak awal.

OpenCode harus membuat folder berdasarkan kebutuhan implementasi aktual.

# 6. Application Routing

PIMS menggunakan Next.js App Router.

Halaman utama:

| Route | Page | Responsibility |
|---|---|---|
| `/` | Dashboard | Main overview |
| `/portfolio` | Portfolio | Portfolio management |
| `/portfolio/[id]` | Portfolio Detail | Portfolio-specific information |
| `/markets` | Markets | Market overview |
| `/markets/[symbol]` | Instrument Detail | Instrument analysis |
| `/scanner` | Market Scanner | Market screening |
| `/analytics` | Analytics | Quantitative analysis |
| `/research` | AI Research | Research interface |
| `/settings` | Settings | Application configuration |

Route dapat dikembangkan berdasarkan kebutuhan fitur.

Ketentuan:

- Gunakan route yang memiliki nama konsisten.
- Dynamic routes digunakan untuk entitas tertentu.
- Navigation state harus mencerminkan halaman aktif.
- Route yang membutuhkan data harus menangani loading dan error.
- Halaman yang tidak tersedia harus memiliki not-found state.

# 7. Application Layout

Layout utama PIMS menggunakan dashboard structure.

Komponen layout:

## 7.1 Sidebar

Tanggung jawab:

- Main navigation.
- Active page indication.
- Navigation grouping.
- Access to application modules.

## 7.2 Top Navigation

Tanggung jawab:

- Page title.
- Global instrument search entry point.
- Market status.
- Notification entry point.
- Application settings access.

## 7.3 Main Content Area

Tanggung jawab:

- Menampilkan konten sesuai route.
- Mengatur content width.
- Mengelola scroll behavior.
- Menjaga konsistensi spacing.

## 7.4 Responsive Navigation

Pada layar lebih kecil, sidebar dapat berubah menjadi compact navigation atau mobile navigation.

Layout harus tetap dapat digunakan tanpa menghilangkan informasi penting.

# 8. Design System

PIMS menggunakan desain Modern Financial Dashboard dengan karakteristik profesional dan information-dense.

## 8.1 Design Principles

- Clear information hierarchy.
- Consistent typography.
- Consistent spacing.
- Restrained color usage.
- Readable financial data.
- Functional visual hierarchy.
- Consistent component behavior.
- Responsive layout.

## 8.2 Color Semantics

Warna harus memiliki makna yang konsisten.

Contoh penggunaan:

| Semantic Role | Usage |
|---|---|
| Positive | Positive return or increase |
| Negative | Negative return or decrease |
| Neutral | Standard information |
| Warning | Data warning or attention |
| Critical | Important application error |
| Accent | Primary interaction |

Jangan menggunakan warna positif atau negatif hanya sebagai dekorasi.

Nilai finansial juga harus dapat dibedakan melalui tanda, label, atau teks sehingga makna tidak hanya bergantung pada warna.

## 8.3 Typography

Typography harus mendukung pembacaan informasi finansial.

Ketentuan:

- Gunakan hierarchy yang konsisten.
- Angka finansial harus mudah dibandingkan.
- Gunakan tabular numerals untuk data numerik jika tersedia.
- Hindari terlalu banyak variasi font.
- Pastikan ukuran teks tetap terbaca.

## 8.4 Spacing and Layout

- Gunakan spacing scale yang konsisten.
- Hindari elemen yang terlalu rapat.
- Gunakan grid untuk dashboard widgets.
- Pertahankan alignment antar-kolom.
- Prioritaskan informasi penting.

## 8.5 Component Consistency

Komponen dengan fungsi yang sama harus memiliki perilaku dan visual yang konsisten.

Contohnya:

- Buttons.
- Inputs.
- Selects.
- Tables.
- Cards.
- Dialogs.
- Dropdowns.
- Tooltips.
- Loading indicators.
- Status indicators.

# 9. Component Architecture

Komponen dibagi menjadi dua kategori utama.

## 9.1 Shared Components

Komponen yang digunakan oleh banyak fitur.

Contoh:

```text
components/
├── ui/
│   ├── Button.tsx
│   ├── Input.tsx
│   ├── Select.tsx
│   ├── Card.tsx
│   ├── Dialog.tsx
│   └── Tooltip.tsx
│
├── layout/
│   ├── AppLayout.tsx
│   ├── Sidebar.tsx
│   ├── TopNavigation.tsx
│   └── MainContent.tsx
│
├── feedback/
│   ├── LoadingState.tsx
│   ├── ErrorState.tsx
│   └── EmptyState.tsx
│
└── data-display/
    ├── DataTable.tsx
    ├── MetricCard.tsx
    └── StatusIndicator.tsx
```

Shared components harus bersifat reusable dan tidak mengandung business logic fitur tertentu.

## 9.2 Feature Components

Komponen yang memiliki tanggung jawab khusus terhadap fitur.

Contoh:

```text
features/
├── dashboard/
├── portfolio/
├── markets/
├── charts/
├── scanner/
├── analytics/
└── research/
```

Setiap feature dapat memiliki:

- Components.
- Hooks.
- Services.
- Types.
- Utils.
- Tests.

Tidak semua feature harus memiliki seluruh jenis file tersebut.

# 10. Feature Specifications

## 10.1 Dashboard

Dashboard menjadi pusat informasi utama PIMS.

Informasi yang dapat ditampilkan:

- Portfolio overview.
- Total portfolio value.
- Performance summary.
- Asset allocation.
- Market overview.
- Watchlist.
- Recent transactions.
- Risk summary.
- Scanner highlights.

Dashboard harus mengambil data dari backend melalui service layer.

Detail layout dan widget akan ditentukan dalam:

`specifications/frontend/dashboard-spec.md`

## 10.2 Portfolio Interface

Tanggung jawab:

- Portfolio list.
- Portfolio detail.
- Holdings table.
- Transaction history.
- Transaction form.
- Cash balance.
- Portfolio performance display.

Ketentuan:

- Form harus memiliki validation.
- Transaksi harus dikonfirmasi sebelum dikirim.
- Hasil transaksi harus mencerminkan respons backend.
- Perhitungan holdings tidak boleh dibuat ulang sebagai sumber kebenaran di frontend.

## 10.3 Market Interface

Tanggung jawab:

- Instrument search.
- Market overview.
- Instrument detail.
- Latest price display.
- Historical price visualization.
- Market status.
- Data freshness.

Frontend harus menampilkan informasi sumber data jika tersedia.

## 10.4 Chart Interface

Chart menggunakan TradingView Lightweight Charts.

Tanggung jawab:

- Chart rendering.
- Historical candle display.
- Streaming updates.
- Timeframe selection.
- Indicator visualization.
- Chart interaction.

Frontend tidak menghitung indikator finansial utama.

Detail implementasi chart akan ditentukan dalam:

`specifications/frontend/chart-engine-spec.md`

## 10.5 Market Scanner Interface

Tanggung jawab:

- Scanner categories.
- Scanner filters.
- Market universe selection.
- Results table.
- Ranking display.
- Scanner run status.
- Instrument navigation.

Frontend hanya mengatur filter dan menampilkan hasil yang dihitung backend.

## 10.6 Analytics Interface

Tanggung jawab:

- Performance visualization.
- Risk metrics.
- Allocation charts.
- Correlation visualization.
- Market regime display.

Semua angka harus berasal dari backend.

## 10.7 AI Research Interface

Tanggung jawab:

- Research request input.
- Research loading state.
- Research report display.
- Source references.
- Research history.
- Report metadata.

AI response harus ditampilkan secara terstruktur dan membedakan fakta, data, dan interpretasi.

# 11. API Integration

Semua komunikasi REST API harus menggunakan centralized API service.

Frontend tidak boleh menyebarkan penggunaan `fetch` atau HTTP clients secara tidak terstruktur ke seluruh komponen.

## 11.1 API Client

Tanggung jawab:

- Base URL configuration.
- Request handling.
- Response parsing.
- Error normalization.
- Timeout handling.
- Request cancellation jika diperlukan.

## 11.2 API Service Organization

Contoh struktur:

```text
services/
└── api/
    ├── client.ts
    ├── endpoints.ts
    ├── portfolio.api.ts
    ├── market.api.ts
    ├── analytics.api.ts
    ├── scanner.api.ts
    └── research.api.ts
```

Struktur tersebut dapat disesuaikan selama pemisahan tanggung jawab tetap terjaga.

## 11.3 API Response Handling

Frontend harus dapat menangani:

- Successful response.
- Validation error.
- Authentication error jika authentication diterapkan.
- Not found.
- Rate limit.
- Server error.
- Network failure.
- Timeout.

Jangan menampilkan error teknis mentah kepada pengguna.

## 11.4 Type Safety

TypeScript types harus konsisten dengan backend API contracts.

Jika memungkinkan, API contracts harus memiliki sumber definisi yang dapat digunakan untuk menghasilkan atau memvalidasi frontend types.

OpenCode tidak boleh membuat asumsi terhadap struktur response yang belum ditentukan.

# 12. WebSocket Integration

WebSocket digunakan untuk menerima data yang membutuhkan pembaruan berkelanjutan.

Jenis event:

- Market price update.
- Candle update.
- Scanner notification.
- Market event.
- Connection status.

## 12.1 WebSocket Manager

Gunakan centralized WebSocket manager.

Tanggung jawab:

- Establish connection.
- Maintain connection.
- Manage subscriptions.
- Handle reconnection.
- Parse incoming messages.
- Distribute events to subscribers.
- Handle connection state.

## 12.2 Subscription Management

Frontend harus melakukan subscription hanya terhadap data yang diperlukan.

Contoh:

- Instrumen yang sedang dibuka.
- Watchlist yang aktif.
- Scanner notifications yang relevan.

Ketika halaman atau komponen tidak lagi membutuhkan subscription, subscription harus dilepas.

## 12.3 Reconnection Handling

Ketika koneksi terputus:

- Tampilkan connection status.
- Lakukan reconnect sesuai kebijakan.
- Restore subscription yang masih diperlukan.
- Periksa kembali konsistensi data setelah reconnect.
- Jangan menganggap data lama sebagai live.

## 12.4 Message Validation

Incoming messages harus diperiksa sebelum digunakan.

Frontend harus menangani:

- Invalid payload.
- Unknown event type.
- Missing fields.
- Unexpected timestamp.
- Duplicate updates.

# 13. State Management

Frontend harus memisahkan beberapa jenis state.

| State Type | Examples |
|---|---|
| Local UI State | Modal, dropdown, tabs |
| Server State | Portfolio, holdings, analytics |
| Realtime State | Latest prices, candle updates |
| Form State | Transaction form, filters |
| Navigation State | Active route, selected portfolio |

Prinsip:

- Jangan menyimpan semua state dalam satu global store.
- Gunakan local state untuk interaksi sederhana.
- Server state harus memiliki mekanisme caching dan invalidation yang sesuai.
- Realtime state harus dikelola secara terkontrol.
- State yang dapat diturunkan tidak perlu disimpan berulang kali.
- Hindari duplicate sources of truth.

Library state management belum ditetapkan. OpenCode harus mengusulkan pilihan berdasarkan kompleksitas aktual dan mendapatkan persetujuan sebelum menambahkan dependency utama.

# 14. Data Formatting

Data finansial harus diformat secara konsisten.

Jenis formatting:

- Currency.
- Price.
- Percentage.
- Volume.
- Quantity.
- Date.
- Time.
- Market session.
- Return.
- P&L.

Ketentuan:

- Currency harus memiliki kode yang jelas.
- Percentage harus menggunakan precision yang konsisten.
- Angka yang tidak tersedia tidak boleh ditampilkan sebagai nol.
- Timestamp harus ditampilkan menggunakan timezone yang ditentukan aplikasi.
- Nilai yang dibulatkan tidak boleh mengubah nilai asli yang digunakan backend.
- Negative values harus dapat dibedakan dengan jelas.

Formatting utility harus digunakan bersama agar tidak terjadi perbedaan tampilan antarhalaman.

# 15. Loading, Error, and Empty States

Setiap fitur yang mengambil data dari backend harus memiliki state yang jelas.

## 15.1 Loading State

Digunakan ketika data sedang dimuat atau proses sedang berjalan.

## 15.2 Error State

Digunakan ketika request gagal.

Informasi yang ditampilkan:

- Penjelasan singkat.
- Status kegagalan.
- Retry action jika memungkinkan.

## 15.3 Empty State

Digunakan ketika belum ada data.

Contoh:

- Belum ada portofolio.
- Belum ada transaksi.
- Belum ada scanner results.
- Belum ada research reports.

## 15.4 Partial Data State

Jika hanya sebagian data tersedia, frontend harus menjelaskan bagian mana yang belum tersedia.

Jangan menampilkan dashboard seolah seluruh data lengkap apabila sebagian sumber mengalami kegagalan.

# 16. Performance Requirements

Frontend harus memperhatikan performa karena PIMS menampilkan data numerik, tabel, dan chart yang dapat diperbarui secara berkelanjutan.

Ketentuan:

- Hindari unnecessary re-renders.
- Gunakan component boundaries yang tepat.
- Hindari memuat seluruh market universe sekaligus.
- Gunakan pagination atau virtualization untuk tabel besar jika diperlukan.
- Batasi jumlah data chart sesuai kebutuhan timeframe.
- Hindari membuat WebSocket connection berulang untuk satu sumber yang sama.
- Gunakan dynamic loading untuk komponen berat jika diperlukan.
- Pisahkan komponen client-side yang memang memerlukan browser interaction.

Target performa kuantitatif akan ditetapkan melalui testing requirements dan hasil pengukuran.

# 17. Responsive Design

PIMS harus dapat digunakan pada:

- Desktop.
- Laptop.
- Tablet.
- Mobile browser.

Prioritas desain utama adalah desktop karena dashboard memiliki banyak informasi.

Namun, fungsi penting tetap harus tersedia pada layar kecil.

Ketentuan:

- Sidebar harus adaptif.
- Tables harus memiliki strategi responsive.
- Chart harus menyesuaikan container.
- Metric cards harus mengikuti layout grid.
- Modal dan forms harus tetap dapat digunakan.
- Tidak boleh terjadi horizontal overflow yang tidak disengaja.

# 18. Accessibility

Frontend harus mengikuti prinsip accessibility dasar.

Ketentuan:

- Semantic HTML.
- Keyboard navigation.
- Visible focus states.
- Accessible form labels.
- Meaningful button labels.
- Sufficient color contrast.
- Screen reader friendly status messages.
- Do not rely on color alone.

Interactive charts harus tetap memiliki informasi pendukung yang dapat dibaca di luar visual chart jika diperlukan.

# 19. Security Requirements

Frontend harus menerapkan aturan keamanan berikut:

1. Tidak menyimpan provider API secrets.
2. Tidak mengakses database secara langsung.
3. Tidak menaruh AI provider keys di client-side code.
4. Menggunakan environment variables hanya untuk konfigurasi frontend yang memang aman diekspos.
5. Tidak menampilkan sensitive backend error details.
6. Memvalidasi input sebelum dikirim ke backend.
7. Tidak menganggap frontend validation sebagai pengganti backend validation.
8. Menghindari penyimpanan data sensitif di browser storage tanpa kebutuhan dan evaluasi keamanan.
9. Menangani external links dengan aman.
10. Tidak mempercayai data dari WebSocket tanpa validasi.

Jika authentication ditambahkan pada fase berikutnya, mekanisme session dan credential storage harus mengikuti security specification.

# 20. Testing Requirements

Frontend harus memiliki pengujian sesuai kompleksitas fitur.

| Test Type | Purpose |
|---|---|
| Component Tests | Menguji perilaku komponen |
| Unit Tests | Menguji utility dan hooks |
| API Integration Tests | Menguji komunikasi API |
| WebSocket Tests | Menguji event handling |
| Form Tests | Menguji input validation |
| E2E Tests | Menguji workflow pengguna |
| Visual Review | Memeriksa konsistensi UI |

Test cases minimal mencakup:

- Dashboard loading.
- Portfolio list retrieval.
- Transaction form validation.
- Market data display.
- Chart historical loading.
- WebSocket connection handling.
- Scanner result rendering.
- Analytics error handling.
- Empty states.

# 21. Gemini Design Reference Integration

PIMS dapat menggunakan hasil desain Gemini sebagai referensi visual.

Lokasi:

```text
design-reference/
└── dashboard/
    ├── Dashboard.tsx
    ├── components/
    ├── data/
    ├── styles/
    └── assets/
```

Folder tersebut merupakan design reference, bukan implementasi final frontend.

Ketentuan:

1. OpenCode harus memeriksa desain yang tersedia sebelum membuat dashboard.
2. Identifikasi layout, typography, spacing, colors, dan komponen visual.
3. Pisahkan visual reference dari business logic.
4. Jangan menganggap data contoh sebagai data pasar asli.
5. Jangan mengimpor seluruh design reference secara langsung tanpa evaluasi.
6. Adaptasi desain ke arsitektur frontend yang telah disetujui.
7. Pertahankan konsistensi dengan design direction PIMS.

Jika terdapat perbedaan antara desain referensi dan kebutuhan fungsional, kebutuhan fungsional serta arsitektur yang disetujui menjadi acuan.

# 22. Implementation Guidelines for OpenCode

OpenCode wajib mengikuti ketentuan:

- Gunakan TypeScript secara konsisten.
- Hindari `any` tanpa alasan yang dapat dipertanggungjawabkan.
- Gunakan feature-oriented architecture.
- Gunakan shared components untuk elemen berulang.
- Pisahkan API communication dari UI components.
- Pisahkan local state dan server state.
- Gunakan centralized WebSocket manager.
- Jangan membuat perhitungan finansial utama di frontend.
- Jangan menggunakan mock data seolah data live.
- Jangan membuat seluruh modul sekaligus.
- Jangan menambahkan library besar tanpa persetujuan.
- Jalankan linting, type checking, dan tests.
- Perbarui dokumentasi jika terjadi perubahan yang disetujui.

# 23. Implementation Order

Urutan implementasi frontend:

| Phase | Component | Priority |
|---|---|---|
| 1 | Next.js foundation | Critical |
| 2 | Global layout and navigation | Critical |
| 3 | Design system foundation | Critical |
| 4 | API service foundation | Critical |
| 5 | Portfolio interface | High |
| 6 | Market interface | High |
| 7 | Chart integration | High |
| 8 | Dashboard widgets | High |
| 9 | Analytics interface | High |
| 10 | Market Scanner interface | High |
| 11 | AI Research interface | Medium |

Implementasi harus mengikuti dependency backend dan tidak boleh mengandalkan endpoint yang belum tersedia tanpa mock contract yang jelas.

Mock data hanya boleh digunakan dalam development dan testing dengan identitas yang jelas.

# 24. Acceptance Criteria

Frontend specification dianggap telah diimplementasikan dengan baik apabila:

- Next.js application berjalan.
- TypeScript digunakan secara konsisten.
- Routing utama tersedia.
- Layout utama konsisten.
- Design system dasar tersedia.
- API communication terpusat.
- WebSocket management terpusat.
- Loading, error, dan empty states tersedia.
- Frontend tidak melakukan database access langsung.
- Provider credentials tidak terekspos.
- Chart dapat menerima data dari backend.
- Financial values ditampilkan secara konsisten.
- Responsive behavior berfungsi.
- Komponen utama memiliki pengujian.
- Tidak ada critical type errors atau linting errors yang belum diselesaikan.

# 25. Related Documents

- `AGENTS.md`
- `specifications/project/project-overview.md`
- `specifications/project/project-scope.md`
- `specifications/project/development-roadmap.md`
- `specifications/frontend/dashboard-spec.md`
- `specifications/frontend/chart-engine-spec.md`
- `specifications/backend/backend-spec.md`
- `specifications/backend/api-spec.md`
- `specifications/backend/websocket-spec.md`
- `docs/architecture/application-architecture.md`
- `docs/architecture/component-diagram.md`
- `docs/architecture/data-flow-diagram.md`
- `docs/decisions/technical-decisions.md`

---

# Final Principle

Frontend PIMS harus berfungsi sebagai presentation and interaction layer yang terintegrasi dengan backend secara konsisten.

Seluruh data finansial harus berasal dari backend yang menjadi sumber kebenaran. Frontend berfokus pada penyajian informasi, visualisasi, interaksi, dan pengalaman pengguna.

Desain harus mendukung kebutuhan analisis finansial yang kompleks tanpa mengorbankan keterbacaan, konsistensi, dan performa aplikasi.