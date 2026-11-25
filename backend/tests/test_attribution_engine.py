"""M4 Attribution Engine — Phase 1 tests (asset-level attribution).

Covers: pure-math contribution + conservation sum==R, active vs benchmark,
and the endpoint + persistence path. Deterministic; no network.
"""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.models import (
    Asset,
    DataProvider,
    Holding,
    Market,
    MarketCandle,
    ProviderInstrument,
    AttributionResult,
    AnalyticsRun,
    Portfolio,
)
from app.engines.attribution.engine import (
    run_attribution_for_portfolio,
    _simple_return,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Pure-math tests
# ---------------------------------------------------------------------------

def test_simple_return_basic():
    r = _simple_return(100.0, 110.0)
    assert r == pytest.approx(0.1)


def test_simple_return_zero_start():
    assert _simple_return(0.0, 110.0) is None
    assert _simple_return(None, 110.0) is None


# ---------------------------------------------------------------------------
# Endpoint + persistence (DB)
# ---------------------------------------------------------------------------

@pytest.fixture
def attribution_setup(db_session):
    """Portfolio with two holdings, each with candles and invested value."""
    # Provider
    prov = db_session.query(DataProvider).filter_by(code="YAHOO").first()
    if not prov:
        prov = DataProvider(code="YAHOO", name="Yahoo", provider_type="GENERAL")
        db_session.add(prov)

    # Market
    mkt = db_session.query(Market).filter_by(code="CRYPTO").first()
    if not mkt:
        mkt = Market(code="CRYPTO", name="Crypto", market_type="CRYPTO")
        db_session.add(mkt)

    # Portfolio
    pf = Portfolio(
        name="Attribution Test",
        reporting_currency="USD",
        status="ACTIVE",
    )
    db_session.add(pf)
    db_session.flush()

    # Assets
    assets = []
    for sym, base, qty, avg_cost in [
        ("ATTR_A", 100.0, 10.0, 100.0),  # invested = 1000
        ("ATTR_B", 50.0, 5.0, 50.0),     # invested = 250
    ]:
        a = Asset(symbol=sym, name=sym, asset_type="CRYPTO", market_id=mkt.id)
        db_session.add(a)
        db_session.flush()
        db_session.add(ProviderInstrument(asset_id=a.id, provider_id=prov.id, provider_symbol=sym))
        # Holding
        db_session.add(Holding(
            portfolio_id=pf.id,
            asset_id=a.id,
            quantity=qty,
            average_cost=avg_cost,
            cost_basis=avg_cost * qty,
            cost_currency="USD",
            calculation_status="VALID",
        ))
        assets.append(a)

    db_session.flush()

    # Candles for each asset: uptrend for A, flat for B
    now = datetime.now(timezone.utc)
    period_start = now - timedelta(days=10)
    period_end = now

    for a, base, drift in [(assets[0], 100.0, 1.0), (assets[1], 50.0, 0.0)]:
        for i in range(15):
            price = base + drift * i
            db_session.add(MarketCandle(
                asset_id=a.id, provider_id=prov.id, timeframe="1d",
                open_time=period_start + timedelta(days=i),
                close_time=period_start + timedelta(days=i + 1),
                open_price=price - 1, high_price=price + 1,
                low_price=price - 2, close_price=price,
                volume=500.0, quote_volume=price * 500.0,
                currency="USD", candle_status="CLOSED",
            ))

    db_session.commit()
    return {
        "db_session": db_session,
        "portfolio_id": str(pf.id),
        "asset_a": str(assets[0].id),
        "asset_b": str(assets[1].id),
        "symbol_a": assets[0].symbol,
        "symbol_b": assets[1].symbol,
        "period_start": period_start,
        "period_end": period_end,
    }


def test_attribution_pure_math_conservation(attribution_setup):
    """Test that sum of contributions equals portfolio return."""
    setup = attribution_setup
    db_session = attribution_setup["db_session"] if "db_session" in attribution_setup else None
    # Use the engine function directly
    result = run_attribution_for_portfolio(
        db_session,
        setup["portfolio_id"],
        period_start=setup["period_start"],
        period_end=setup["period_end"],
        timeframe="1d",
    )

    assert result["calculation_status"] == "COMPLETED"
    total_return = result["total_return"]
    # Sum of contributions should equal total_return (within float tolerance)
    contrib_sum = sum(b["contribution"] for b in result["breakdown"] if b["contribution"] is not None)
    assert abs(total_return - contrib_sum) < 1e-10


def test_attribution_with_benchmark(attribution_setup):
    """Test active contribution vs benchmark."""
    setup = attribution_setup
    db_session = attribution_setup["db_session"] if "db_session" in attribution_setup else None

    result = run_attribution_for_portfolio(
        db_session,
        setup["portfolio_id"],
        benchmark_asset_id=setup["asset_a"],  # use asset A as benchmark
        period_start=setup["period_start"],
        period_end=setup["period_end"],
        timeframe="1d",
    )

    assert result["calculation_status"] == "COMPLETED"
    assert result["benchmark_return"] is not None
    # Active return = portfolio return - benchmark return
    assert result["active_return"] == pytest.approx(result["total_return"] - result["benchmark_return"])
    # Each active contribution = contribution - benchmark_return
    for b in result["breakdown"]:
        if b["contribution"] is not None:
            assert b["active_contribution"] == pytest.approx(b["contribution"] - result["benchmark_return"])


def test_attribution_endpoint_persists(db_session, attribution_setup):
    """Test endpoint persists analytics_runs(ATTRIBUTION) + attribution_results."""
    setup = attribution_setup

    resp = client.post("/api/v1/analytics/attribution", json={
        "portfolio_id": setup["portfolio_id"],
        "period_start": setup["period_start"].isoformat(),
        "period_end": setup["period_end"].isoformat(),
        "timeframe": "1d",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "COMPLETED"
    assert "run_id" in data
    assert "breakdown" in data
    assert len(data["breakdown"]) == 2

    # Check persistence
    run_id = data["run_id"]
    run = db_session.get(AnalyticsRun, run_id)
    assert run is not None
    assert run.engine_type == "ATTRIBUTION"

    rows = db_session.query(AttributionResult).filter_by(analytics_run_id=run_id).all()
    assert len(rows) == 2
    symbols = {r.symbol for r in rows}
    assert symbols == {setup["symbol_a"], setup["symbol_b"]}
    for r in rows:
        assert r.contribution is not None
        # active_contribution is None when no benchmark


def test_attribution_endpoint_with_benchmark(db_session, attribution_setup):
    """Test endpoint with benchmark asset."""
    setup = attribution_setup

    resp = client.post("/api/v1/analytics/attribution", json={
        "portfolio_id": setup["portfolio_id"],
        "benchmark_asset_id": setup["asset_a"],
        "period_start": setup["period_start"].isoformat(),
        "period_end": setup["period_end"].isoformat(),
        "timeframe": "1d",
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "COMPLETED"
    assert data["active_return"] is not None
    for item in data["breakdown"]:
        assert item["active_contribution"] is not None


def test_attribution_insufficient_data_no_holdings(db_session):
    """Test INSUFFICIENT_DATA when portfolio has no holdings."""
    pf = Portfolio(name="Empty PF", reporting_currency="USD", status="ACTIVE")
    db_session.add(pf)
    db_session.commit()

    resp = client.post("/api/v1/analytics/attribution", json={
        "portfolio_id": str(pf.id),
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "INSUFFICIENT_DATA"
    assert data["breakdown"] == []


def test_attribution_insufficient_data_no_candles(db_session):
    """Test INSUFFICIENT_DATA when holdings exist but no candles."""
    # Provider + Market
    prov = DataProvider(code="YAHOO", name="Yahoo", provider_type="GENERAL")
    mkt = Market(code="CRYPTO", name="Crypto", market_type="CRYPTO")
    db_session.add_all([prov, mkt])
    db_session.flush()

    pf = Portfolio(name="No Candles PF", reporting_currency="USD", status="ACTIVE")
    db_session.add(pf)
    db_session.flush()

    a = Asset(symbol="NOCANDLE", name="No Candle", asset_type="CRYPTO", market_id=mkt.id)
    db_session.add(a)
    db_session.flush()

    db_session.add(ProviderInstrument(asset_id=a.id, provider_id=prov.id, provider_symbol="NOCANDLE"))
    db_session.add(Holding(
        portfolio_id=pf.id,
        asset_id=a.id,
        quantity=10.0,
        average_cost=100.0,
        cost_basis=1000.0,
        cost_currency="USD",
        calculation_status="VALID",
    ))
    db_session.commit()

    resp = client.post("/api/v1/analytics/attribution", json={
        "portfolio_id": str(pf.id),
    })
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "INSUFFICIENT_DATA"


def test_attribution_determinism(db_session, attribution_setup):
    """Two runs with same inputs produce identical results."""
    setup = attribution_setup

    resp1 = client.post("/api/v1/analytics/attribution", json={
        "portfolio_id": setup["portfolio_id"],
        "period_start": setup["period_start"].isoformat(),
        "period_end": setup["period_end"].isoformat(),
        "timeframe": "1d",
    })
    resp2 = client.post("/api/v1/analytics/attribution", json={
        "portfolio_id": setup["portfolio_id"],
        "period_start": setup["period_start"].isoformat(),
        "period_end": setup["period_end"].isoformat(),
        "timeframe": "1d",
    })

    data1 = resp1.json()["data"]
    data2 = resp2.json()["data"]

    # Different run IDs
    assert data1["run_id"] != data2["run_id"]
    # But same calculations
    assert data1["total_return"] == data2["total_return"]
    for b1, b2 in zip(data1["breakdown"], data2["breakdown"]):
        assert b1["contribution"] == b2["contribution"]
        assert b1["active_contribution"] == b2["active_contribution"]