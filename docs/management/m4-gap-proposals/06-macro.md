# M4 Gap Proposal — Macro Engine *(DEFERRED)*

**Status:** PROPOSED — implementasi **DEFERRED** owner (menunggu data + metodologi approval).
**Priority:** di luar 4 engine M4.
**Aturan:** Kode TIDAK dimulai sebelum data provider + metodologi di-approve. Proposal ini = **gap analysis** untuk review owner.

---

## 1. Tujuan dan Scope

Macro engine mengkuantifikasi kondisi makroekonomi untuk mengontekstualkan regime pasar + input risk/allocation.

**In-scope (setelah approval):**
- Indikator makro (suku bunga, inflasi/CPI, yield curve, VIX, USD index, GDP).
- Frekuensi data + revision policy + lag handling.
- Definisi regime (terhubung `market_regime` engine).

**Kondisi saat ini (HONEST):**
- PIMS punya `market_regime` engine (existing) tapi **tanpa data makro**.
- **Tidak ada** tabel makro, **tidak ada** Macro Data Provider (owner deferred §A.6).
- Engine hanya `__init__.py`.

> ⚠️ **Gap utama:** engine ini **blocked** sampai owner menyetujui (a) source data makro, (b) set indikator, (c) frekuensi + regime model. Tanpa itu, tak ada yang bisa diimplement.

## 2. Metodologi Alternatif yang Relevan

| Opsi | Deskripsi | Ketersediaan Data |
|---|---|---|
| **A. Provider seri waktu makro (mis. FRED)** | Suku bunga, CPI, GDP dari sumber publik | ⚠️ FRED gratis tapi API key + coverage (terutama USD/US-centric); IDX/IDR terbatas |
| **B. Input manual / kurasi** | User input indikator kunci (mis. BI rate, CPI ID) | ✅ Deterministik, uni-user; manual |
| **C. Provider berbayar** | API makro (mis. Quandl/Nasdaq Data Link) | ⚠️ Biaya + API key (owner tak boleh dibelanjai oleh agent) |

## 3. Rekomendasi Metodologi + Alasan

**Rekomendasi: Phase B (manual/kurasi) dulu untuk indikator kunci + Phase A (FRED) untuk data US/USD; Phase C hanya jika perlu.**

- **Alasan:** indikator kunci untuk decision investing (BI rate, CPI, VIX) bisa di-kurasi manual (uni-user, frekuensi rendah). FRED untuk seri waktu US/USD (gratis, API key). Berbayar = keputusan biaya → approval owner.
- **Catatan:** data makro bersifat **lagged + revised** → engine harus handle revision policy (decision).

> ⚠️ **Flag untuk approval:** set indikator, source, frekuensi, revision policy, lag handling, regime model — semua §14.

## 4. Formula dan Definisi Metrik *(PROPOSED — perlu approval)*

| Indikator | Definisi |
|---|---|
| Real rate | `nominal_rate − inflation` |
| Yield curve slope | `long_term_rate − short_term_rate` (mis. 10y − 2y) |
| Inflation momentum | `(CPI_t − CPI_{t-1}) / CPI_{t-1}` |
| Risk-on/off proxy | VIX level + z-score |
| Regime score | kombinasi indikator (definisi = decision owner) |

> ⚠️ **Flag:** set indikator, bobot regime, threshold — approval owner §14.

## 5. Data Input dan Sumbernya

| Input | Sumber | Ketersediaan |
|---|---|---|
| Suku bunga, CPI, GDP, VIX, USD index | **Macro provider (A/B/C)** | ❌ Tak ada sekarang |
| Regime (existing) | `market_regime` engine | ✅ Ada (tapi tanpa data makro) |

## 6. Data Availability dan Kualitas

- **HONEST:** **0 data makro** di PIMS. Tak ada table, tak ada provider.
- **Revision:** data makro di-revision (CPI, GDP) → engine harus track revision (decision).
- **Lag:** data makro keluar terlambat (CPI monthly/quarterly) → lag handling (decision).
- **Frekuensi:** campur (daily VIX, monthly CPI, quarterly GDP) → normalisasi waktu (decision).
- **Coverage IDR/IDX:** sumber makro Indonesia lebih terbatas.

## 7. Dependency terhadap Engine Lain

- `market_regime` (existing) — makro bisa feed regime (decision: apakah feed atau terpisah?).
- **Macro Data Provider** — **blocked** (owner decision §A.6).
- `risk` / `allocation` (opsional, downstream) — bergantung.

## 8. Database Schema yang Dibutuhkan *(PROPOSED — tidak dibuat sampai approved)*

| Tabel | Kolom kunci |
|---|---|
| `macro_indicators` | `id`, `indicator` (key), `value` (numeric), `period` (ts), `frequency`, `currency`, `revision` (int), `source`, `created_at` |

> ⚠️ **Owner eksplisit (§A.6): jangan buat migration makro sebelum data provider di-approve.** Schema ini hanya PROPOSED.

## 9. API dan Output Contract *(PROPOSED)*

`GET /api/v1/macro/indicators?indicator=&period_from=&period_to=`
- Response: `{ indicators: [{key, value, period, frequency, revision, source}], regime_summary? }`

> ⚠️ Kontrak **proposed** — tak diimplement sampai approved.

## 10. Risiko Metodologi dan Keterbatasan

- **Blocked data:** tanpa provider, engine tak bisa jalan.
- **Revision:** data lama berubah → hasil regime bisa berubah retroaktif (flag).
- **Lag:** decision dibuat dengan data terlambat → keterbatasan.
- **Regime definition:** tanpa definisi disetujui, regime = arbitrer (decision owner).
- **Provider cost (C):** keputusan biaya → owner.

## 11. Unit Test dan Integration Test

- **Unit:** normalisasi frekuensi, revision tracking, yield curve slope, real rate (input sintetis).
- **Integration:** (setelah provider) fetch + persist `macro_indicators`; regime summary; determinism.
- **Regression:** tak ada code path makro sebelum approved.

## 12. Acceptance Criteria

1. Indikator makro diambil dari source yang **sudah disetujui** (bukan dikarang).
2. Revision policy + lag handling di-apply.
3. Frekuensi campur dinormalisasi.
4. Regime definition sesuai keputusan owner.
5. Source + period + revision di-report.
6. Determinism.
7. **Tidak ada** implementation sebelum provider + indikator di-approve.

## 13. Tahapan Implementasi

1. **Owner approve** source + indikator + frekuensi + regime model (§14).
2. **Spec final** → `specifications/engines/macro-engine-spec.md`.
3. **Provider integration** (A/B/C sesuai approval).
4. **Model + migration** (`macro_indicators`).
5. **Engine deterministik** (normalisasi + indikator + regime).
6. **API + test**.

> **Tidak dimulai sekarang** — owner deferred.

## 14. Keputusan yang Membutuhkan Product Owner Approval

| # | Keputusan | Opsi |
|---|---|---|
| 1 | Source data makro | A (FRED) / B (manual) / C (berbayar) — **butuh pilihan** |
| 2 | Set indikator | BI rate, CPI, yield curve, VIX, USD index, GDP — **butuh pilihan** |
| 3 | Frekuensi | daily/weekly/monthly/quarterly — **butuh pilihan** |
| 4 | Revision policy | track + replay / pakai terbaru saja — **butuh pilihan** |
| 5 | Lag handling | flag / backfill — **butuh pilihan** |
| 6 | Regime model | feed `market_regime` / terpisah — **butuh pilihan** |
| 7 | Provider berbayar (C) | hanya jika perlu — **butuh approval biaya** |
