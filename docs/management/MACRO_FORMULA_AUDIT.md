# Audit Rumus Macro Engine PIMS

**Penyusun: Nadia subagent** — Auditor Rumus & Rubrik, Kantor 2
**Tanggal:** 28 November 2026
**Status keseluruhan:** `FAIL — 2 blocker numerik (series GDP salah + lag YoY/MA generik), 3 cacat definisi, 1 rumus lolos`

## Lingkup & metode

- Spesifikasi: `docs/management/MACRO_DATA_SPEC.md` (Tara, 16 baris) — sudah ada.
- Implementasi yang diaudit: `backend/app/engines/macro/engine.py` (196 baris, `CALC_VERSION = "macro.phase1.v1"`; file muncul saat audit berjalan), data `backend/app/data/providers/macro/fred.py`, `backend/app/data/providers/macro/fred_fetch.py`.
- Audit angka, bukan kode: setiap fungsi dieksekusi dengan data FRED nyata di venv, lalu dibandingkan terhadap hitungan manual independen (tanpa pandas) dan rumus standar.
- Lingkungan: `backend/.venv/Scripts/python.exe` — Python 3.13.7, pandas 3.1.1.
- Data: FRED publik via `fredgraph.csv` (tanpa key) **dan** FRED API v1 `series/observations` (key dibaca dari `.env`, tidak dicetak, `.env` tidak diubah). Kedua sumber identik: CPIAUCSL `2026-10-01 = 337.476`.
- Sampel: CPIAUCSL 957 obs (1947-01→2026-10) · GDPC1 319 obs (1947-01→2026-07) · GDPA 97 obs (tahunan, s.d. 2025) · UNRATE 945 obs (→2026-10) · FEDFUNDS 868 obs (→2026-10, 3.88) · DGS10 16.210 obs (→2026-11-25, 4.85).
- Test suite: `pytest --collect-only -q` = **355 tests collected** (klaim terkonfirmasi). `pytest tests/test_macro_engine.py -q` = **13 passed**.
- Skrip audit read-only di luar repo: `D:/temp/audit_macro.py`, `D:/temp/audit_macro2.py`.

## Ringkasan verdict

| # | Rumus | Spec | Engine (`engine.py`) | Verdict |
|---|---|---|---|---|
| F1 | YoY bulanan | `(t-t12)/t12` tanpa `×100` | `(t-t12)/t12*100` (baris 55) | **PASS** — kode benar, spec cacat unit (LOW) |
| F2 | YoY lag-12 untuk GDP | lag 12 untuk semua series | `lag=12` dipaku, series `GDPA` tahunan | **FAIL — BLOCKER** (YoY 82,82%) |
| F3 | YoY untuk series persen | idem | idem | **FAIL** — relatif atas persen, tak bermakna |
| F4 | Rolling avg 12 periode | `mean(last 12)` | `mean(last 12)` (baris 62) | **PASS bulanan / FAIL non-bulanan** |
| F5 | Z-score | `(x-mean)/std(all)` | populasi std, guard `var<=0` (baris 65-73) | **PASS aritmetika / CONDITIONAL definisi** |
| F6 | Regime | `Z > 0` → expansion | `level >= MA12` → EXPANSION | **FAIL** — spec≠kode, keduanya ≠ standar |
| F7 | Pemetaan series & integritas | — | `GDP→GDPA`, error ditelan, stub `100.0` | **FAIL** |

---

## F1 — YoY change bulanan (CPI)

**Formula:** `(val_t - val_t-12) / val_t-12 * 100`

**Expected manual (CPIAUCSL):**
- t = 2026-10-01 → 337,476
- t-12 = 2025-09-01 → 324,245
- (337,476 − 324,245) / 324,245 × 100 = **4,0806%** (Python murni: 4,080556%)

**Actual (venv, `compute_metrics` engine):**
```
CPI CPIAUCSL n=957 period=2026-10-01 level=337.476 yoy=4.080556
```

**Verdict: PASS.** Kode mengalikan 100 dan hasilnya cocok sampai 6 desimal dengan hitungan tangan.
Cacat dokumen (bukan kode): `MACRO_DATA_SPEC.md` baris 13 menulis `(val_t - val_t-12)/val_t-12` tanpa `×100` tetapi menamai metrik "YoY%" — implementasi mengikuti kontrak persen, spec tidak. Perbaiki spec agar tidak "dibetulkan" ke arah yang salah nanti.

**Bukti:** blok A `audit_macro.py`; `4.080556% (hand)` vs `4.080556% (engine)`.

---

## F2 — YoY untuk GDP (BLOCKER)

