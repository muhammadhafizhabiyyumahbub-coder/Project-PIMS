# M4 Gap Proposal — Backtesting Engine

**Status:** PROPOSED (menunggu approval metodologi Product Owner).
**Priority:** #1 dari 4 engine M4 (owner decision).
**Aturan:** Kode TIDAK dimulai sebelum metodologi di-approve (brief GPT #3 §C/F).

---

## 1. Tujuan dan Scope

Backtesting engine mengevaluasi kinerja strategi investasi terhadap data historis PIMS (`MarketCandle`) untuk menjawab: "apakah strategi ini menghasilkan return/risk yang acceptable, dan seberapa reliable estimasinya?"

**In-scope:**
- Strategi berbasis sinyal engine yang sudah ada (technical, scanner) + strategi buy-and-hold / static-weight.
- Perhitungan return, drawdown, Sharpe, win-rate, turnover.
- Biaya transaksi + slippage (model deterministik).
- Look-ahead bias prevention + survivorship bias consideration.
- Out-of-sample + walk-forward validation.
- Benchmark comparison.
- Reproducibility (deterministic, frozen inputs, versioned config).

**Out-of-scope (fase ini):**
- Optimizer portfolio (itu Allocation Engine).
- Corporate actions kompleks (dividend reinvest, split, rights issue) — cukup flag + penanganan sederhana.
- Multi-asset live simulation (uni-user, historis saja).

## 2. Metodologi Alternatif yang Relevan

| Opsi | Deskripsi | Kelebihan | Kekurangan |
|---|---|---|---|
| **A. Buy-and-hold / static-weight** | Hold konstan sejak start, reweight periodik (fixed schedule) | Paling sederhana, baseline untuk semua strategi, tak butuh sinyal | Kurang informatif untuk strategi aktif |
| **B. Rule-based strategy backtest** | Sinyal dari technical/scanner engine → entry/exit rules | Memanfaatkan engine yang sudah ada, realistis untuk user | Butuh definisi aturan + backtest rules (metodologi decision) |
| **C. Allocation-strategy backtest** | Rebalance ke target weight Allocation Engine tiap periode | Terintegrasi dengan Allocation, realistis untuk portfolio | Ganda dengan Allocation engine; tergantung metodologi allocation |

## 3. Rekomendasi Metodologi + Alasan

**Rekomendasi: phased A → B (C ditunda).**

- **Phase 1 (feasible sekarang):** Opsi A — buy-and-hold + static-weight rebalance. Ini **baseline wajib** untuk semua engine lain (benchmark internal) dan sepenuhnya bisa dihitung dari `MarketCandle` + `portfolio` holdings. Deterministik, tak butuh sinyal.
- **Phase 2 (setelah Phase 1 approved + berjalan):** Opsi B — rule-based, sinyal dari technical/scanner. Butuh definisi aturan entry/exit (metodologi decision → approval owner).
- **Opsi C ditunda** — tumpang-tindih dengan Allocation Engine; implement setelah Allocation metodologi di-approve.

**Alasan:** PIMS sudah punya `MarketCandle` (OHLCV 1h/1d) + `portfolio` holdings + technical/scanner signals. Opsi A bisa langsung di-ground ke data yang ada tanpa asumsi baru. Opsi B menambah nilai tapi butuh aturan yang harus di-approve dulu.

> ⚠️ **Flag untuk approval:** Rekomendasi A→B, parameter rebalance, definisi aturan entry/exit (B), biaya model — semua menunggu approval owner (§14).

## 4. Formula dan Definisi Metrik *(PROPOSED — perlu approval)*

Untuk strategi dengan posisi weight `w_t` pada periode `t`:

- **Return strategi:** `R_t = Σ_i w_{i,t-1} · r_{i,t}` (mark-to-market, weight awal periode).
- **Cumulative return:** `Π_t (1 + R_t) − 1`.
- **Annualized return (geometric):** `(1 + cumR)^(1/n_years) − 1`.
- **Volatility:** `σ = std(R_t) · √√(annualizing factor)`.
- **Sharpe ratio:** `(annualReturn − rf) / σ`. `rf` = risk-free rate (decision: sumber `rf`, default 0 untuk crypto/uni-user).
- **Max drawdown:** `max_t (peak_t − R_t)` atas equity curve.
- **Calmar:** `annualReturn / maxDrawdown`.
- **Win rate:** `count(R_t > 0) / count(R_t)`.
- **Turnover:** `Σ_t Σ_i |Δw_{i,t}|` (menggerakkan biaya).
- **Cost-adjusted return:** kurangi `turnover · (fee_bps + slippage_bps)` dari return kotor.

> ⚠️ Formula di atas **proposed**. Owner harus approve: set metrik mana yang wajib, value `rf`, annualizing factor (1h→1d→1y), cost model (bps fee + bps slippage).

## 5. Data Input dan Sumbernya

| Input | Sumber PIMS | Ketersediaan |
|---|---|---|
| OHLCV historis | `MarketCandle` (per asset, per provider, timeframe 1h/1d) | ✅ Ada (CLOSED candles) |
| Holding weight | `portfolio` service (holdings) | ✅ Ada |
| Sinyal (opsional, B) | `technical` + `scanner` engines | ✅ Ada |
| Cost model | Konfigurasi (fee bps, slippage bps) | ⚠️ Perlu decision (default: fee 10bps + slippage 5bps, APPROVE) |
| Risk-free rate | Konfigurasi | ⚠️ Perlu decision (default 0, APPROVE) |
| Benchmark | Konfigurasi per asset class | ⚠️ Perlu decision (default: equal-weight universe atau BTC, APPROVE) |

## 6. Data Availability dan Kualitas

- **Ada:** `MarketCandle` untuk CRYPTO/US/IDX via YAHOO/BYBIT. Data freshness + status `CLOSED` sudah di-validasi scanner.
- **Keterbatasan:**
  - Data historis **begitu adanya** di DB — engine tidak fetch baru (deterministik, offline).
  - Survivorship: universe saat ini = active assets. Asset yang sudah delist/merge **tidak** di-candle DB → survivorship bias **tidak bisa** di-correct tanpa data historis lengkap (flag: limitation, bukan bug).
  - Look-ahead: candle `CLOSED` saja; tak boleh pakai `UNCLOSED` candle di periode backtest.
  - Cost model + `rf` adalah **asumsi** (bukan data) → perlu approval.

## 7. Dependency terhadap Engine Lain

- `portfolio` (holding weight + valuation) — wajib.
- `technical` + `scanner` (sinyal) — hanya untuk Opsi B (Phase 2).
- `correlation` (M1) — opsional, untuk risk metrics kombinasi.
- `risk` — opsional, untuk VaR/ES output backtest.

## 8. Database Schema yang Dibutuhkan *(PROPOSED)*

| Tabel | Kolom kunci | Catatan |
|---|---|---|
| `backtest_runs` | `id`, `strategy_name`, `strategy_config` (JSONB, versioned), `start_ts`, `end_ts`, `timeframe`, `cost_model` (JSONB), `benchmark`, `created_at` | Satu run = satu konfigurasi + periode |
| `backtest_metrics` | `id`, `run_id` FK, `metric` (key), `value` (numeric), `detail` (JSONB) | Long format: satu baris per metrik |
| `backtest_trades` | `id`, `run_id` FK, `ts`, `asset_id`, `side`, `weight_change`, `cost`, `price` | Untuk audit + turnover |

> ⚠️ Schema **proposed** — mengikuti pola `correlation_results` (§7.5 schema-spec). Finalisasi setelah metodologi di-approve.

## 9. API dan Output Contract *(PROPOSED)*

`POST /api/v1/backtest/runs`
- Request: `{ strategy: "BUY_HOLD"|"STATIC_WEIGHT"|"RULE_BASED", timeframe, start, end, asset_ids?, weights?, cost_model?, benchmark? }`
- Response: `{ run_id, status, metrics: {cum_return, annual_return, sharpe, max_dd, win_rate, turnover, cost_adjusted}, trades_count, benchmark_comparison }`

`GET /api/v1/backtest/runs/{run_id}` → detail + metrics + equity curve (sampling).
`GET /api/v1/backtest/runs/{run_id}/trades` → paginasi trade log.

Status: `COMPLETED` / `FAILED` (data insufficient) / `INVALID_CONFIG`.

> ⚠️ Kontrak **proposed** — ikuti konvensi `api-spec.md`. Finalisasi setelah approval.

## 10. Risiko Metodologi dan Keterbatasan

- **Look-ahead bias:** mitigasi = hanya `CLOSED` candle ≤ decision timestamp; engine menolak `UNCLOSED` di jendela backtest.
- **Survivorship bias:** universe aktif saja; limitation eksplisit di output (flag, tak di-correct).
- **Cost/slippage asumsi:** jika asumsi salah, return over/under-estimated. Mitigasi: cost model configurable + di-report terpisah dari return kotor.
- **Overfitting aturan (B):** banyak aturan → overfit. Mitigasi: walk-forward + out-of-sample, jumlah aturan dibatasi.
- **Kualitas data historis:** gap candle, stale data → metrik tidak reliable. Mitigasi: validasi data availability di awal run (minimal candles per asset).

## 11. Unit Test dan Integration Test

- **Unit (pure math):** buy-and-hold return (1 asset), static-weight (2 asset, rebalance), cost subtraction, Sharpe/drawdown pada series sintetis, look-ahead guard (tolak `UNCLOSED`).
- **Integration (DB):** run end-to-end pada candle seeded → persist `backtest_runs` + `backtest_metrics` + `backtest_trades`; benchmark comparison; determinism (2 run identik = hasil identik).
- **Regression:** Opsi B (setelah approved) — sinyal scanner/technical menghasilkan trade sesuai aturan.

## 12. Acceptance Criteria

1. Buy-and-hold + static-weight backtest menghasilkan metrik deterministik (2 run sama = hasil sama).
2. Look-ahead bias: run menolak/mengabaikan `UNCLOSED` candle di jendela backtest.
3. Cost model: return bersih = return kotor − (turnover × cost); di-report terpisah.
4. Survivorship bias: dilaporkan sebagai limitation, bukan di-silence.
5. Walk-forward: data di-split in-sample/out-of-sample; metrik out-of-sample dilaporkan.
6. Benchmark comparison: metrik strategi vs benchmark (excess return, tracking).
7. Reproducibility: `strategy_config` versioned + frozen inputs; run dapat di-replay.
8. Data insufficient → status `FAILED` dengan alasan jelas, bukan crash.
9. Semua metrik di §4 dihitung + dipersist.
10. Opsi B (rule-based) hanya diimplement setelah aturan di-approve.

## 13. Tahapan Implementasi

1. **Spec final** (dari proposal ini + approval owner) → `specifications/engines/backtesting-engine-spec.md`.
2. **Model + migration** (`backtest_runs`, `backtest_metrics`, `backtest_trades`).
3. **Engine deterministik** (pure math: return, cost, metrics; look-ahead guard).
4. **API** (`/backtest/runs` POST + GET).
5. **Test** (unit + integration, sesuai §11).
6. **Phase 2** (Opsi B rule-based) — HANYA setelah aturan entry/exit di-approve.

> Kode dimulai **setelah** item 1 (spec final + approval metodologi).

## 14. Keputusan yang Membutuhkan Product Owner Approval

| # | Keputusan | Opsi |
|---|---|---|
| 1 | Strategi phase 1 | A (buy-and-hold + static-weight) — **saran: approve** |
| 2 | Aturan entry/exit (B) | definisi rules — **butuh approval sebelum Phase 2** |
| 3 | Cost model (fee bps, slippage bps) | default fee 10 + slippage 5 — **saran: approve** |
| 4 | Risk-free rate | default 0 — **saran: approve** |
| 5 | Benchmark | equal-weight universe / BTC / custom — **butuh pilihan** |
| 6 | Annualizing factor + set metrik wajib | Sharpe/Calmar/drawdown/win-rate — **saran: approve** |
| 7 | Walk-forward split (in/out ratio) | 70/30 — **saran: approve** |
| 8 | Treatment corporate actions | flag + skip (tanpa reinvest) — **saran: approve** |
