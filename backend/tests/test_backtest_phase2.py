"""M4 Backtesting Engine — Phase 2 (rule-based) tests.

Covers: MA_CROSSOVER / RSI_THRESHOLD / MOMENTUM pure-math signals, the
UNAVAILABLE guard, determinism, cost impact, plus the endpoint + persistence
path (strategy_type / entry_rule / exit_rule / trade_count / win_rate).
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
from app.engines.backtesting import (
    Series,
    compute_rule_based,
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


def test_ma_crossover_enters_and_exits():
    # rise into a fast>slow regime, then fall back out of it
    closes = [10.0] * 5 + [11.0, 12.0, 13.0, 14.0, 15.0, 16.0,
                           15.0, 14.0, 13.0, 12.0, 11.0]
    r = compute_rule_based(_series("A", closes), "MA_CROSSOVER",
                           {"ma_fast": 2, "ma_slow": 4})
    assert r["calculation_status"] == "COMPLETED"
    assert r["trade_count"] >= 1
    assert r["entry_rule"] == "SMA(2) > SMA(4)"
    assert r["exit_rule"] == "SMA(2) < SMA(4)"
    assert r["turnover"] > 0 and r["cost"] > 0
    assert 0.0 <= r["win_rate"] <= 1.0


def test_ma_crossover_insufficient_is_unavailable():
    r = compute_rule_based(_series("A", [1.0, 2.0, 3.0]), "MA_CROSSOVER",
                           {"ma_fast": 10, "ma_slow": 30})
    assert r["calculation_status"] == "UNAVAILABLE"
    assert r["trade_count"] == 0
    assert "candles" in r["reason"]


def test_ma_crossover_bad_config_raises():
    with pytest.raises(InsufficientData):
        compute_rule_based(_series("A", [1.0] * 50), "MA_CROSSOVER",
                           {"ma_fast": 30, "ma_slow": 10})


def test_rsi_threshold_enters_oversold_exits_overbought():
    # sharp drop (RSI ~0) then recovery (RSI high) triggers one round trip
    closes = [100.0] * 15 + [95.0, 90.0, 85.0, 80.0, 75.0,
                             80.0, 85.0, 90.0, 95.0, 100.0, 110.0]
    r = compute_rule_based(_series("A", closes), "RSI_THRESHOLD",
                           {"rsi_period": 3, "rsi_oversold": 30.0,
                            "rsi_overbought": 70.0})
    assert r["calculation_status"] == "COMPLETED"
    assert r["trade_count"] >= 1
    assert r["entry_rule"] == "RSI(3) < 30"
    assert r["exit_rule"] == "RSI(3) > 70"


def test_rsi_threshold_insufficient_is_unavailable():
    r = compute_rule_based(_series("A", [1.0, 2.0, 3.0]), "RSI_THRESHOLD",
                           {"rsi_period": 14})
    assert r["calculation_status"] == "UNAVAILABLE"


def test_momentum_invested_in_uptrend():
    closes = [100.0 + i for i in range(30)]
    r = compute_rule_based(_series("A", closes), "MOMENTUM",
                           {"momentum_period": 5, "momentum_threshold": 0.0})
    assert r["calculation_status"] == "COMPLETED"
    assert r["trade_count"] == 1
    assert r["total_return"] > 0
    assert r["entry_rule"] == "ret(5) > 0"


def test_momentum_flat_market_no_trade():
    r = compute_rule_based(_series("A", [100.0] * 30), "MOMENTUM",
                           {"momentum_period": 5, "momentum_threshold": 0.0})
    assert r["trade_count"] == 0
    assert r["turnover"] == 0.0 and r["cost"] == 0.0
    assert r["total_return"] == pytest.approx(0.0)


def test_rule_based_deterministic():
    closes = [10.0] * 5 + [11.0, 12.0, 13.0, 14.0, 15.0, 14.0, 13.0, 12.0]
    s = _series("A", closes)
    a = compute_rule_based(s, "MA_CROSSOVER", {"ma_fast": 2, "ma_slow": 4})
    b = compute_rule_based(s, "MA_CROSSOVER", {"ma_fast": 2, "ma_slow": 4})
    assert a == b


def test_rule_based_costs_reduce_return():
    closes = [10.0, 11.0, 10.5, 12.0, 11.0, 13.0, 12.0, 14.0, 13.0, 15.0]
    s = _series("A", closes)
    free = compute_rule_based(s, "MA_CROSSOVER", {"ma_fast": 2, "ma_slow": 3},
                              fee_bps=0.0, slippage_bps=0.0)
    costly = compute_rule_based(s, "MA_CROSSOVER", {"ma_fast": 2, "ma_slow": 3},
                                fee_bps=50.0, slippage_bps=50.0)
    assert costly["cost"] > free["cost"] == 0.0
    assert costly["total_return"] < free["total_return"]


# ---------------------------------------------------------------------------
# Endpoint + persistence (DB)
# ---------------------------------------------------------------------------

@pytest.fixture
def rule_universe(db_session):
    """Three active CRYPTO assets with 90 CLOSED daily candles (deterministic)."""
    prov = db_session.query(DataProvider).filter_by(code="YAHOO").first()
    if not prov:
        prov = DataProvider(code="YAHOO", name="Yahoo", provider_type="GENERAL")
        db_session.add(prov)
    mkt = db_session.query(Market).filter_by(code="CRYPTO").first()
    if not mkt:
        mkt = Market(code="CRYPTO", name="Crypto", market_type="CRYPTO")
        db_session.add(mkt)
    db_session.flush()

    symbols = []
    for sym, base in [("RULEA", 100.0), ("RULEB", 50.0), ("RULEC", 200.0)]:
        a = Asset(symbol=sym, name=sym, asset_type="CRYPTO", market_id=mkt.id)
        db_session.add(a)
        db_session.flush()
        db_session.add(ProviderInstrument(asset_id=a.id, provider_id=prov.id,
                                          provider_symbol=sym))
        now = datetime.now(timezone.utc)
        price = base
        for i in range(90):
            # gentle up-trend with a mid pullback so crossover rules fire
            price = price * (1.01 if i < 60 else 0.99)
            db_session.add(MarketCandle(
                asset_id=a.id, provider_id=prov.id, timeframe="1d",
                open_time=now - timedelta(days=90 - i),
                close_time=now - timedelta(days=89 - i),
                open_price=price - 1, high_price=price + 1,
                low_price=price - 2, close_price=price,
                volume=1000.0, quote_volume=price * 1000.0,
                currency="USD", candle_status="CLOSED",
            ))
        symbols.append(a.symbol)
    db_session.commit()
    return symbols


def _post(symbols, strategy, **kw):
    body = {"symbols": symbols, "strategy": strategy, "timeframe": "1d", **kw}
    return client.post("/api/v1/analytics/backtest", json=body)


def test_endpoint_ma_crossover_persists(db_session, rule_universe):
    resp = _post([rule_universe[0]], "MA_CROSSOVER",
                 ma_fast=5, ma_slow=20)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["calculation_status"] == "COMPLETED"
    assert data["strategy"] == "MA_CROSSOVER"
    assert "trade_count" in data["metrics"]

    run = db_session.get(AnalyticsRun, data["run_id"])
    assert run is not None and run.engine_type == "BACKTESTING"
    rows = (db_session.query(BacktestMetrics)
            .filter_by(analytics_run_id=data["run_id"]).all())
    assert {r.metric for r in rows} >= {"total_return", "sharpe", "max_drawdown",
                                        "win_rate", "trade_count"}
    assert all(r.strategy_type == "MA_CROSSOVER" for r in rows)
    assert rows[0].entry_rule == "SMA(5) > SMA(20)"
    assert rows[0].trade_count is not None


def test_endpoint_rsi_threshold_persists(db_session, rule_universe):
    resp = _post([rule_universe[0]], "RSI_THRESHOLD",
                 rsi_period=14, rsi_oversold=40, rsi_overbought=60)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["strategy"] == "RSI_THRESHOLD"
    rows = (db_session.query(BacktestMetrics)
            .filter_by(analytics_run_id=data["run_id"]).all())
    assert rows[0].strategy_type == "RSI_THRESHOLD"
    assert rows[0].exit_rule == "RSI(14) > 60"


def test_endpoint_momentum_persists(db_session, rule_universe):
    resp = _post([rule_universe[1]], "MOMENTUM",
                 momentum_period=10, momentum_threshold=0.0)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["strategy"] == "MOMENTUM"
    rows = (db_session.query(BacktestMetrics)
            .filter_by(analytics_run_id=data["run_id"]).all())
    assert rows[0].entry_rule == "ret(10) > 0"


def test_endpoint_rule_unavailable_when_candles_short(db_session, rule_universe):
    resp = _post([rule_universe[0]], "MA_CROSSOVER", ma_fast=10, ma_slow=500)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["calculation_status"] == "UNAVAILABLE"
    run = db_session.get(AnalyticsRun, data["run_id"])
    assert run.execution_status == "UNAVAILABLE"


def test_endpoint_rule_rejects_multi_symbol(db_session, rule_universe):
    resp = _post(rule_universe[:2], "MA_CROSSOVER")
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "INVALID_CONFIG"


def test_endpoint_buy_hold_still_works(db_session, rule_universe):
    """Phase 1 regression: BUY_HOLD keeps working after the Phase 2 change."""
    resp = _post([rule_universe[0]], "BUY_HOLD")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["calculation_status"] == "COMPLETED"
    assert data["metrics"]["turnover"] == 0.0
    assert data["metrics"]["cost"] == 0.0


def test_endpoint_unknown_strategy_rejected(db_session, rule_universe):
    resp = _post([rule_universe[0]], "NOPE")
    assert resp.status_code == 422