**Formula spec:** lag 12 untuk semua series. **Engine:** `yoy_change(values)` dengan `lag = ROLLING_WINDOW = 12` (baris 48-55) — tidak ada parameter frekuensi. **Provider:** `SERIES_MAP["GDP"] = "GDPA"` (tahunan, nominal) sedangkan spec menyebut `GDPC1` (kuartalan, riil).

**Expected manual (definisi benar):**
- Kuartalan → lag 4: (24.665,201 − 24.112,966) / 24.112,966 × 100 = **2,29%** (2026-07 vs 2025-07)
- Tahunan (`GDPA` yang dipakai kode) → lag 1: (30.861,292 − 29.380,991) / 29.380,991 × 100 = **5,04%**

**Actual (venv, engine):**
```
GDP GDPA n=97 period=2025-01-01 level=30861.292 yoy=82.820162
     rolling_avg_12=22980.473083 (rata-rata 12 TAHUN) zscore=3.089529 regime=EXPANSION
GDPC1 (spec series) dipaksa lewat engine lag-12: 8.04% vs benar 2.29% (abs_err 5.75pp)
```

**Verdict: FAIL — BLOCKER.** Dua cacat bertumpuk:
1. `GDP→GDPA` (tahunan, **nominal**) sementara spec + UI mengklaim GDP riil YoY.
2. `lag = 12` buta frekuensi: pada data tahunan = **12 tahun** → 82,82%; pada kuartalan = 3 tahun → 8,04% (vs 2,29% benar).

Konsekuensi: headline GDP salah ~16× (82,82% vs 5,04%) dan z-score GDP (3,09) tidak bermakna. Lolos test karena `tests/test_macro_engine.py` memakai fixture berjarak seragam (mis. 111 → 123) yang tidak menguji perbedaan frekuensi.

**Bukti:** blok D/D2; `SERIES_MAP` tercetak `{'CPI': 'CPIAUCSL', 'GDP': 'GDPA', ...}`.

---

## F3 — YoY pada series ber-unit persen

**Formula:** sama `*100` diterapkan ke UNRATE, FEDFUNDS, DGS10.

**Expected manual (metrik bermakna = poin persentase):**
- UNRATE 4,4 (2025-09) → 4,1 (2026-10) = **−0,30 pp**
- FEDFUNDS 4,09 (2025-10) → 3,88 (2026-10) = **−0,21 pp**
- DGS10: YoY bulanan rata-rata = **21,41%** (setelah agregasi bulanan)

**Actual (venv, engine):**
```
UNRATE   yoy=-6.818182  (4.4 -> 4.1)   MA12=4.266667  z=-0.911214  CONTRACTION
FEDFUNDS yoy=-5.134474  (4.09 -> 3.88) MA12=3.6925    z=-0.202468  EXPANSION
10YUSTR  yoy=-0.205761  MA12=5.003333  z=-0.325789   CONTRACTION
  (DGS10: t-12 = 12 hari bursa, 2026-11-06 -> 2026-11-25)
```

**Verdict: FAIL.** Tiga masalah:
1. Perubahan relatif dari sebuah **laju** bergantung basis arbitrer: 4,1→4,2 terbaca "+2,4%", tetapi 0,1%→0,2% terbaca "+100%". Tidak sebanding antarrezim suku bunga.
2. DGS10 harian: `t-12` = **12 hari bursa** → "−0,21%" derau dua minggu, bukan YoY (YoY bulanan sebenarnya 21,41%). Salah konteks ~100×.
3. UI menampilkan "YoY" untuk tiga jenis besaran berbeda (indeks, persen, yield) yang tidak setara maknanya.

Rekomendasi (tidak diterapkan): `yoy_pct` hanya CPI/GDP; `delta_pp` untuk UNRATE/FEDFUNDS/DGS10; DGS10 diagregasi bulanan sebelum YoY.

**Bukti:** blok E/H; output engine di atas.

---

## F4 — Rolling average 12

**Formula:** `mean(last 12 observations)`.

**Expected manual (CPI, 12 obs terakhir = Nov 2025–Okt 2026):** Σ/12 = **331,258917**.

**Actual (venv):**
```
CPI       rolling_avg_12=331.258917        (hand sum/12 = 331.258917 -> cocok 6 desimal)
GDP(GDPA) rolling_avg_12=22980.473083      (rata-rata 12 TAHUN; level kini 30861.29)
GDPC1:    12-quarter MA=23811.14 vs 4-quarter (12 bulan) MA=24368.27 -> delta -2.29%
DGS10:    12 observasi = 12 hari bursa
```

**Verdict: PASS untuk bulanan, FAIL untuk kuartalan/harian.** `ROLLING_WINDOW=12` dibaca sebagai *observasi*, bukan *bulan*. Untuk CPI identik dengan hitungan tangan; untuk GDP rata-rata mencakup 12 tahun — selisih −2,29% (GDPC1) sampai −25,5% (GDPA 22.980 vs 30.861) terhadap MA 12 bulan sebenarnya. Spec juga tidak menyatakan MA atas **level** atau **YoY**; engine memakai level, sedangkan MA atas YoY CPI = 3,51%.

