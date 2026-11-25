# M4 Gap Proposal — Sentiment Engine *(DEFERRED)*

**Status:** PROPOSED — implementasi **DEFERRED** owner (menunggu data + metodologi approval).
**Priority:** di luar 4 engine M4.
**Aturan:** Kode TIDAK dimulai sebelum data provider + metodologi di-approve. Proposal ini = **gap analysis** untuk review owner.

---

## 1. Tujuan dan Scope

Sentiment engine mengkuantifikasi sentimen pasar dari sumber berita/sosial, untuk mengontekstualkan decision + input AI Research (trigger-based).

**In-scope (setelah approval):**
- Sentimen per asset (berita / sosial).
- Agregasi + windowing + decay.
- Deduplikasi + timestamp + freshness.
- Bahasa (ID / EN / multilingual).

**Kondisi saat ini (HONEST):**
- **Tidak ada** data berita/sosial di PIMS.
- **Tidak ada** News Data Provider (owner deferred §A.4).
- AI Research = trigger-based, **bukan** analisis kontinu (brief P3) → sentimen tidak jalan terus-menerus.
- Engine hanya `__init__.py`.

> ⚠️ **Gap utama:** engine ini **blocked** sampai owner menyetujui (a) sumber data (berita/sosial), (b) scope bahasa, (c) model sentimen, (d) agregasi. Tanpa itu, tak ada yang bisa diimplement.
> ⚠️ **§10 External Data Sharing:** sentimen = data eksternal → terikat aturan sanitasi (tanpa PII/credential/posisi) di decision §26.

## 2. Metodologi Alternatif yang Relevan

| Aspek | Opsi | Tradeoff |
|---|---|---|
| **Sumber** | A. Berita (RSS/news API) vs B. Sosial (X/Twitter) | Berita: reliable, terstruktur. Sosial: real-time, noise tinggi, rate-limit, ToS |
| **Model** | A. Lexicon (VADER/AFINN) vs B. LLM (agnes-3.0-flash) | Lexicon: cepat, deterministik, murah. LLM: lebih akurat, lebih lambat, butuh gating deterministik |
| **Agregasi** | A. Mean per window vs B. Decay-weighted vs C. Per-asset rolling | Decay-weighted lebih responsif; per-asset untuk fokus |

## 3. Rekomendasi Metodologi + Alasan

**Rekomendasi: Berita (A) + Model LLM (B) dengan gating deterministik + Agregasi decay-weighted per-asset.**

- **Berita > Sosial:** sumber lebih reliable, terstruktur, ToS lebih ramah. Sosial noise tinggi + rate-limit → deferred.
- **LLM (agnes-3.0-flash) > Lexicon:** akurat untuk konteks; **tetap** harus di-gate deterministik (AI tak menggantikan perhitungan engine; output sentimen = sinyal, bukan keputusan). Konsisten brief P3 + §10.
- **Decay-weighted:** sentimen fresh lebih penting; window per-asset.
- **Catatan:** sentimen = **input sinyal** untuk AI Research / dashboard, **bukan** trigger trading otomatis.

> ⚠️ **Flag untuk approval:** sumber (berita/sosial), scope bahasa, model (lexicon/LLM), window + decay, dedup — semua §14.

## 4. Formula dan Definisi Metrik *(PROPOSED — perlu approval)*

- **Sentiment score per artikel:** `s ∈ [−1, +1]` (LLM: classify pos/neu/neg → mapping; lexicon: compound VADER).
- **Agregasi decay-weighted per asset, window W:**
  `S_asset = Σ (s_k · λ^(age_k)) / Σ (λ^(age_k))`, `age_k = now − ts_k`, `λ ∈ (0,1)` (decay factor).
- **Freshness:** `fraction of articles within last D days`.
- **Volume:** `count(articles in W)` (context, bukan skor).

> ⚠️ **Flag:** range skor, decay factor `λ`, window `W`, dedup policy — approval owner §14.

## 5. Data Input dan Sumbernya

| Input | Sumber | Ketersediaan |
|---|---|---|
| Artikel berita (headline, body, ts) | **News provider (deferred §A.4)** | ❌ Tak ada |
| Postingan sosial | Sosial API | ❌ Tak ada (deferred) |
| Asset mapping (ticker → entity) | `Asset` | ✅ Ada |
| Sentimen model | LLM `agnes-3.0-flash` / lexicon | ⚠️ LLM ada (provider), lexicon tak ada |

## 6. Data Availability dan Kualitas

- **HONEST:** **0 data sentimen** di PIMS. Tak ada news/social table, tak ada provider.
- **Dedup:** berita sama dari banyak sumber → dedup wajib (policy decision).
- **Timestamp:** freshness sentimen kritis → track `ts`.
- **Bahasa:** sumber campur ID/EN → model harus multilingual (LLM bisa; lexicon per-bahasa).
- **Source reliability:** rating per sumber (decision).
- **§10 restriction:** payload sentimen ke LLM = sanitized headline/summary, **tanpa** PII/posisi/credential.

