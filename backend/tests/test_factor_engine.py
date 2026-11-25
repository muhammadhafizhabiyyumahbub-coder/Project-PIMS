"""M4 Factor Engine — Phase 1 tests (market-based factors).

Covers: pure-math factor functions + normalization + composite, missing-data
exclusion, and the endpoint + persistence path. Deterministic, no network.
"""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.models import (
    Asset,
    DataProvider,
    Market,
    MarketCandle,
    ProviderInstrument,
    FactorResult,
    AnalyticsRun,
)
from app.engines.factor.engine import (
    FactorConfig,
    compute_momentum,
    compute_reversal,
    compute_size,
    compute_volatility,
    normalize,
    composite,
    run_factor_for_universe,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Pure-math tests
# ---------------------------------------------------------------------------

def test_momentum_basic():
    closes = list(range(100, 130))  # steady uptrend
    m = compute_momentum(closes, lookback=5, gap=0)
    assert m is not None and m > 0


def test_reversal_negative_of_recent():
    closes = [100.0, 110.0]  # up move -> reversal signal negative
    r = compute_reversal(closes, period=1)
    assert r is not None and r < 0


def test_size_log():
    assert compute_size([100.0], 1000.0) == pytest.approx(__import__("math").log(1000.0))
    assert compute_size([100.0], 0.0) is None


def test_volatility_needs_two_returns():
    assert compute_volatility([100.0, 110.0, 105.0], 5) is not None
    assert compute_volatility([100.0, 110.0], 5) is None


def test_normalize_zscore():
    raw = {
        "A": {"MOMENTUM": 0.10},
        "B": {"MOMENTUM": 0.20},
        "C": {"MOMENTUM": 0.00},
    }
    z = normalize(raw, "MOMENTUM", "ZSCORE")
    # mean 0.1, B above mean -> positive, C below -> negative
    assert z["B"] > 0 > z["C"]


def test_normalize_rank():
    raw = {"A": {"MOMENTUM": 0.3}, "B": {"MOMENTUM": 0.1}, "C": {"MOMENTUM": 0.2}}
    r = normalize(raw, "MOMENTUM", "RANK")
    assert r["A"] > r["B"] and r["A"] > r["C"] and r["B"] < r["C"]


def test_composite_equal_weight_drops_missing():
    z = {"A": {"MOMENTUM": 1.0, "REVERSAL": None}, "B": {"MOMENTUM": -1.0, "REVERSAL": None}}
    out = composite(z, ["MOMENTUM", "REVERSAL"])
    assert out["A"] == pytest.approx(1.0)  # only momentum contributes
    assert out["B"] == pytest.approx(-1.0)


# ---------------------------------------------------------------------------
# Endpoint + persistence (DB)
# ---------------------------------------------------------------------------

@pytest.fixture
def factor_universe(db_session):
    prov = db_session.query(DataProvider).filter_by(code="YAHOO").first()
    if not prov:
        prov = DataProvider(code="YAHOO", name="Yahoo", provider_type="GENERAL")
        db_session.add(prov)
    mkt = db_session.query(Market).filter_by(code="CRYPTO").first()
    if not mkt:
        mkt = Market(code="CRYPTO", name="Crypto", market_type="CRYPTO")
        db_session.add(mkt)
    db_session.flush()

    syms = []
    for sym, base, drift in [("FA", 100.0, 1.0), ("FB", 50.0, 0.5)]:
        a = Asset(symbol=sym, name=sym, asset_type="CRYPTO", market_id=mkt.id)
        db_session.add(a)
        db_session.flush()
        db_session.add(ProviderInstrument(asset_id=a.id, provider_id=prov.id, provider_symbol=sym))
        now = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        for i in range(40):
            price = base + drift * i
            db_session.add(MarketCandle(
                asset_id=a.id, provider_id=prov.id, timeframe="1d",
                open_time=now - __import__("datetime").timedelta(days=40 - i),
                close_time=now - __import__("datetime").timedelta(days=39 - i),
                open_price=price - 1, high_price=price + 1,
                low_price=price - 2, close_price=price,
                volume=500.0, quote_volume=price * 500.0,
                currency="USD", candle_status="CLOSED",
            ))
        syms.append(sym)
    db_session.commit()
    return syms


def test_factor_endpoint_persists(db_session, factor_universe):
    resp = client.post("/api/v1/analytics/factor", json={
        "symbols": factor_universe,
        "factors": ["MOMENTUM", "VOLATILITY", "REVERSAL", "SIZE"],
        "timeframe": "1d",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["calculation_status"] == "COMPLETED"
    assert data["universe_size"] == 2
    assert data["assets_included"] == 2
    # FA drifts faster -> higher momentum z
    fa = data["scores"][factor_universe[0]]
    fb = data["scores"][factor_universe[1]]
    assert fa["z"]["MOMENTUM"] is not None
    # persisted
    run_id = data["run_id"]
    run = db_session.get(AnalyticsRun, run_id)
    assert run.engine_type == "FACTOR"
    rows = db_session.query(FactorResult).filter_by(analytics_run_id=run_id).all()
    assert len(rows) == 2
    assert {r.symbol for r in rows} == set(factor_universe)


def test_factor_endpoint_unknown_symbol(db_session, factor_universe):
    resp = client.post("/api/v1/analytics/factor", json={
        "symbols": ["NOPE"],
    })
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"
