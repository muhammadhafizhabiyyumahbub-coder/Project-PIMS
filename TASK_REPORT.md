# Justifikasi Index (schema-spec §13)

| Index Nama | Lokasi Spec §13 |
|---|---|
| `ix_market_candles_asset_tf_time` | market_candles(asset_id, timeframe, open_time) |
| `ix_assets_symbol_type` | assets(symbol, asset_type) |
| `ix_analytics_runs_type_started` | analytics_runs(analysis_type, started_at) |
| `ix_perf_results_portfolio_period` | performance_results(portfolio_id, period_start) |
| `ix_tech_results_asset_tf_time` | technical_results(asset_id, timeframe, time) |
| `ix_regime_results_asset_tf_time` | regime_results(asset_id, timeframe, time) |
| `ix_scanner_results_run_rank` | scanner_results(run_id, rank) |

*Catatan: Semua index yang ditambahkan pada migrasi `2462e115ce2f` telah dipetakan langsung ke kebutuhan `specifications/database/schema-spec.md` untuk mendukung query performa tinggi pada analytics engine dan scanner.*
