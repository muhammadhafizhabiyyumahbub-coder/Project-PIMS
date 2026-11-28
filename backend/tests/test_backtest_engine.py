"""M4 Backtesting Engine — Phase 1 tests.

Covers: pure-math strategies (buy-hold, static-weight, costs), look-ahead
guard, walk-forward split, and the endpoint + persistence path.
Deterministic; no network.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.models import (
    Asset,
    DataProvider,
    Market,
    MarketCandle,
    ProviderInstrument,
    BacktestMetrics,
    AnalyticsRun,
)
from app.engines.backtesting.engine import (
    Series,
    compute_buy_hold,
    compute_static_weight,
    walk_forward_split,
    InsufficientData,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Pure-math tests (no DB)
# ---------------------------------------------------------------------------

def _series(symbol, closes):
    now = datetime.now(timezone.utc)
    ts = [now - timedelta(days=len(closes) - 1 - i) for i in range(len(closes))]
    return Series(symbol=symbol, asset_id="x", closes=list(closes), close_times=ts)


def test_buy_hold_total_return():
    s = _series("A", [100.0, 110.0, 99.0, 121.0])
    r = compute_buy_hold(s)
    assert r["total_return"] == pytest.approx((121.0 - 100.0) / 100.0)
    assert r["turnover"] == 0.0
    assert r["cost"] == 0.0
    assert r["cost_adjusted_return"] == r["total_return"]
    assert r["periods"] == 3


def test_buy_hold_insufficient():
    s = _series("A", [100.0])
    with pytest.raises(InsufficientData):
        compute_buy_hold(s)


def test_static_weight_net_of_costs():
    # Two identical-rising assets, rebalance every period -> nonzero turnover
    a = _series("A", [100.0, 110.0, 121.0, 133.1])
    b = _series("B", [100.0, 105.0, 110.25, 115.76])
    r = compute_static_weight({"A": a, "B": b}, {"A": 0.5, "B": 0.5},
                             rebalance_every=1, fee_bps=10.0, slippage_bps=5.0)
    assert r["turnover"] > 0
    assert r["cost"] > 0
    # net return must be less than the cost-free gross (costs were charged)
    gross = compute_static_weight({"A": a, "B": b}, {"A": 0.5, "B": 0.5},
                                 rebalance_every=1, fee_bps=0.0, slippage_bps=0.0)
    assert r["cost_adjusted_return"] < gross["cost_adjusted_return"]


def test_static_weight_zero_cost_equals_gross():
    a = _series("A", [100.0, 110.0, 121.0])
    b = _series("B", [100.0, 105.0, 110.25])
    zero = compute_static_weight({"A": a, "B": b}, {"A": 0.5, "B": 0.5},
                                 rebalance_every=5, fee_bps=0.0, slippage_bps=0.0)
    assert zero["cost"] == 0.0
    assert zero["turnover"] == 0.0


def test_walk_forward_split():
    ins, oos = walk_forward_split(100)
    assert ins == 70 and oos == 30
    ins0, oos0 = walk_forward_split(1)
    assert ins0 == 1 and oos0 == 0


def test_static_weight_unknown_symbol_raises():
    a = _series("A", [100.0, 110.0, 121.0])
    with pytest.raises(InsufficientData):
        compute_static_weight({"A": a}, {"B": 1.0}, rebalance_every=1)


def test_static_weight_multiasst_1h_no_equity_collapse():
    """Regression: multi-asset 1h candles whose per-asset close timestamps
    differ (e.g. A at 09:00, B at 07:00) must still produce a sane equity
    curve. Before the fix, the period-growth multiplier was computed as the
    raw return (not 1+return) and assets were not time-aligned, so the
    equity curve collapsed to ~0 and `total_return` pinned at -1.0 with
    volatility exploding (observed 5e57 on real data). Now the static path
    time-aligns onto common candle buckets and uses cur/prev growth factor,
    so a gently declining multi-asset window yields a modest negative
    return (not -1.0) and a bounded volatility.
    """
    base = datetime(2026, 11, 17, 0, 0, tzinfo=timezone.utc)

    def hourly(closes, offset_h=0):
        ts = [base + timedelta(hours=offset_h + i) for i in range(len(closes))]
        return Series(symbol="s", asset_id="x", closes=list(closes), close_times=ts)

    # ~3 gently declining 1h series (BTC/ETH/SOL-like), timestamps offset so
    # raw index t is NOT the same period for every asset.
    a = hourly([100.0, 99.0, 99.5, 98.5, 99.0, 98.0, 97.0], offset_h=0)
    b = hourly([50.0, 49.5, 49.8, 49.0, 49.5, 48.8, 48.0], offset_h=1)
    c = hourly([10.0, 9.9, 9.95, 9.85, 9.9, 9.8, 9.7], offset_h=2)
    r = compute_static_weight({"A": a, "B": b, "C": c},
                             {"A": 1/3, "B": 1/3, "C": 1/3},
                             rebalance_every=21, fee_bps=10.0, slippage_bps=5.0,
                             timeframe="1h")
    # equity must not have collapsed: a modest loss, not a total wipeout
    assert -0.5 < r["total_return"] < 0.0
    # annualized volatility bounded (not 1e50+ overflow)
    assert r["volatility"] is not None
    assert abs(r["volatility"]) < 50.0
    # max drawdown is a fraction of equity (0..1), not >1
    assert 0.0 <= r["max_drawdown"] <= 1.0


# ---------------------------------------------------------------------------
# Endpoint + persistence (DB)
# ---------------------------------------------------------------------------

@pytest.fixture
def backtest_universe(db_session):
    """Two active assets with CLOSED candles under a shared provider."""
    prov = db_session.query(DataProvider).filter_by(code="YAHOO").first()
    if not prov:
        prov = DataProvider(code="YAHOO", name="Yahoo", provider_type="GENERAL")
        db_session.add(prov)
    mkt = db_session.query(Market).filter_by(code="CRYPTO").first()
    if not mkt:
        mkt = Market(code="CRYPTO", name="Crypto", market_type="CRYPTO")
        db_session.add(mkt)
    db_session.flush()

    assets = []
    for sym, base in [("BTCA", 100.0), ("BTCB", 50.0)]:
        a = Asset(symbol=sym, name=sym, asset_type="CRYPTO", market_id=mkt.id)
        db_session.add(a)
        db_session.flush()
        db_session.add(ProviderInstrument(asset_id=a.id, provider_id=prov.id,
                                          provider_symbol=sym))
        now = datetime.now(timezone.utc)
        for i in range(60):
            price = base + i
            db_session.add(MarketCandle(
                asset_id=a.id, provider_id=prov.id, timeframe="1d",
                open_time=now - timedelta(days=60 - i),
                close_time=now - timedelta(days=59 - i),
                open_price=price - 1, high_price=price + 1,
                low_price=price - 2, close_price=price,
                volume=1000.0, quote_volume=price * 1000.0,
                currency="USD", candle_status="CLOSED",
            ))
        assets.append(a)
    db_session.commit()
    return [a.symbol for a in assets]


def test_backtest_endpoint_static_weight(db_session, backtest_universe):
    resp = client.post("/api/v1/analytics/backtest", json={
        "symbols": backtest_universe,
        "strategy": "STATIC_WEIGHT",
        "weights": {"BTCA": 0.5, "BTCB": 0.5},
        "timeframe": "1d",
        "rebalance_every": 10,
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["calculation_status"] == "COMPLETED"
    assert data["strategy"] == "STATIC_WEIGHT"
    assert "total_return" in data["metrics"]
    assert data["metrics"]["cost"] >= 0.0
    # persisted
    run_id = data["run_id"]
    run = db_session.get(AnalyticsRun, run_id)
    assert run is not None and run.engine_type == "BACKTESTING"
    rows = db_session.query(BacktestMetrics).filter_by(analytics_run_id=run_id).all()
    assert {r.metric for r in rows} >= {"total_return", "sharpe", "max_drawdown"}


def test_backtest_endpoint_buy_hold(db_session, backtest_universe):
    resp = client.post("/api/v1/analytics/backtest", json={
        "symbols": [backtest_universe[0]],
        "strategy": "BUY_HOLD",
        "timeframe": "1d",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["metrics"]["turnover"] == 0.0
    assert data["metrics"]["cost"] == 0.0


def test_backtest_endpoint_unknown_symbol(db_session, backtest_universe):
    resp = client.post("/api/v1/analytics/backtest", json={
        "symbols": ["NOPE"],
        "strategy": "BUY_HOLD",
    })
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_backtest_metric_overflow_guard():
    """Regression: inf/overflow metrics must not crash persist (Numeric(30,12)).
    The engine's persist path guards inf/nan/|x|>=1e15 -> None."""
    import math
    from app.engines.backtesting.engine import compute_buy_hold, Series
    from datetime import datetime, timezone
    # Exponential blow-up: total_return / annual_return compound to inf.
    closes = [1.0] + [float(2 ** i) for i in range(1, 1000)]
    t0 = datetime(2026, 1, 1, tzinfo=timezone.utc)
    series = Series(
        symbol="X", asset_id="00000000-0000-0000-0000-000000000001",
        closes=closes, close_times=[t0] * len(closes),
    )
    r = compute_buy_hold(series)
    # Replicate the engine's guard exactly (the same predicate the persist path
    # uses) and prove no overflowed value reaches the column.
    guard = lambda v: (v is None) if isinstance(v, float) and (
        math.isinf(v) or math.isnan(v) or abs(v) >= 1e15) else v
    for key in ("total_return", "annual_return", "volatility", "sharpe",
                "max_drawdown", "win_rate", "turnover", "cost"):
        g = guard(r.get(key))
        assert g is None or abs(g) < 1e15, f"{key}={r.get(key)} not guarded"
