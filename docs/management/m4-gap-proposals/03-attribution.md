# M4 Gap Proposal — Attribution Engine

**Status:** PROPOSED (menunggu approval metodologi Product Owner).
**Priority:** #3 dari 4 engine M4 (owner decision).
**Aturan:** Kode TIDAK dimulai sebelum metodologi di-approve.

---

## 1. Tujuan dan Scope

Attribution engine menjelaskan **dari mana** return portfolio berasal: kontribusi tiap asset (alokasi vs selektif) relatif terhadap benchmark, pada periode tertentu.

**In-scope:**
- Asset-level attribution (kontribusi tiap holding ke return portfolio).
- Brinson-Fachler (allocation + selection + interaction) — **butuh benchmark + klasifikasi**.
- Return-based attribution (regresi exposure) — deferred.
- Periode + benchmark configurable.

**Out-of-scope (fase ini):**
- Sector-level Brinson (PIMS tak punya klasifikasi sector/asset resmi → decision).
- Multi-period rolling attribution.

## 2. Metodologi Alternatif yang Relevan

| Opsi | Deskripsi | Kebutuhan |
|---|---|---|
| **A. Asset-level attribution** | Kontribusi tiap holding: `wgt_i × return_i` vs benchmark | Data holdings + return (sudah ada) — **feasible now** |
| **B. Brinson-Fachler** | `allocation + selection + interaction` per asset class/sector | Benchmark weight + klasifikasi aset (decision) |
| **C. Return-based (regresi)** | Regresi return portfolio terhadap factor/benchmark | Factor data + regression (complex) — deferred |

## 3. Rekomendasi Metodologi + Alasan

**Rekomendasi: phased A → B (C deferred).**

- **Phase 1:** Opsi A — asset-level attribution. Paling sederhana, langsung pakai `portfolio` holdings + `MarketCandle` return + benchmark (configurable). Menjawab "aset mana yang menggerakkan portfolio".
- **Phase 2:** Opsi B — Brinson-Fachler. **Butuh decision owner:** benchmark choice + klasifikasi aset/sector + periode (lihat §14).
- **Opsi C deferred** — kompleks (regresi), manfaat terbatas untuk uni-user; tunda.

**Alasan:** owner minta evaluasi Brinson-Fachler vs return-based + jelaskan kebutuhan benchmark/klasifikasi/periode/alokasi-vs-seleksi. Asset-level adalah fondasi; Brinson-Fachler menambah decompose alokasi vs seleksi.

> ⚠️ **Flag untuk approval:** benchmark choice, klasifikasi aset (apakah pakai `market` CRYPTO/US/IDX sebagai "class"?), periode attribution, definisi selection vs allocation — semua §14.

## 4. Formula dan Definisi Metrik *(PROPOSED — perlu approval)*

**Asset-level (Phase 1):**
- Contribution asset `i`: `C_i = w_i · r_i` (weight awal periode × return).
- Total: `Σ C_i = R_portfolio` (konservasi).
- Active vs benchmark: `C_i^active = w_i·r_i − w_i^bench·r_i^bench`.

**Brinson-Fachler (Phase 2):** per asset class `k`:
- **Allocation:** `A_k = (w_k − b_k) · (R_k − R_b)` (selisih weight × selisih return class).
- **Selection:** `S_k = b_k · (R_k − R_b)` (return class di atas di bawah benchmark, pada weight benchmark).
- **Interaction:** `I_k = (w_k − b_k) · (R_k − R_b)` — BF klasik: `A + I` digabung atau dipisah.
- **Total BF:** `Σ (A_k + S_k + I_k) = R_p − R_b`.

> ⚠️ **Flag:** definisi asset class, benchmark weight `b_k`, split interaction ke allocation/seleksi (BF vs Brennan-Scotto), periode — approval owner §14.

## 5. Data Input dan Sumbernya

| Input | Sumber PIMS | Ketersediaan |
|---|---|---|
| Holding weight + return | `portfolio` + `MarketCandle` | ✅ Ada |
| Benchmark return | Konfigurasi (asset / index) | ⚠️ Perlu decision |
| Benchmark weight per class | Konfigurasi | ⚠️ Perlu decision |
| Klasifikasi aset/sector | `Asset.market` (CRYPTO/US/IDX) sebagai proxy | ⚠️ Perlu decision (cukup? atau perlu klasifikasi lebih?) |

## 6. Data Availability dan Kualitas

