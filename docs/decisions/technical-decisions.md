# 7.x Market Scanner Routing and Provider Decisions

- Yahoo Finance is used for both US and IDX markets due to the adapter's generic capability (`fetch_klines`) and the absence of specific vendor API requirements.
- The `markets=None` parameter in `run_scanner` defaults to scanning all active assets with valid provider mappings.
- Eligibility is enforced strictly: assets without valid mappings or with insufficient candle data (defined as < 50 candles per spec §4) are skipped, with reasons logged in `execution_metadata`.
- Symbol mapping quality directly dictates scanning eligibility; failure to map results in a skipped status rather than an invalid data process.
