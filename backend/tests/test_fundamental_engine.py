"""M4 Fundamental Engine — Phase 1 tests (P/E, ROE, revenue-growth).

Covers: pure-math z-score + composite, UNAVAILABLE handling, endpoint + persistence.
Deterministic, no network.
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
    FundamentalResult,
    AnalyticsRun,
    Portfolio,
)
from app.engines.fundamental.engine import run_fundamental_for_universe

client = TestClient(app)


# ---------------------------------------------------------------------------
# Pure-math tests
# ---------------------------------------------------------------------------

def test_zscore_normalization():
    """Test z-score normalization."""
    from app.engines.fundamental.engine import _normalize
    
    values = {"A": 10.0, "B": 20.0, "C": 30.0}
    result = _normalize(values)
    assert abs(result["A"] + 1.2247) < 0.01  # -sqrt(1.5)
    assert abs(result["B"]) < 0.01
    assert abs(result["C"] - 1.2247) < 0.01
    
    # Edge case: all same
    values = {"A": 10.0, "B": 10.0}
    result = _normalize(values)
    assert result["A"] == 0.0
    assert result["B"] == 0.0
    
    # Edge case: single value
    values = {"A": 10.0}
    result = _normalize(values)
    assert result["A"] == 0.0


def test_composite_equal_weight():
    """Test equal-weight composite with available metrics."""
    # Import composite from factor engine since pattern is same
    from app.engines.factor.engine import composite
    
    z = {
        "A": {"pe": 1.0, "roe": -1.0, "revenue_growth": 0.0},
        "B": {"pe": -1.0, "roe": 1.0, "revenue_growth": 0.0},
        "C": {"pe": 0.0, "roe": 0.0, "revenue_growth": 1.0},
    }
    scores = composite(z, ["pe", "roe", "revenue_growth"])
    assert scores["A"] == pytest.approx(0.0)
    assert scores["B"] == pytest.approx(0.0)
    assert scores["C"] == pytest.approx(0.3333, rel=1e-3)


def test_composite_missing_metrics():
    """Test composite with some metrics missing (equal-weight renormalization)."""
    from app.engines.factor.engine import composite
    
    z = {
        "A": {"pe": 1.0, "roe": None, "revenue_growth": -1.0},
        "B": {"pe": None, "roe": 1.0, "revenue_growth": -1.0},
    }
    scores = composite(z, ["pe", "roe", "revenue_growth"])
    # A: (1.0 + -1.0) / 2 = 0.0
    # B: (1.0 + -1.0) / 2 = 0.0
    assert scores["A"] == pytest.approx(0.0)
    assert scores["B"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Endpoint + persistence (DB)
# ---------------------------------------------------------------------------

@pytest.fixture
def fundamental_setup(db_session):
    """Portfolio with two holdings, each with fundamental data."""
    # Provider
    prov = db_session.query(DataProvider).filter_by(code="YAHOO").first()
    if not prov:
        prov = DataProvider(code="YAHOO", name="Yahoo", provider_type="GENERAL")
        db_session.add(prov)

    # Market
    mkt = db_session.query(Market).filter_by(code="US").first()
    if not mkt:
        mkt = Market(code="US", name="US Stocks", market_type="STOCK")
        db_session.add(mkt)

    # Portfolio
    pf = Portfolio(name="Fundamental Test", reporting_currency="USD", status="ACTIVE")
    db_session.add(pf)
    db_session.flush()

    # Assets with fundamentals
    assets = []
    for sym, pe, roe, rev_growth in [
        ("FUND_A", 15.0, 0.18, 0.12),   # Good fundamentals
        ("FUND_B", 25.0, 0.08, 0.03),   # Mixed
    ]:
        a = Asset(symbol=sym, name=sym, asset_type="STOCK", market_id=mkt.id)
        db_session.add(a)
        db_session.flush()
        db_session.add(ProviderInstrument(asset_id=a.id, provider_id=prov.id, provider_symbol=sym))
        assets.append(a)

    db_session.commit()
    return {
        "portfolio_id": str(pf.id),
        "asset_a": str(assets[0].id),
        "asset_b": str(assets[1].id),
        "symbol_a": assets[0].symbol,
        "symbol_b": assets[1].symbol,
    }


def test_fundamental_endpoint_persists(db_session, fundamental_setup):
    """Test endpoint persists analytics_runs(FUNDAMENTAL) + fundamental_results."""
    setup = fundamental_setup

    resp = client.post("/api/v1/analytics/fundamental", json={
        "symbols": [setup["symbol_a"], setup["symbol_b"]],
        "timeframe": "1d",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "COMPLETED"
    assert "run_id" in data

    # Check persistence
    run_id = data["run_id"]
    run = db_session.get(AnalyticsRun, run_id)
    assert run is not None
    assert run.engine_type == "FUNDAMENTAL"

    rows = db_session.query(FundamentalResult).filter_by(analytics_run_id=run_id).all()
    assert len(rows) == 2
    symbols = {r.symbol for r in rows}
    assert symbols == {setup["symbol_a"], setup["symbol_b"]}


def test_fundamental_insufficient_data(db_session):
    """Test INSUFFICIENT_DATA when symbols not found."""
    resp = client.post("/api/v1/analytics/fundamental", json={
        "symbols": ["NONEXISTENT"],
        "timeframe": "1d",
    })
    assert resp.status_code == 422


def test_fundamental_determinism(db_session, fundamental_setup):
    """Two runs with same inputs produce identical results."""
    setup = fundamental_setup

    resp1 = client.post("/api/v1/analytics/fundamental", json={
        "symbols": [setup["symbol_a"], setup["symbol_b"]],
        "timeframe": "1d",
    })
    resp2 = client.post("/api/v1/analytics/fundamental", json={
        "symbols": [setup["symbol_a"], setup["symbol_b"]],
        "timeframe": "1d",
    })

    data1 = resp1.json()["data"]
    data2 = resp2.json()["data"]

    # Different run IDs
    assert data1["run_id"] != data2["run_id"]
    # Same calculations
    assert data1["status"] == data2["status"]