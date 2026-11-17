"Seam 3: deterministic engine math on known inputs (synthetic series)."
from app.engines import market_regime, risk, scanner
from app.engines.technical import engine as technical

from tests.conftest import synthetic_candles


class TestTechnical:
    def test_sma_known_values(self):
        assert technical.sma([1, 2, 3, 4], 2) == 3.5
        assert technical.sma([1, 2], 3) is None

    def test_rsi_extremes(self):
        rising = [float(i) for i in range(20)]
        falling = [float(-i) for i in range(20)]
        assert technical.rsi(rising) == 100.0
        assert technical.rsi(falling) == 0.0

    def test_compute_completed_on_sufficient_candles(self):
        out = technical.compute(synthetic_candles(120), observation_time=None)
        assert out["calculation_status"] == "COMPLETED"
        values = out["values"]
        for key in ("sma_20", "sma_50", "rsi_14", "atr_14", "macd"):
            assert values[key] is not None

    def test_compute_fails_on_insufficient_candles(self):
        out = technical.compute(synthetic_candles(30), observation_time=None)
        assert out["calculation_status"] == "FAILED"


class TestMarketRegime:
    def test_bullish_classification(self):
        out = market_regime.classify(
            sma_20=110.0, sma_50=100.0, last_close=115.0, rsi_14=60.0, atr_14=1.0
        )
        assert out["trend_regime"] == "BULLISH"
        assert out["volatility_regime"] == "LOW"
        assert out["momentum_regime"] == "BULLISH"

    def test_bearish_classification(self):
        out = market_regime.classify(
            sma_20=90.0, sma_50=100.0, last_close=85.0, rsi_14=40.0, atr_14=1.0
        )
        assert out["trend_regime"] == "BEARISH"

    def test_confidence_bounded(self):
        out = market_regime.classify(
            sma_20=200.0, sma_50=100.0, last_close=300.0, rsi_14=70.0, atr_14=1.0
        )
        assert 0 <= out["confidence_score"] <= 100


class TestRisk:
    def test_flat_series_low_volatility(self):
        closes = [100.0] * 60
        out = risk.compute(
            [
                {
                    "close": c,
                    "high": c + 0.5,
                    "low": c - 0.5,
                }
                for c in closes
            ]
        )
        assert out["calculation_status"] == "COMPLETED"
        assert out["volatility"] == 0.0
        assert out["risk_classification"] == "LOW"

    def test_high_volatility_classified_high(self):
        # Alternating +/- 5% closes -> large annualized volatility.
        closes = [100.0 * (1.05 if i % 2 else 0.95) for i in range(60)]
        out = risk.compute(
            [{"close": c, "high": c + 0.5, "low": c - 0.5} for c in closes]
        )
        assert out["risk_classification"] == "HIGH"

    def test_max_drawdown_known(self):
        closes = [100.0, 120.0, 90.0]
        assert abs(risk.max_drawdown(closes) - 0.25) < 1e-9
