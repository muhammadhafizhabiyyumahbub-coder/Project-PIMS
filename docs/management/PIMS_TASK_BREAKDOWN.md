# PIMS Task Breakdown — Fase 2 (Lanjutan)

**Disusun:** Nolan (Project Director) + Galih (Manajer Tugas)
**Diperbarui:** Galih subagent, 2026-11-28
**Status PIMS V1:** Release Candidate — M4 7/7 engine selesai + CI fix P0 SELESAI
**Test:** 397 passed, 0 failed

## Status Gate P0–P8 (perbarui 2026-11-28)

| Gate | Item | Status | Catatan |
|---|---|---|---|
| P0 | CI fix (fred_fetch httpx) | **SELESAI** | commit `0bd2313`; test lulus |
| P1 | Audit engine (Nadia) | **JALAN** | audit rumus engine + verifikasi angka |
| P2 | — | pending | (P2 scanner sudah SELESAI `7e2f6f4`) |
| P3 | Real integration test | **SELESAI** | live probe 3 market |
| P4 | M4 engine (7 engine + macro + backtest P2) | **SELESAI** | 7 engine: correlation/backtesting/factor/attribution/scenario/fundamental/sentiment + macro FRED; backtest P2 |
| P5–P8 | Roadmap lanjutan | **PENDING** | menunggu P1 audit + P4 |

**Bottleneck saat ini:** P1 audit (Nadia) → kunci P5–P8.
**Dependensi:** P1 → P5–P8; P4 sudah selesai, tak blokir.

## Gap dari perencanaan awal (M4 gap proposals)

| # | Item | Status | Prioritas | Pemilik | Tenggat |
|---|---|---|---|---|---|
| T1 | Macro engine (FRED API) | **SELESAI** (M4) | P4 | Raka/Hermes | — |
| T2 | Backtest Phase 2 (rule-based) | **SELESAI** (M4, gated §26 hypothetical masih pending) | P4 | Raka/Hermes | — |
| T3 | Scenario hypothetical | GATED §26 — pending | P5 | Raka | 2026-12 |
| T4 | Watchlist (2 tabel) | PENDING — skema decided, tak perlu approval | P5 | Raka | 2026-12 |
| T5 | Fundamental Phase 2 | PENDING — blocked data provider | P5 | Raka | 2026-12 |
| T6 | Scheduler analitis | manual, tak urgent | P6 | Raka | fleksibel |
| T7 | Beta + benchmark + HHI | belum mulai | P6 | Raka | fleksibel |
| T8 | 9 endpoint gap spec | by-design, owner decision | P7 | Raka | fleksibel |

**QA keseluruhan:** suite 397 passed / 0 failed (perbarui 2026-11-28).
**P1 audit (Nadia):** jalan — verifikasi rumus engine M4.

## Alur kerja (per task)

1. **Audit codebase** (Nolan, `codebase-inspection` skill) — LOC, modul, status test
2. **Arsitektur** (Bima, OpenCode) — rencana teknis per fitur
3. **Implementasi** (Raka, OpenCode) — kode + test (TDD)
4. **QA** (Sakti, OpenCode) — pytest + verifikasi
5. **Dataset/analisis** (Tara + Damar, subagent Hermes) — data + interpretasi
6. **Audit rumus** (Nadia, subagent) — verifikasi angka engine
7. **Browser/Edge** (Nolan) — live-verify dashboard PIMS
8. **Dokumentasi + git** (Laras, OpenCode) — README, docs, commit
9. **Obsidian** (Nolan + Galih subagent) — vault PIMS + task tracker

## Dependensi

- P4 M4 → 7 engine selesai + macro FRED + backtest P2
- P1 audit → kunci P5–P8
- T3 (Scenario hypothetical) → GATED §26, pending
- T4 (Watchlist) → skema 2 tabel (decided, tak butuh approval)
- T5–T8 → menunggu P1 audit selesai

## Timeline (perkiraan)

| Fase | Durasi | Output | Status saat ini |
|---|---|---|---|
| P0 CI fix | — | commit 0bd2313 | **SELESAI** |
| P1 audit (Nadia) | paralel | verifikasi engine | **JALAN** |
| P4 M4 engine | 1–2 hari | 7 engine + macro + backtest P2 | **SELESAI** |
| P5–P8 | 1–2 minggu | roadmap lanjutan | **PENDING** |
| Docs + push | 30 mnt | README + git | menunggu P5 |