- **Asset-level:** feasible — holdings + return ada.
- **Brinson-Fachler:** bergantung pada **benchmark + klasifikasi** (decision owner). Jika benchmark = single asset (mis. BTC), BF degenerasi jadi asset-level → perlu benchmark multi-class untuk BF bermakna.
- **Keterbatasan:** klasifikasi sector resmi (GICS/sector) tak ada di PIMS; `market` (CRYPTO/US/IDX) adalah granularitas tertinggi saat ini.

## 7. Dependency terhadap Engine Lain

- `portfolio` (holdings + valuation) — wajib.
- `technical`/return engine — return per asset (sudah ada di portfolio performance).
- `benchmark` (config) — eksternal decision.

## 8. Database Schema yang Dibutuhkan *(PROPOSED)*

| Tabel | Kolom kunci |
|---|---|
| `attribution_runs` | `id`, `portfolio_id` FK, `benchmark`, `period_start`, `period_end`, `method` (ASSET/BF), `created_at` |
| `attribution_results` | `id`, `run_id` FK, `asset_id` FK, `contribution` (numeric), `allocation` (numeric, BF), `selection` (numeric, BF), `interaction` (numeric, BF), `created_at` |

> ⚠️ Schema **proposed**. Finalisasi setelah approval.

## 9. API dan Output Contract *(PROPOSED)*

`POST /api/v1/attribution/runs`
- Request: `{ portfolio_id, benchmark, period_start, period_end, method: "ASSET"|"BRINSON_FACHLER" }`
- Response: `{ run_id, status, total_active_return, breakdown: [{symbol, contribution, allocation?, selection?, interaction?}], benchmark_return }`

`GET /api/v1/attribution/runs/{run_id}`.

Status: `COMPLETED` / `INSUFFICIENT_DATA` / `INVALID_CONFIG` (mis. BF dengan benchmark tunggal → warning).

> ⚠️ Kontrak **proposed**.

## 10. Risiko Metodologi dan Keterbatasan

- **Benchmark choice menentukan semua:** BF tanpa benchmark multi-class = degenerasi.
- **Klasifikasi granularitas:** `market` (3 kelas) terlalu kasar untuk BF sector-level → decision apakah cukup atau perlu klasifikasi lebih.
- **Periode:** mismatch holding weight vs return window → hasil misleading.
- **BF variant (BF vs Brennan-Scotto):** treatment interaction berbeda → decision.

## 11. Unit Test dan Integration Test

- **Unit (pure math):** asset-level contribution (konservasi ΣC=R), Brinson-Fachler allocation/selection/interaction pada contoh numerik, degenerasi benchmark tunggal.
- **Integration (DB):** run end-to-end portfolio + benchmark seeded → persist `attribution_runs` + `attribution_results`; determinism.
- **Regression:** BF dengan benchmark tunggal → warning/flag (bukan crash).

## 12. Acceptance Criteria

1. Asset-level attribution: `Σ contribution == R_portfolio` (konservasi, toleransi FP).
2. Active return vs benchmark di-report.
3. Brinson-Fachler (Phase 2): allocation + selection + interaction di-report; `Σ BF == R_p − R_b`.
4. Benchmark + klasifikasi + periode sesuai keputusan owner.
5. Benchmark tunggal + BF → warning eksplisit.
6. Data insufficient → `INSUFFICIENT_DATA`.
7. Determinism: 2 run sama = hasil sama.

## 13. Tahapan Implementasi

1. **Spec final** → `specifications/engines/attribution-engine-spec.md`.
2. **Model + migration** (`attribution_runs`, `attribution_results`).
3. **Engine deterministik** (asset-level Phase 1; Brinson-Fachler Phase 2).
4. **API** (`/attribution/runs`).
5. **Test** (§11).
6. **Phase 2** BF — HANYA setelah benchmark + klasifikasi di-approve.

## 14. Keputusan yang Membutuhkan Product Owner Approval

| # | Keputusan | Opsi |
|---|---|---|
| 1 | Phase 1 = asset-level | **saran: approve** |
| 2 | Benchmark choice | index multi-asset / single asset / custom — **butuh pilihan** |
| 3 | Klasifikasi aset | pakai `market` (3 kelas) / klasifikasi lebih detail — **butuh pilihan** |
| 4 | Periode attribution | harian / mingguan / kustom — **butuh pilihan** |
| 5 | Brinson-Fachler variant | BF (split interaction) / Brennan-Scotto (merge ke allocation) — **butuh pilihan** |
| 6 | Return-based (C) | deferred — **saran: approve** |
