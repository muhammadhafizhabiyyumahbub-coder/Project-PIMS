# M4 Gap Proposals — INDEX

**Status:** PROPOSED (menunggu review + approval Product Owner).
**Aturan (brief GPT #3):** proposal = bahan review, **bukan** izin implementasi. Kode engine baru dimulai HANYA setelah metodologi engine terkait di-approve.
**Format:** Option B (owner choice) — technical gap proposal + acceptance criteria, 14 section per proposal.

## Priority (owner decision)

| Prioritas | Engine | File | Status Implementasi |
|---|---|---|---|
| 1 | Backtesting | `01-backtesting.md` | Ready-after-approval (Phase 1 feasible now) |
| 2 | Factor | `02-factor.md` | Ready-after-approval (market-based feasible; fundamental deferred) |
| 3 | Attribution | `03-attribution.md` | Ready-after-approval (asset-level feasible; BF needs benchmark) |
| 4 | Scenario | `04-scenario.md` | Ready-after-approval (sensitivity+historical feasible; hypothetical gated) |
| — | Fundamental | `05-fundamental.md` | **DEFERRED** (blocked: no data provider) |
| — | Macro | `06-macro.md` | **DEFERRED** (blocked: no data provider) |
| — | Sentiment | `07-sentiment.md` | **DEFERRED** (blocked: no news provider) |

## Keputusan Kunci per-Engine (ringkasan §14)

### Backtesting
Metode A→B, cost model, risk-free rate, benchmark, walk-forward split, treatment corporate actions.

### Factor
Set factor (momentum/vol/reversal/size), lookback, normalization (z/rank/winsorize), weighting, rebalance, missing-data, fundamental factor deferred.

### Attribution
Benchmark choice, klasifikasi aset, periode, Brinson-Fachler variant (BF vs Brennan-Scotto), return-based deferred.

### Scenario
Daftar historical scenarios, magnitude + probabilitas hypothetical shock, VaR/ES (normal vs empirical), treatment asset tak-ter-korelasi.

### Fundamental (deferred)
Source (Yahoo/manual/berbayar), set metrik, trailing/forward, currency, refresh cadence, missing-value, crypto N/A.

### Macro (deferred)
Source (FRED/manual/berbayar), set indikator, frekuensi, revision policy, lag, regime model.

### Sentiment (deferred)
Sumber (berita/sosial), bahasa, model (LLM gated/lexicon), window + decay, dedup, sosial deferred.

## Prinsip Lintas-Engine

1. **Deterministik:** kalkulasi oleh engine, AI hanya interpretasi (brief P3 + §26.10).
2. **Tanpa mengarang:** formula/metodologi = proposed, menunggu approval.
3. **Data gap jujur:** fundamental/macro/sentiment tak bisa di-ground ke data hari ini → deferred.
4. **§10 data sharing:** payload eksternal sanitized (tanpa PII/posisi/credential).
5. **Pola M1:** spec → model+migration → engine deterministik → API → test.

## Langkah Berikutnya

1. Owner review 7 proposal (terutama §14 keputusan per-engine).
2. Owner approve metodologi engine prioritas (1-4) → Hermes susun spec final.
3. Implementasi engine (1) Backtesting → (2) Factor → (3) Attribution → (4) Scenario, satu per satu, masing-masing dengan test + CI.
4. Engine deferred (5-7) aktif setelah provider data di-approve.
