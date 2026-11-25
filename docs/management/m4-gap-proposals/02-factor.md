# M4 Gap Proposal — Factor Engine

**Status:** PROPOSED (menunggu approval metodologi Product Owner).
**Priority:** #2 dari 4 engine M4 (owner decision).
**Aturan:** Kode TIDAK dimulai sebelum metodologi di-approve.

---

## 1. Tujuan dan Scope

Factor engine mengkuantifikasi exposure suatu asset/portfolio terhadap factor-faktor return yang dikenal, menghasilkan **factor score** per asset yang bisa dipakai untuk ranking, diversifikasi, atau input strategi.

**In-scope:**
- Factor model berbasis **market data** (komputable dari `MarketCandle`): momentum, volatility, size (liability proxy via quote volume), reversal.
- Factor universe + normalization + weighting + rebalance + missing-data policy.
- Output: factor score per asset + factor exposure per portfolio.

**Out-of-scope (fase ini):**
- **Fundamental-based factor** (value/quality/ROE) — **BLOCKED**, tak ada data fundamental di PIMS (owner deferred Fundamental Data Provider).
- Factor model multi-aset dengan cross-asset covariance lengkap (fase lanjutan).

> ⚠️ **Pemisahan wajib (owner):** MARKET-BASED factor (feasible now) vs FUNDAMENTAL-BASED factor (deferred, butuh data). Proposal ini fokus MARKET-BASED.

## 2. Metodologi Alternatif yang Relevan

| Opsi | Deskripsi | Feasibility PIMS |
|---|---|---|
| **A. Market-based factor model** | Momentum (N-periode return), volatility (std return), reversal (short-term return negatif), size proxy (log quote volume) — semua dari candle | ✅ Feasible (data ada) |
| **B. Fundamental factor model** | Value (P/E, P/B), quality (ROE), growth (revenue) | ❌ Blocked (tak ada data fundamental) |
| **C. Hybrid (market now, fundamental later)** | A sekarang; B ditambahkan saat fundamental engine + data provider approved | ✅ Recommended |

## 3. Rekomendasi Metodologi + Alasan

**Rekomendasi: Opsi C — market-based FIRST, fundamental deferred.**

- **Phase 1:** Opsi A (market-based factor). Komputable 100% dari `MarketCandle`; deterministik; tak butuh provider eksternal.
- **Phase 2 (deferred):** fundamental factor ditambahkan **setelah** Fundamental Engine + Fundamental Data Provider di-approve (owner decision §A.5).
- **Alasan:** owner eksplisit memisahkan market-based vs fundamental-based + melarang mengasumsikan fundamental tersedia. Market-based adalah satu-satunya yang bisa di-ground ke data PIMS hari ini.

> ⚠️ **Flag untuk approval:** set factor mana (momentum/vol/reversal/size), lookback per factor, normalization (z-score vs rank vs winsorize), weighting (equal vs factor-score), rebalance frequency, missing-data policy — semua §14.

## 4. Formula dan Definisi Metrik *(PROPOSED — perlu approval)*

Per asset, di factor universe, pada waktu `t`:

- **Momentum (N-month):** `mom_i = return_{t-N→t} − return_{t−gap→t−gap}` (skip terakhir `gap` periode; lookback `N`, gap `G`).
- **Reversal:** `rev_i = −return_{short}` (short = 1 periode; inverse momentum jangka pendek).
- **Volatility:** `vol_i = std(returns over M perodes)` (M = lookback vol).
- **Size proxy:** `size_i = log(quote_volume_24h_i)` (proxy likuiditas; bukan market-cap P2P karena tak ada market-cap data).
- **Normalization (per factor, per rebalance date):** `z_i = (raw_i − mean) / std` **atau** rank-percentile `rank_i = rank(raw_i) / n`.
- **Factor score (composite):** `score_i = Σ_k w_k · z_{k,i}` (default equal-weight `w_k = 1/K`; atau inverse-var).
- **Portfolio factor exposure:** `exp_k = Σ_i (wgt_i · z_{k,i})` (weight = posisi portfolio).

> ⚠️ **Flag:** lookback N/G/M, set factor, normalization scheme, weighting, rebalance frequency — approval owner §14.

## 5. Data Input dan Sumbernya

| Input | Sumber PIMS | Ketersediaan |
|---|---|---|
| Return per periode | `MarketCandle` (close) | ✅ Ada |
| Quote volume (size proxy) | `MarketCandle.quote_volume` | ✅ Ada |
| Volatility | `MarketCandle` close series | ✅ Ada |
| Fundamental metrik | — | ❌ Tak ada (deferred) |
| Holding weight (portfolio exposure) | `portfolio` service | ✅ Ada |

## 6. Data Availability dan Kualitas