**Bukti:** blok B, D3; output engine.

---

## F5 — Z-score

**Formula:** `(x - mean(all)) / std(all)`. Engine: populasi std (`/len`), guard `var <= 0 → None`.

**Expected manual (CPI, 957 obs):**
- mean = 126,0275; std populasi (ddof=0) = 91,2002
- z(2026-10) = (337,476 − 126,0275) / 91,2002 = **2,3185**
- pembanding ddof=1: std 91,2479 → z 2,3173

**Actual (venv, engine):**
```
CPI zscore=2.318509     (expected ddof=0: 2.318509 -> cocok)
UNRATE z=-0.911214 | FEDFUNDS z=-0.202468 | DGS10 z=-0.325789 | GDP(GDPA) z=3.089529
z pada series YoY CPI (bukan level) = 0.195226 (mean=0.035228, std=0.028571)
```

**Verdict: PASS aritmetika, CONDITIONAL pada definisi.**
1. Aritmetika tepat: cocok dengan hitungan manual ddof=0 sampai 6 desimal; guard `var<=0` dan `len<2` ada (diuji `test_zscore_matches_independent_value`).
2. Jendela "all" tidak dikunci — z bergantung seluruh history 1947–2026; dengan jendela 10 tahun nilainya jauh berbeda. Tanpa `z_window` di `CALC_VERSION`, angka tidak dapat direproduksi setelah revisi data FRED.
3. **Cacat interpretasi:** z atas **level** CPI = 2,32 (dibaca "2,3σ tidak normal"), padahal inflasi YoY hanya 0,20σ di atas rata-rata historisnya (4,08% vs 3,52%). Untuk CPI/GDP/DGS10 yang ber-tren, z level mengukur posisi dalam tren, bukan anomali. Alternatif: z atas YoY/Δ.

**Bukti:** blok C; output engine.

---

## F6 — Regime

**Spec:** `expansion if Z > 0 else contraction`.
**Engine:** `classify_regime(latest, avg)` → `EXPANSION if latest >= rolling_avg_12 else CONTRACTION` (baris 76-80; `>=` terhitung expansion).
**Standar (rujukan tugas):** expansion jika **YoY GDP > 0 dan UNRATE turun**.

**Expected manual (kondisi sekarang, definisi standar):**
- GDPC1 YoY (lag 4) = 2,29% > 0 ✔
- UNRATE 4,2 (2026-09) → 4,1 (2026-10), turun ✔
- → **expansion**

**Actual (venv, engine, per series):**
```
CPI       level=337.476      MA12=331.258917  -> EXPANSION
UNRATE    level=4.1          MA12=4.266667    -> CONTRACTION
FEDFUNDS  level=3.88         MA12=3.6925      -> EXPANSION
10YUSTR   level=4.85         MA12=5.003333    -> CONTRACTION
GDP(GDPA) level=30861.292    MA12=22980.473   -> EXPANSION
```
Perbandingan definisi (944 bulan, 1948–2026): regime `Z>0` atas CPI level vs standar (GDP YoY>0 & UNRATE turun) **sepakat hanya 51,3%** — setara lempar koin. Distribusi: spec 503 contraction/441 expansion; standar 577/367.

**Verdict: FAIL.** Empat masalah:
1. **Spec ≠ kode.** Spec `Z > 0`; kode `level >= MA12`. Dua aturan berbeda, sehingga reviewer menguji hal yang tidak dijalankan engine.
2. **Tidak ada label makro.** Hasil per series saling bertentangan hari ini (CPI EXPANSION, UNRATE CONTRACTION, 10Y CONTRACTION). Tidak ada aturan agregasi di spec maupun kode; UI yang menampilkan satu "regime" akan menyesatkan.
3. **Semantik salah untuk sebagian series.** `level >= MA12` pada FEDFUNDS berarti "suku bunga di atas rata-rata 12 bulan = EXPANSION" — justru stance moneter ketat. Pada UNRATE label CONTRACTION kebetulan sejalan arah, tetapi alasannya (pengangguran di bawah rata-rata) terbalik dari maksud ekonomi.
4. **Ambang `>=`** membuat level tepat sama dengan MA selalu EXPANSION (test baris 61 mengunci perilaku ini) — bias expansion pada series datar.

Rekomendasi (tidak diterapkan): satu `macro_regime` dari `gdp_yoy > 0 and unrate_delta_3m < 0`; label per series diganti netral (`above_ma12`/`below_ma12`); sertakan `regime_basis` di respons API.

