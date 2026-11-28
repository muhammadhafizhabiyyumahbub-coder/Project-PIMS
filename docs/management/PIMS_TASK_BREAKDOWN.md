# PIMS Task Breakdown — Fase 2 (Lanjutan)

**Disusun:** Nolan (Project Director) + Galih (Manajer Tugas)
**Tanggal:** 2026-11-28
**Status PIMS V1:** Release Candidate (belum dirilis) — M4 7/7 engine selesai
**Gap:** 1 test gagal (fixed d13995c), 3 fitur tertunda

## Gap dari perencanaan awal

| # | Item | Status | Prioritas | Pemilik | Tenggat |
|---|---|---|---|---|---|
| T1 | Macro engine (FRED API) | SEDANG DIKERJAKAN — Raka (Tara: data FRED, Sakti: QA) | P1 | Raka | 2026-11-28 EOD |
| T2 | Backtest Phase 2 (rule-based) | PENDING — gate §26, blokir T1 | P2 | Raka | 2026-11-29 |
| T3 | Scenario hypothetical | GATED §26 — blokir T2 | P2 | Raka | 2026-11-30 |
| T4 | Watchlist (2 tabel) | PENDING — skema decided, tak perlu approval | P2 | Raka | 2026-11-29 |
| T5 | Fundamental Phase 2 | PENDING — blokir T1 (data provider) | P3 | Raka | 2026-11-30 |
| T6 | Scheduler analitis | manual, tak urgent | P3 | Raka | fleksibel |
| T7 | Beta + benchmark + HHI | belum mulai | P3 | Raka | fleksibel |
| T8 | 9 endpoint gap spec | by-design, owner decision | P3 | Raka | fleksibel |

**QA keseluruhan:** Sakti jalan — target suite 355 passed/0 failed.
**Bottleneck:** T1 (Macro) → kunci T2, T3, T5. QA (Sakti) paralel, tak blokir.
**Dependensi:** T1→T2→T3; T1→T5; T4 berdiri sendiri.

## Alur kerja (per task)

1. **Audit codebase** (Nolan, `codebase-inspection` skill) — LOC, modul, status test
2. **Arsitektur** (Bima, OpenCode) — rencana teknis per fitur
3. **Implementasi** (Raka, OpenCode) — kode + test (TDD)
4. **QA** (Sakti, OpenCode) — pytest + verifikasi
5. **Dataset/analisis** (Tara + Damar, subagent Hermes) — data + interpretasi
6. **Audit rumus** (Nadia, subagent) — verifikasi angka engine
7. **Browser/Edge** (Nolan) — live-verify dashboard PIMS
8. **Dokumentasi + git** (Laras, OpenCode) — README, docs, commit
9. **Obsidian** (Nolan) — vault PIMS + write-read test

## Dependensi

- T1 (Macro) → butuh FRED key (sudah ada di .env: PIMS_FRED_API_KEY)
- T2 (Backtest P2) → T1 selesai dulu (macro data untuk benchmark)
- T3 (Scenario) → T2 selesai
- T4 (Watchlist) → skema 2 tabel (decided, tak butuh approval)
- T5-T8 → T1-T4 selesai

## Timeline (perkiraan)

| Fase | Durasi | Output | Status saat ini |
|---|---|---|---|
| Macro engine (T1) | 1–2 jam | engine + test + endpoint | SEDANG DIKERJAKAN (Raka) |
| QA suite (Sakti) | paralel | 355 passed / 0 failed | SEDANG BERJALAN |
| Backtest P2 (T2) | 1–2 jam | rule-based engine | PENDING — blokir T1 |
| Watchlist (T4) | 1 jam | tabel + CRUD | PENDING — standalone |
| Scenario (T3) | 1 jam | hypothetical | GATED §26 — blokir T2 |
| Fundamental P2 (T5) | 1–2 jam | engine | PENDING — blokir T1 |
| Docs + push | 30 mnt | README + git | menunggu T1–T5 |
