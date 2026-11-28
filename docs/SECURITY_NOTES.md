# PIMS — Security Notes

Status: **dev / single-user, lokal**. Dokumen ini mencatat asumsi keamanan dan
keputusan yang belum diimplementasikan. Bukan pengganti audit (lihat
`docs/QA_REPORT.md`).

## 1. Model ancaman (asumsi)

- PIMS adalah **aplikasi single-user lokal** (keputusan §26 owner: tak ada tabel
  `users`, `portfolios` tanpa `owner_id` — `docs/decisions/technical-decisions.md`
  §7.17). Tidak ada lapisan auth.
- Karena itu REST & WebSocket **tidak diautentikasi** (Sakti S8). Ini diterima
  **hanya** selama instance berjalan di mesin lokal tepercaya.
- **Jangan expose ke jaringan publik / LAN.** Batasi dengan firewall host,
  bind loopback, atau reverse proxy yang menambahkan auth.
- Real-time feed hanya diklaim bila provider menjamin (AGENTS.md §8.3).

## 2. Pengerasan yang sudah dilakukan (Q1, 2026-11-28)

- `docker-compose.yml`:
  - Port Postgres `5432` **tidak lagi dipublish** ke host — DB hanya di jaringan
    compose internal.
  - Backend dipublish host-local: `127.0.0.1:8000:8000` (bukan `0.0.0.0`), jadi
    tidak dapat dijangkau dari LAN.
- `backend/Dockerfile` tetap `--host 0.0.0.0` **di dalam container** karena
  service `frontend` memanggil `http://backend:8000` lewat jaringan compose.
  Membind loopback di dalam container akan memutus frontend. Eksposur ke host/LAN
  dikendalikan oleh publish binding di compose (di atas), bukan oleh listen
  address container.

> Catatan deviasi dari instruksi Q1: instruksi meminta ubah Dockerfile
> `0.0.0.0 -> 127.0.0.1`. Diubah ke loopback akan memecah `frontend -> backend`
> (satu compose network). Penulis memilih kontrol eksposur di layer publish
> (compose) dan menahan perubahan Dockerfile. Perlu persetujuan owner bila tetap
> ingin listen loopback container.

## 3. Kebocoran detail error (Q2, 2026-11-28)

- Handler 500 tidak lagi mengembalikan `str(exc)` mentah ke client. Helper
  `server_error()` di `app/api/envelope.py` menulis detail + traceback ke server
  log (`logger.exception`) dan mengembalikan pesan generik
  `"Internal error (see server logs)"`.
- Semua 13 titik `error_response("SERVER_ERROR", str(exc), 500)` di
  `app/api/rest/analytics_v2.py` (12) dan `app/api/rest/analytics.py` (1) sudah
  diganti. Test: `backend/tests/test_security_q2.py`.

## 4. Belum dikerjakan (butuh keputusan owner)

| Area | Status | Catatan |
|---|---|---|
| Authentication/authorization | **Phase 2** | Belum ada; lihat §1. |
| Rate limit / biaya LLM (Q5) | belum | `POST /api/v1/research` + endpoint analytics sinkron. |
| Port DB ke host | ditutup (§2) | Untuk debug lokal, publish manual sesaat. |
| Cap subscription WS + validasi timeframe (Q6) | belum | lihat `docs/QA_REPORT.md`. |
| Secrets di `.env` | OK | `.env` gitignored; hanya `.env.example`. |