**Bukti:** blok F/F2/G; output engine; `classify_regime` + test baris 58-62.

---

## F7 — Pemetaan series & integritas angka

| Item | Spec | Kode | Dampak angka |
|---|---|---|---|
| GDP | `GDPC1` kuartalan riil, miliar chained 2017 | `SERIES_MAP["GDP"] = "GDPA"` — **tahunan nominal** | YoY 82,82% (bukan 5,04%); z GDP 3,09 tidak bermakna |
| DFF | tidak ada di spec | `DFF` harian (duplikat FEDFUNDS) | Dua series suku bunga, satu label "fed funds" |
| 10Y | `DGS10` | `10YUSTR → DGS10` | nama key beda dari dokumen bisnis; nilai benar |
| Cakupan | — | `GDPA` s.d. 2025-01; `GDPC1` s.d. 2026-07 | UI tampak 1,5 tahun tertinggal |

`fred_fetch.py` (Tara):
- Baris 12-13: bila key kosong atau `"test_key"` → `[{"value": "100.0", "date": "2024-01-01"}]`. **Data dikarang.** Dengan satu observasi, engine melaporkan `level=100.0` sah, `yoy=None`, `zscore=None`, `regime=UNAVAILABLE` — angka palsu bercampur status valid.
- Memakai `requests` (bukan `httpx` seperti `fred.py`) dan tidak menangani `"."`; `float(".")` → `ValueError` pada series dengan nilai hilang.

**Kegagalan senyap di provider (teramati hari ini):**
```
run 1: FREDAdapter(timeout=15).fetch_observations('CPIAUCSL') -> n=0   -> status UNAVAILABLE
run 2: adapter sama, key sama                                -> n=957 (2,0 detik)
raw httpx tanpa adapter                                      -> 200, 958 obs
```
`fred.py` menangkap `httpx.HTTPError` lalu `return []` tanpa log/retry (baris 62-63). Kegagalan transien pada series acuan (CPI) tidak dapat dibedakan dari "tidak ada data", dan engine menyimpannya sebagai `UNAVAILABLE` di `macro_results`. Ini menurunkan keandalan laporan karena CPI adalah dasar audit YoY.

**Verdict: FAIL.**

---

## Verifikasi yang dijalankan

| Cek | Metode | Hasil |
|---|---|---|
| YoY CPI dari FRED nyata | fredgraph CSV + FRED API v1 (key `.env`, tidak dicetak) | 4,0806% (2026-10); kedua sumber identik 337.476 |
| YoY hand-aritmetika | Python murni tanpa pandas | 4,080556% = engine 4,080556% |
| Rolling avg 12 | Σ/12 manual vs engine | 331,258917 = 331,258917 |
| Z-score | manual ddof=0 vs engine | 2,3185 = 2,318509 |
| Z-score sensitivitas | ddof 0 vs 1 | 2,318509 vs 2,317298 (Δ0,0012) |
| GDP lag | t-12 vs t-4 (GDPC1); t-12 vs t-1 (GDPA) | 8,04% / 2,29%; 82,82% / 5,04% |
| DGS10 lag | t-12 observasi vs YoY bulanan | −0,21% vs 21,41% |
| Regime vs standar | 944 bulan | sepakat 51,3% |
| Engine end-to-end | `compute_metrics` pada 5 series FRED | lihat tabel F6 |
| Test suite | `pytest --collect-only -q` / `test_macro_engine.py` | 355 collected / 13 passed |

## Prioritas perbaikan (untuk Raka & Tara — tidak saya terapkan)

1. **Blocker** — `SERIES_MAP["GDP"]`: `GDPA` → `GDPC1`, samakan dengan spec.
2. **Blocker** — lag YoY & window MA mengikuti frekuensi (`12` bulanan, `4` kuartalan, agregasi bulanan/`252` harian); jangan konstanta 12 global.
3. **High** — ganti regime per-series `level>=MA12` dengan satu `macro_regime` (GDP YoY + arah UNRATE) + `regime_basis`; selaraskan `MACRO_DATA_SPEC.md` (spec menulis `Z>0`, kode memakai MA).
4. **High** — rate/yield: `delta_pp`, bukan `yoy_pct`; DGS10 agregasi bulanan dulu.
5. **Medium** — kunci `ddof`, jendela z, dan hitung z atas YoY/Δ (bukan level) untuk CPI/GDP/DGS10.
6. **Medium** — `rolling_avg_12` eksplisit "12 bulan kalender atas level".
7. **Low** — hapus stub `100.0` di `fred_fetch.py`; satukan fetcher pada `httpx`; log + retry sekali pada `HTTPError` di `fred.py`.

**Nadia subagent** — audit angka saja; tidak ada perubahan kode, `.env`, atau push.
