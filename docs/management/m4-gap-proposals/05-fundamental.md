# M4 Gap Proposal — Fundamental Engine *(DEFERRED)*

**Status:** PROPOSED — implementasi **DEFERRED** owner (menunggu data + metodologi approval).
**Priority:** di luar 4 engine M4 (fundamental/macro/sentiment deferred).
**Aturan:** Kode TIDAK dimulai sebelum data provider + metodologi di-approve. Proposal ini = **gap analysis** untuk review owner.

---

## 1. Tujuan dan Scope

Fundamental engine mengkuantifikasi kualitas finansial asset (terutama STOCK) dari laporan keuangan, untuk skoring / input factor / research.

**In-scope (setelah approval):**
- Metrik fundamental (P/E, P/B, ROE, revenue growth, D/E, EPS, dividend yield).
- Normalisasi periode pelaporan + currency.
- Missing-value policy.
- Data-quality validation.

**Kondisi saat ini (HONEST):**
- **Tidak ada** tabel fundamental di PIMS.
- **Tidak ada** Fundamental Data Provider (owner deferred §A.5).
- Engine hanya berisi `__init__.py`.

> ⚠️ **Gap utama:** engine ini **blocked** sampai owner menyetujui (a) source data fundamental, (b) set metrik, (c) currency + refresh cadence. Tanpa itu, tak ada yang bisa diimplement.

## 2. Metodologi Alternatif yang Relevan

| Opsi | Deskripsi | Ketersediaan Data |
|---|---|---|
| **A. Provider otomatis (Yahoo Finance fundamentals)** | Fetch P/E, ROE, dsb via endpoint Yahoo (sudah provider PIMS) | ⚠️ Tersedia untuk US/IDX sebagian; **kualitas + coverage bervariasi**; perlu validasi |
| **B. Input manual user** | User isi metrik per asset | ✅ Deterministik, tak bergantung provider; cocok uni-user tapi manual |
| **C. Provider berbayar** | API fundamental (mis. Financial Modeling Prep, EODHD, Alpha Vantage) | ⚠️ Butuh biaya + API key (owner tak boleh dibelanjai oleh agent) |

## 3. Rekomendasi Metodologi + Alasan

**Rekomendasi: Phase A (Yahoo) untuk coverage awal + Phase B (manual) sebagai fallback; Phase C (berbayar) hanya jika A/B tak cukup.**

- **Alasan:** PIMS sudah pakai YAHOO (provider mapping ada). Opsi A zero new dependency. Opsi B menjamin data walau provider gagal. Opsi C = keputusan biaya → approval owner (agent tidak membelanjai layanan).
- **Catatan:** fundamental terutama relevan untuk **STOCK** (US/IDX); **CRYPTO tak punya laporan keuangan** → fundamental factor tak berlaku untuk crypto (flag).

> ⚠️ **Flag untuk approval:** source (A/B/C), set metrik, currency normalization, refresh cadence, missing-value policy — semua §14.

## 4. Formula dan Definisi Metrik *(PROPOSED — perlu approval)*

| Metrik | Definisi | Sumber |
|---|---|---|
| P/E | `price / EPS` (trailing) | harga (candle) + EPS (fundamental) |
| P/B | `price / book_value_per_share` | harga + BVPS |
| ROE | `net_income / equity` (TTM) | laporan keuangan |
| Revenue growth | `(rev_t − rev_{t-1}) / rev_{t-1}` (YoY) | laporan |
| D/E | `total_debt / equity` | laporan |
| EPS | `net_income / shares_out` | laporan |
| Dividend yield | `dividend_per_share / price` | laporan + harga |

> ⚠️ **Flag:** set metrik mana yang wajib, trailing vs forward, TTM window — approval owner §14.

## 5. Data Input dan Sumbernya

| Input | Sumber | Ketersediaan |
|---|---|---|
| Harga (untuk P/E, P/B, div yield) | `MarketCandle` | ✅ Ada |
| EPS, BVPS, ROE, revenue, debt, equity | **Fundamental provider (A/B/C)** | ❌ Tak ada sekarang |
| Periode pelaporan (fiscal year, currency) | Fundamental provider | ❌ Tak ada |

