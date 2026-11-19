# PIMS — Roadmap Lanjutan (setelah V1 RC)

**Status:** Draft kerja, disusun dari gap nyata terhadap `specifications/` (bukan asumsi).
**Dasar:** `api-spec.md` mendefinisikan 54 endpoint; implementasi saat ini 26 endpoint (selisih **35**).
**Prinsip:** hanya mengerjakan yang punya spec; gagal-jujur (UNAVAILABLE + alasan) lebih baik daripada angka karangan; setiap tahap wajib test hijau + commit + push.

## Gap yang terverifikasi

| # | Gap | Bukti |
|---|---|---|
| G1 | 35 endpoint spec belum ada | diff `api-spec.md` vs `openapi.json` |
| G2 | Tabel `market_quotes`, `fx_rates`, `scanner_configurations` ada di `schema-spec` §6.1/§6.4/§8.1 tapi belum ada di model/DB | `grep __tablename__` vs spec |
| G3 | `watchlists` dirujuk `api-spec` (6 endpoint) tapi **tidak ada** di `schema-spec` | konflik dokumen → butuh keputusan |
| G4 | Tidak ada script verifikasi tunggal / laporan test rilis terpusat | `scripts/verify_all.sh`, `docs/testing/RELEASE_TEST_REPORT.md` belum ada |
| G5 | Docker belum diverifikasi (ditunda atas keputusan owner) | bukan blocker; test pakai PostgreSQL 17 lokal |
| G6 | Engine correlation/factor/sentiment/macro/backtesting/attribution/scenario masih kosong | sesuai spec belum ada rumusnya |

## Tahapan

### Stage U — API read-only dari tabel yang sudah ada (tanpa schema change)
- `GET /dashboard/overview|activity|market-overview|research-highlights|scanner-highlights`
- `GET /markets`, `/markets/{id}`, `/markets/status`
- `GET /market-data/instruments/{asset_id}/candles`
- `GET /research` (list), `DELETE /research/{report_id}`
- `GET /scanner/categories`, `/scanner/results`, `/scanner/runs/{run_id}`
Gate: semua endpoint punya test; nilai tak tersedia → null + alasan; 0 float di JSON; suite hijau.

### Stage V — Market quotes & scanner configs (schema per spec §6.1, §6.4, §8.1)
- Migration: `market_quotes`, `fx_rates`, `scanner_configurations`.
- `GET /market-data/quotes`, `/market-data/instruments/{asset_id}/quote`, CRUD `/scanner/configurations`.
- Kejujuran: quote tanpa data → `UNAVAILABLE` + `data_timestamp` null; FX tanpa data → tolak konversi, bukan kurs karangan.

### Stage W — Analytics instrument-scope & watchlists
- `GET /analytics/{technical,market-regime,correlation,allocation,performance,risk}` (instrument-scope hanya bila engine + data ada; selain itu UNAVAILABLE + alasan).
- Watchlists: **butuh keputusan owner** karena tabelnya tidak ada di `schema-spec` (konflik G3). Opsi: (a) tambahkan tabel ke schema-spec lalu implementasi, (b) tunda.

### Stage X — Hardening (security, performance, quality)
- Security: validasi input batas, batas ukuran payload, rate-limit `/market-data/refresh`, header CSP/CORS eksplisit, audit log tanpa secrets.
- Performance: index sesuai `schema-spec` §indexes (mis. `market_candles(asset_id, timeframe, open_time)`), hilangkan N+1 pada holdings/valuation/allocation, ukur sebelum/sesudah.
- Quality: `ruff check` bersih (konfigurasi eksplisit, bukan mematikan aturan), tipe & docstring konsisten, `scripts/verify_all.sh` + `docs/testing/RELEASE_TEST_REPORT.md`.

### Stage Y — Dokumentasi & rilis
- Perbarui `RELEASE_NOTES_V1.md`, `RELEASE_KNOWN_ISSUES.md`, panduan pengguna untuk endpoint baru.
- Docker: dikerjakan setelah owner siap reboot fisik.

## Urutan eksekusi & alasan
1. **U** — nilai tertinggi, risiko terendah (read-only, tabel sudah ada).
2. **X (parsial: index + N+1)** — mencegah utang performa sebelum data bertambah.
3. **V** — menambah kemampuan nyata (quote/fx/scanner config), butuh migration terpisah + review.
4. **W** — menunggu keputusan watchlists.
5. **Y** — di akhir setiap tahap dokumen disinkronkan.

## Definisi selesai (per tahap)
- Test baru dengan angka hitung tangan; suite penuh 0 failed.
- Frontend lint/build hijau bila tersentuh.
- Kejujuran data diuji (null/UNAVAILABLE punya test).
- Commit + push; `technical-decisions.md` diperbarui bila ada keputusan.