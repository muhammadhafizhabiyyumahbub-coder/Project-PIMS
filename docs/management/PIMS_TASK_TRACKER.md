# PIMS Task Tracker — Fase 2
**Dibuat:** 2026-11-28 · Galih subagent
**Repo:** `D:/personal-investment-management-system` · branch `master`

## Status Legend
- `SEDANG DIKERJAKAN` — in-progress, aktif
- `PENDING` — menunggu task upstream selesai
- `GATED` — butuh keputusan owner (§26)
- `SELESAI` — done + test lulus
- `DEFERRED` — owner tunda

## Task Tracker

| ID | Task | Pemilik | Status | Tenggat | Dependensi |
|----|------|---------|--------|---------|------------|
| T1 | Macro engine (FRED API) | Raka (Tara: data, Sakti: QA) | SEDANG DIKERJAKAN | 2026-11-28 EOD | FRED key di .env (ada) |
| T2 | Backtest Phase 2 (rule-based) | Raka | PENDING | 2026-11-29 | T1 selesai |
| T3 | Scenario hypothetical | Raka | GATED §26 | 2026-11-30 | T2 selesai + approval owner |
| T4 | Watchlist (2 tabel: watchlists + watchlist_items) | Raka | PENDING | 2026-11-29 | skema decided, tak butuh approval |
| T5 | Fundamental Phase 2 | Raka | PENDING | 2026-11-30 | T1 selesai (data provider) |
| T6 | Scheduler analitis (auto-run) | Raka | PENDING (fleksibel) | TBD | T1–T5 selesai |
| T7 | Beta + benchmark + HHI | Raka | PENDING (fleksibel) | TBD | T1 selesai |
| T8 | 9 endpoint gap spec (7 watchlists + PATCH/DELETE transaksi) | Raka | DEFERRED (owner decision) | TBD | keputusan owner |
| QA | QA suite penuh (target 355 passed / 0 failed) | Sakti | SEDANG BERJALAN | paralel T1–T5 | T1–T5 commit |
| DOCS | Dokumentasi + README update | Laras | PENDING | setelah QA lulus | QA selesai |
| GIT | commit + push (SSH, tiap tahap) | Galih subagent | PENDING | setelah DOCS | DOCS selesai |

## Bottleneck & Risiko

| Bottleneck | Dampak | Mitigasi |
|------------|--------|----------|
| T1 (Macro) belum selesai | T2, T5, T7 terblokir | Raka fokus T1; Tara siapkan dataset FRED paralel |
| QA (Sakti) paralel dengan T1–T5 | potensi konflik DB test (`pims_test`) | aturan §7: jangan jalankan pytest bersamaan dengan OpenCode |
| T3 GATED §26 | scenario hypothetical tak bisa mulai | tunggu approval owner |
| T8 owner decision | 9 endpoint gap tetap terbuka | owner putuskan: implementasi atau tunda |

## Catatan Galih subagent
- T1 SEDANG DIKERJAKAN Raka — jangan klaim selesai sebelum commit + test lulus.
- T4 (Watchlist) tak butuh approval — skema 2 tabel sudah decided di `technical-decisions`.
- Jangan push, jangan ubah `.env`.
- Semua klaim file wajib bukti `git status --short`.
