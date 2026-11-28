# Macro Data Specification
Target: FRED API Integration

| Name | FRED ID | Unit | Freq | Start | Fetch | Metrics |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| CPI | CPIAUCSL | Index | Monthly | 1947 | fred_api_get | YoY%, 12m MA, Z-score, Regime |
| GDP | GDPC1 | Billions Chained 2017 USD | Quarterly | 1947 | fred_api_get | YoY%, 12m MA, Z-score, Regime |
| Unemp | UNRATE | Percent | Monthly | 1948 | fred_api_get | YoY%, 12m MA, Z-score, Regime |
| Fed Funds | FEDFUNDS | Percent | Monthly | 1954 | fred_api_get | YoY%, 12m MA, Z-score, Regime |
| 10Y Treasury | DGS10 | Percent | Daily | 1962 | fred_api_get | YoY%, 12m MA, Z-score, Regime |

Metrics:
- YoY change: `(val_t - val_t-12) / val_t-12`
- Rolling avg 12m: `mean(last 12 periods)`
- Z-score: `(val - mean(all)) / std(all)`
- Regime: `expansion if Z > 0 else contraction`