- **Market-based:** feasible — semua dari candle `CLOSED`. Butuh minimal lookback candles per asset (validasi).
- **Fundamental-based:** **blocked** — tak ada table fundamental. Tidak di-compute sampai data tersedia.
- **Keterbatasan:** size proxy = quote volume (likuiditas), **bukan** market-cap (tak ada data market-cap) → flag keterbatasan metodologi.
- **Missing data:** asset dengan candle kurang dari lookback → di-exclude dari universe (missing-data policy: exclude, bukan impute — default; approval §14).

## 7. Dependency terhadap Engine Lain

- `portfolio` (weight untuk portfolio exposure) — wajib.
- `technical` (opsional, jika mau pakai indicator sebagai factor) — tidak wajib.
- `correlation` (M1) — opsional untuk diversifikasi check.
- `fundamental` engine (Phase 2) — **blocked** sampai engine + data provider approved.

## 8. Database Schema yang Dibutuhkan *(PROPOSED)*

| Tabel | Kolom kunci |
|---|---|
| `factor_runs` | `id`, `universe_size`, `rebalance_date`, `factors` (JSONB list), `weighting`, `created_at` |
| `factor_scores` | `id`, `run_id` FK, `asset_id` FK, `raw` (JSONB per factor), `z` (JSONB per factor), `score` (numeric), `created_at` |
| `factor_portfolio_exposure` | `id`, `run_id` FK, `portfolio_id` FK, `exposure` (JSONB per factor) |

> ⚠️ Schema **proposed** (pola `correlation_results`). Finalisasi setelah approval.

## 9. API dan Output Contract *(PROPOSED)*

`POST /api/v1/factor/runs`
- Request: `{ factors: ["MOMENTUM","VOLATILITY","REVERSAL","SIZE"], lookback, timeframe, universe_asset_ids?, normalization?, weighting?, portfolio_id? }`
- Response: `{ run_id, status, scores: [{symbol, score, factor_z}], portfolio_exposure?, universe_size, exclusions }`

`GET /api/v1/factor/runs/{run_id}` → detail.

Status: `COMPLETED` / `INSUFFICIENT_DATA` / `INVALID_CONFIG`.

> ⚠️ Kontrak **proposed** — ikuti `api-spec.md`.

## 10. Risiko Metodologi dan Keterbatasan

- **Factor timing:** factor value berubah saat rebalance → backtest factor butuh walk-forward (lihat Backtesting).
- **Size proxy bukan market-cap:** keterbatasan data; flag eksplisit.
- **Missing data:** exclude policy bisa menggeser universe antar periode → konsistensi universe perlu documented.
- **Fundamental factor absen:** engine tidak lengkap sampai Phase 2 (by-design, owner deferred).
- **Overfit set factor:** banyak factor + weight → overfit. Mitigasi: set factor dibatasi + out-of-sample.

## 11. Unit Test dan Integration Test

- **Unit (pure math):** momentum/reversal/vol/size pada series sintetis; z-score vs rank; composite score equal-weight; missing-data exclusion.
- **Integration (DB):** run end-to-end pada universe seeded → persist `factor_runs` + `factor_scores`; portfolio exposure; determinism.
- **Regression:** fundamental factor **tidak** muncul sebelum Phase 2 (guard).

## 12. Acceptance Criteria

1. Market-based factor (momentum/vol/reversal/size) dihitung deterministik dari candle `CLOSED`.
2. Factor universe + missing-data policy (exclude) di-apply; universe size dilaporkan.
3. Normalization + weighting sesuai keputusan (z-score / rank / equal).
4. Portfolio factor exposure dihitung dari `portfolio` weight.
5. Fundamental factor **tidak** di-compute (blocked) — tak ada code path palsu.
6. Lookback candles minimum di-validasi (insufficient → `INSUFFICIENT_DATA`).
7. Output persist + di-report per factor (transparansi).
8. Determinism: 2 run sama = hasil sama.

## 13. Tahapan Implementasi

1. **Spec final** → `specifications/engines/factor-engine-spec.md`.
2. **Model + migration** (`factor_runs`, `factor_scores`, `factor_portfolio_exposure`).
3. **Engine deterministik** (market-based factor + normalization + composite).
4. **API** (`/factor/runs`).
5. **Test** (§11).
6. **Phase 2** fundamental factor — HANYA setelah Fundamental Engine + data provider di-approve.

## 14. Keputusan yang Membutuhkan Product Owner Approval

| # | Keputusan | Opsi |
|---|---|---|
| 1 | Phase 1 = market-based only | **saran: approve** |
| 2 | Set factor | momentum/vol/reversal/size — **saran: approve** |
| 3 | Lookback (N/G/M) | mom 120/20, rev 5, vol 20, size 1 (24h) — **saran: approve** |
| 4 | Normalization | z-score (default) / rank / winsorize — **butuh pilihan** |
| 5 | Weighting | equal (default) / inverse-var — **butuh pilihan** |
| 6 | Rebalance frequency | harian / mingguan — **butuh pilihan** |
| 7 | Missing-data policy | exclude (default) / impute — **butuh pilihan** |
| 8 | Fundamental factor (Phase 2) | tunda sampai Fundamental Engine approved — **saran: approve** |
