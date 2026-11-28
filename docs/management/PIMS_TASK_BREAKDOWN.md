# PIMS Task Breakdown — Fase 2 (Lanjutan)

**Disusun:** Nolan (Project Director) + Galih (Manajer Tugas)
**Tanggal:** 2026-11-28
**Status PIMS V1:** Release Candidate (belum dirilis) — M4 7/7 engine selesai
**Gap:** 1 test gagal (fixed d13995c), 3 fitur tertunda

## Gap dari perencanaan awal

| # | Item | Status | Prioritas | Pemilik |
|---|---|---|---|---|
| T1 | Macro engine (FRED API) | TUNDA (butuh key) | P1 | Raka |
| T2 | Backtest Phase 2 (rule-based) | GATED §26 | P2 | Raka |
| T3 | Scenario hypothetical | GATED §26 | P2 | Raka |
| T4 | Watchlist (2 tabel) | DEFERRED | P2 | Raka |
| T5 | Fundamental Phase 2 | belum | P3 | Raka |
| T6 | Scheduler analitis | manual | P3 | Raka |
| T7 | Beta + benchmark + HHI | belum | P3 | Raka |
| T8 | 9 endpoint gap spec | by-design | P3 | Raka |

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

| Fase | Durasi | Output |
|---|---|---|
| Audit + breakdown | 30 mnt | doc ini + LOC report |
| Macro engine (T1) | 1-2 jam | engine + test + endpoint |
| Backtest P2 (T2) | 1-2 jam | rule-based engine |
| Watchlist (T4) | 1 jam | tabel + CRUD |
| QA + docs | 30 mnt | test lulus + README |
| Obsidian + push | 30 mnt | vault PIMS + git |