## 7. Dependency terhadap Engine Lain

- `ai/research` (openai_compat provider, `agnes-3.0-flash`) — untuk model LLM.
- `Asset` (entity mapping).
- **News Data Provider** — **blocked** (owner decision §A.4).
- `scanner` (opsional, sebagai sinyal turunan).

## 8. Database Schema yang Dibutuhkan *(PROPOSED — tidak dibuat sampai approved)*

| Tabel | Kolom kunci |
|---|---|
| `sentiment_articles` | `id`, `asset_id` FK, `source`, `headline`, `published_at`, `dedup_key`, `language`, `created_at` |
| `sentiment_scores` | `id`, `article_id` FK, `score` (numeric −1..1), `model` (key), `model_version`, `aggregated` (bool), `window`, `created_at` |
| `sentiment_aggregates` | `id`, `asset_id` FK, `window`, `score`, `volume`, `freshness`, `as_of`, `created_at` |

> ⚠️ **Owner eksplisit (§A.4): jangan buat migration sentimen sebelum news provider di-approve.** Schema ini hanya PROPOSED.

## 9. API dan Output Contract *(PROPOSED)*

`GET /api/v1/sentiment/summary?asset_id=&window=`
- Response: `{ asset_symbol, score, volume, freshness, top_articles: [{headline, ts, source, score}], window }`

> ⚠️ Kontrak **proposed** — tak diimplement sampai approved.

## 10. Risiko Metodologi dan Keterbatasan

- **Blocked data:** tanpa news provider, engine tak bisa jalan.
- **LLM non-deterministik:** skor LLM bisa berubah antar-call → gate deterministik (cache per dedup_key + model_version) + report model version.
- **Noise (jika sosial):** false signal tinggi → berita lebih aman.
- **Manipulasi:** sentimen bisa dimanipulasi (pump) → hanya sinyal, bukan keputusan (aturan brief).
- **§10 data sharing:** payload ke LLM harus sanitized (tanpa PII/posisi).
- **Provider cost/ToS:** news/sosial API bisa berbayar + ToS ketat → approval owner.

## 11. Unit Test dan Integration Test

- **Unit:** agregasi decay-weighted (contoh numerik), dedup, freshness, range skor, LLM output validation (out-of-range → reject).
- **Integration:** (setelah provider) fetch + persist `sentiment_articles` + `sentiment_scores` + `sentiment_aggregates`; determinism (cache per dedup_key).
- **Regression:** tak ada code path sentimen sebelum approved; payload LLM tak mengandung PII (security test).

## 12. Acceptance Criteria

1. Sentimen dihitung dari sumber yang **sudah disetujui** (bukan dikarang).
2. Agregasi decay-weighted per-asset di-apply.
3. Dedup + timestamp + freshness di-track.
4. Model LLM output di-gate deterministik (range + cache + version).
5. Bahasa sesuai scope (di-approve).
6. Payload ke LLM **sanitized** (tak ada PII/posisi/credential) — konsisten §10.
7. Sentimen = sinyal, **bukan** trigger trading.
8. **Tidak ada** implementation sebelum provider + model + agregasi di-approve.

## 13. Tahapan Implementasi

1. **Owner approve** sumber + bahasa + model + agregasi (§14).
2. **News provider integration** (sesuai approval).
3. **Spec final** → `specifications/engines/sentiment-engine-spec.md`.
4. **Model + migration** (3 tabel).
5. **Engine deterministik** (dedup + agregasi + LLM gating + sanitasi).
6. **API + test** (termasuk security test §10).

> **Tidak dimulai sekarang** — owner deferred.

## 14. Keputusan yang Membutuhkan Product Owner Approval

| # | Keputusan | Opsi |
|---|---|---|
| 1 | Sumber data | Berita (RSS/news API) / Sosial / kedua — **butuh pilihan** |
| 2 | News provider spesifik | RSS gratis / API berbayar — **butuh pilihan + approval biaya** |
| 3 | Scope bahasa | ID / EN / multilingual — **butuh pilihan** |
| 4 | Model sentimen | LLM (agnes-3.0-flash, gated) / lexicon (VADER) — **butuh pilihan** |
| 5 | Window + decay factor | W = 7 hari, λ = 0.9 — **butuh approval** |
| 6 | Dedup policy | per headline-hash / per source+ts — **butuh pilihan** |
| 7 | Sosial data | tunda (noise tinggi) — **saran: approve** |
| 8 | Sentimen sebagai sinyal (bukan trigger) | **saran: approve** |