## 6. Data Availability dan Kualitas

- **HONEST:** **0 data fundamental** di PIMS. Tak ada table, tak ada provider.
- **Kualitas (jika pakai Yahoo):** coverage bervariasi per ticker; IDX data fundamental terbatas; revision tak di-track.
- **Currency:** laporan dalam currency emiten → perlu normalisasi ke currency portfolio (decision).
- **Missing value:** metrik tak tersedia → policy exclude/null (decision).

## 7. Dependency terhadap Engine Lain

- `technical`/`portfolio` (harga) — ada.
- **Fundamental Data Provider** — **blocked** (owner decision §A.5).
- `factor` engine (Phase 2 fundamental factor) — bergantung engine ini.

## 8. Database Schema yang Dibutuhkan *(PROPOSED — tidak dibuat sampai approved)*

| Tabel | Kolom kunci |
|---|---|
| `fundamental_metrics` | `id`, `asset_id` FK, `metric` (key), `value` (numeric), `period` (fiscal), `currency`, `source` (provider), `as_of` (ts), `quality` (enum), `created_at` |

> ⚠️ **Owner eksplisit (§A.5): jangan buat migration fundamental sebelum data provider di-approve.** Schema ini hanya PROPOSED.

## 9. API dan Output Contract *(PROPOSED)*

`GET /api/v1/fundamental/metrics?asset_id=&metric=&period=`
- Response: `{ asset_symbol, metrics: {pe, roe, ...}, period, currency, source, as_of, quality, missing }`

> ⚠️ Kontrak **proposed** — tak diimplement sampai approved.

## 10. Risiko Metodologi dan Keterbatasan

- **Blocked data:** tanpa provider, engine tak bisa jalan.
- **Coverage IDX rendah:** fundamental IDX lebih terbatas vs US.
- **Currency + periode:** mismatch → metrik misleading; perlu normalisasi.
- **Crypto N/A:** fundamental tak berlaku untuk crypto (harus di-flag, bukan error).
- **Provider cost (C):** keputusan biaya → owner.

## 11. Unit Test dan Integration Test

- **Unit:** normalisasi currency, missing-value handling, metrik calculation (dengan input fundamental sintetis).
- **Integration:** (setelah provider) fetch + persist `fundamental_metrics`; determinism; crypto → "N/A" flag.
- **Regression:** tak ada code path fundamental sebelum approved.

## 12. Acceptance Criteria

1. Metrik fundamental dihitung dari data yang **sudah disetujui** (bukan dikarang).
2. Currency + periode pelaporan dinormalisasi.
3. Missing value di-handle sesuai policy (di-approve).
4. Crypto → flag "N/A" (bukan error).
5. Data quality + source + timestamp di-report.
6. Determinism.
7. **Tidak ada** implementation sebelum provider + metrik di-approve.

## 13. Tahapan Implementasi

1. **Owner approve** source data + metrik + currency + cadence (§14).
2. **Spec final** → `specifications/engines/fundamental-engine-spec.md`.
3. **Provider integration** (A/B/C sesuai approval).
4. **Model + migration** (`fundamental_metrics`).
5. **Engine deterministik** (normalisasi + metrik).
6. **API + test**.

> **Tidak dimulai sekarang** — owner deferred.

## 14. Keputusan yang Membutuhkan Product Owner Approval

| # | Keputusan | Opsi |
|---|---|---|
| 1 | Source data fundamental | A (Yahoo) / B (manual) / C (berbayar) — **butuh pilihan** |
| 2 | Set metrik wajib | P/E, P/B, ROE, rev growth, D/E, EPS, div yield — **butuh pilihan** |
| 3 | Trailing vs forward | **butuh pilihan** |
| 4 | Currency normalization | ke currency portfolio / as-is — **butuh pilihan** |
| 5 | Refresh cadence | harian / per-laporan / manual — **butuh pilihan** |
| 6 | Missing-value policy | exclude / null / impute — **butuh pilihan** |
| 7 | Apakah fundamental untuk crypto | N/A (flag) — **saran: approve** |
| 8 | Provider berbayar (C) | hanya jika A/B tak cukup — **butuh approval biaya** |
