# M4 Gap Proposal — Scenario Analysis Engine

**Status:** PROPOSED (menunggu approval metodologi Product Owner).
**Priority:** #4 dari 4 engine M4 (owner decision).
**Aturan:** Kode TIDAK dimulai sebelum metodologi di-approve.

---

## 1. Tujuan dan Scope

Scenario analysis engine mengevaluasi ketahanan portfolio terhadap kondisi pasar yang berbeda: "apa yang terjadi pada portfolio kalau skenario X terjadi?"

**In-scope:**
- Sensitivity analysis (single-asset / single-factor perturbasi).
- Historical stress scenarios (replay peristiwa historis ke holdings sekarang).
- Hypothetical shocks (user-defined atau percentile-based).
- Propagasi shock via **correlation matrix (M1)**.

**Out-of-scope (fase ini):**
- Monte Carlo sampling probabilistik (butuh distribusi return — decision).
- Stress test otomatis dari news/macro (deferred).

## 2. Metodologi Alternatif yang Relevan

| Opsi | Deskripsi | Feasibility PIMS |
|---|---|---|
| **A. Sensitivity analysis** | Perturbasi 1 asset/factor → perubahan portfolio (delta VaR/return) | ✅ Feasible (correlation + holdings) |
| **B. Historical stress scenarios** | Replay periode historis (2020 crash, 2022 crypto winter) ke holdings sekarang | ✅ Feasible (candle historis + correlation) |
| **C. Hypothetical shocks** | Shock user-defined / percentile (mis. −30% crypto, +200bp rate) | ✅ Feasible tapi **magnitude/probabilitas = decision owner** |

## 3. Rekomendasi Metodologi + Alasan

**Rekomendasi: A + B dulu, C gated.**

- **Phase 1:** Sensitivity (A) + Historical stress (B). Keduanya pakai data yang **sudah ada** (correlation M1 + candle historis + holdings). Deterministik, tak butuh asumsi baru.
- **Phase 2:** Hypothetical shocks (C) — **magnitude + probabilitas shock harus di-approve owner** (aturan: "jangan tetapkan shock magnitude/probabilitas tanpa metodologi disetujui").
- **Alasan:** A/B grounded ke data nyata; C butuh keputusan asumsi yang tak boleh diarang.

> ⚠️ **Flag untuk approval:** daftar historical scenarios mana, magnitude hypothetical shock, probabilitas, distribusi return (jika Monte Carlo) — semua §14.

## 4. Formula dan Definisi Metrik *(PROPOSED — perlu approval)*

Dengan `w` = weight portfolio, `r_i` = return asset, `Σ` = correlation/covariance matrix (M1):

- **Sensitivity (single-asset):** `ΔR_portfolio ≈ Σ_j w_j · ρ_{j,i} · σ_j · shock_i` (propagasi korelasi). Atau eksak: set `r_i += shock_i`, hitung ulang `Σ w_j r_j`.
- **Historical stress:** ambil return asset pada periode historis `T` → `R_stress = Σ_j w_j · r_{j,T}`.
- **Hypothetical shock:** set `r_i = shock_i` untuk asset target → `R_shock = Σ w_j r_j` (direct + correlated via `ρ`).
- **VaR / ES (jika di-approve):** `VaR_α = −(quantile_α(R_portfolio))`; `ES_α = −E[R | R ≤ VaR_α]`.

> ⚠️ **Flag:** formula VaR/ES + distribusi (normal vs empirical), shock magnitude — approval owner §14.

## 5. Data Input dan Sumbernya

| Input | Sumber PIMS | Ketersediaan |
|---|---|---|
| Holding weight | `portfolio` service | ✅ Ada |
| Correlation matrix | `correlation` engine (M1) | ✅ Ada |
| Return historis (stress) | `MarketCandle` | ✅ Ada |
| Shock magnitude/probabilitas | Konfigurasi | ⚠️ Decision owner |
| Daftar skenario historis | Konfigurasi | ⚠️ Decision owner |

## 6. Data Availability dan Kualitas

