"Seam 3 (continued): scanner scoring/ranking determinism and eligibility."
from app.engines import scanner

from tests.conftest import synthetic_candles, to_storage


def test_ranking_order_follows_momentum_and_trend():
    universe = {
        "UP": synthetic_candles(120, base_price=100.0, drift=0.01),
        "FLAT": synthetic_candles(120, base_price=100.0, drift=0.0),
        # Base price 5000 keeps the falling series above the liquidity floor.
        "DOWN": synthetic_candles(120, base_price=5000.0, drift=-0.01),
    }
    for candle in universe["DOWN"]:
        candle["volume"] = 1000.0
        candle["quote_volume"] = candle["close"] * 1000.0
    results = scanner.evaluate_universe(universe)
    assert [r["symbol"] for r in results] == ["UP", "FLAT", "DOWN"]
    assert results[0]["rank"] == 1
    scores = [r["score"] for r in results]
    assert scores == sorted(scores, reverse=True)
    assert all(0 <= s <= 100 for s in scores)


def test_insufficient_candles_excluded():
    universe = {
        "SHORT": synthetic_candles(30),
        "OK": synthetic_candles(120),
    }
    results = scanner.evaluate_universe(universe)
    assert [r["symbol"] for r in results] == ["OK"]


def test_low_liquidity_excluded():
    thin = synthetic_candles(120)
    for candle in thin:
        candle["volume"] = 0.001
        candle["quote_volume"] = 0.0
    results = scanner.evaluate_universe({"THIN": thin, "OK": synthetic_candles(120)})
    assert [r["symbol"] for r in results] == ["OK"]


def test_scoring_is_deterministic():
    universe = {
        "A": synthetic_candles(120, drift=0.003),
        "B": synthetic_candles(120, drift=-0.002),
    }
    first = scanner.evaluate_universe(universe)
    second = scanner.evaluate_universe(universe)
    assert [r["score"] for r in first] == [r["score"] for r in second]