- **Sensitivity + historical:** feasible — correlation (M1) + candle ada.
- **Hypothetical:** butuh asumsi shock (bukan data) → decision.
- **Keterbatasan:** correlation matrix terbatas pada asset yang punya data korelasi; shock pada asset tak-ter-korelasi = isolasi (flag).

## 7. Dependency terhadap Engine Lain

- `correlation` (M1) — **wajib** (propagasi shock).
- `portfolio` (weight) — wajib.
- `risk` (opsional, untuk VaR/ES) — opsional.

## 8. Database Schema yang Dibutuhkan *(PROPOSED)*

| Tabel | Kolom kunci |
|---|---|
| `scenario_runs` | `id`, `portfolio_id` FK, `scenario_type` (SENSITIVITY/HISTORICAL/HYPOTHETICAL), `params` (JSONB), `created_at` |
| `scenario_results` | `id`, `run_id` FK, `asset_id` FK, `shock` (numeric), `impact` (numeric), `correlated_impact` (numeric), `created_at` |

> ⚠️ Schema **proposed**. Finalisasi setelah approval.

## 9. API dan Output Contract *(PROPOSED)*

`POST /api/v1/scenario/runs`
- Request: `{ portfolio_id, type: "SENSITIVITY"|"HISTORICAL"|"HYPOTHETICAL", asset_id?, shock?, historical_period?, benchmark? }`
- Response: `{ run_id, status, portfolio_impact, per_asset: [{symbol, shock, impact, correlated}], summary }`

`GET /api/v1/scenario/runs/{run_id}`.

Status: `COMPLETED` / `INSUFFICIENT_DATA` / `INVALID_CONFIG` (shock tanpa approval → `INVALID_CONFIG`).

> ⚠️ Kontrak **proposed**.

## 10. Risiko Metodologi dan Keterbatasan

- **Shock asumsi:** hypothetical shock tanpa approval = hasil misleading (aturan brief).
- **Korelasi statis:** M1 correlation = snapshot; shock jangka pendek bisa beda korelasi (regime) → flag.
- **Historical ≠ future:** replay historis bukan prediksi; flag keterbatasan.
- **VaR/ES distribusi:** normal vs empirical → decision (jika di-include).

## 11. Unit Test dan Integration Test

- **Unit (pure math):** sensitivity propagasi korelasi (contoh numerik), historical replay, hypothetical shock eksak, VaR/ES pada series sintetis.
- **Integration (DB):** run end-to-end portfolio + correlation seeded → persist `scenario_runs` + `scenario_results`; determinism.
- **Regression:** hypothetical shock tanpa approval → `INVALID_CONFIG`.

## 12. Acceptance Criteria

1. Sensitivity: perturbasi 1 asset → impact portfolio dihitung via correlation (M1).
2. Historical stress: replay periode historis → impact dilaporkan.
3. Hypothetical: HANYA jalan dengan shock magnitude yang sudah di-approve owner.
4. Correlated impact dihitung (bukan hanya direct).
5. Data insufficient / shock tak-ter-korelasi → flag jelas.
6. Determinism: 2 run sama = hasil sama.

## 13. Tahapan Implementasi

1. **Spec final** → `specifications/engines/scenario-engine-spec.md`.
2. **Model + migration** (`scenario_runs`, `scenario_results`).
3. **Engine deterministik** (sensitivity + historical, pakai correlation M1).
4. **API** (`/scenario/runs`).
5. **Test** (§11).
6. **Phase 2** hypothetical shock — HANYA setelah magnitude/probabilitas di-approve.

## 14. Keputusan yang Membutuhkan Product Owner Approval

| # | Keputusan | Opsi |
|---|---|---|
| 1 | Phase 1 = sensitivity + historical | **saran: approve** |
| 2 | Daftar historical scenarios | 2020-03, 2022-crypto, 2008 (jika ada data) — **butuh pilihan** |
| 3 | Magnitude hypothetical shock | −30% crypto / +200bp rate / dsb — **butuh approval (jangan diarang)** |
| 4 | Probabilitas shock | (jika di-include) — **butuh approval** |
| 5 | VaR/ES (normal vs empirical) | **butuh pilihan** |
| 6 | Treatment asset tak-ter-korelasi | isolasi + flag — **saran: approve** |
