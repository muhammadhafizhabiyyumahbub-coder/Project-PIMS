"""Correlation engine tests (correlation-engine-spec §4/§5/§6 + schema-spec §7.5).

Deterministic: synthetic price fixtures (never presented as market data),
pure engine math (no DB, no network) + endpoint/persistence via client fixtures.
"""
import math

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.engines.correlation.engine import (
    AssetSeries,
    compute_pair,
    correlation_matrix,
    rolling_correlation,
    _pearson,
    _returns,
)


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def portfolio_id(client):
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "Correlation Test Portfolio", "base_currency": "USD"},
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


# ---------- pure math (no DB) ----------

def test_pearson_perfect_positive():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [2.0, 4.0, 6.0, 8.0, 10.0]  # y = 2x
    assert _pearson(xs, ys) == pytest.approx(1.0)


def test_pearson_perfect_negative():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [10.0, 8.0, 6.0, 4.0, 2.0]  # y = 12 - 2x
    assert _pearson(xs, ys) == pytest.approx(-1.0)


def test_pearson_no_correlation_is_bounded():
    # independent-ish pattern, value must stay within [-1,1]
    xs = [1, 2, 3, 4]
    ys = [4, 1, 2, 3]
    v = _pearson(xs, ys)
    assert -1.0 <= v <= 1.0


def test_pearson_insufficient_data_returns_none():
    assert _pearson([1.0], [2.0]) is None


def test_pearson_zero_variance_returns_none():
    assert _pearson([1.0, 1.0, 1.0], [1.0, 2.0, 3.0]) is None


def test_simple_returns_formula():
    closes = [100.0, 110.0, 99.0]
    r = _returns(closes, "SIMPLE")
    assert r[0] is None
    assert r[1] == pytest.approx((110.0 - 100.0) / 100.0)
    assert r[2] == pytest.approx((99.0 - 110.0) / 110.0)


def test_log_returns_formula():
    closes = [100.0, 110.0]
    r = _returns(closes, "LOG")
    assert r[1] == pytest.approx(math.log(110.0 / 100.0))


def test_rolling_correlation_window():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    ys = [2.0, 4.0, 6.0, 8.0, 10.0, 12.0]
    rolls = rolling_correlation(xs, ys, window=3)
    # 6 points, window 3 -> 4 values, all ~1.0 (perfect positive)
    assert len(rolls) == 4
    assert all(v == pytest.approx(1.0) for v in rolls)


def test_rolling_correlation_insufficient():
    assert rolling_correlation([1.0, 2.0], [1.0, 2.0], window=5) == []


def test_compute_pair_insufficient_common_data():
    a = AssetSeries(asset_id=1, symbol="A", closes=[100, 110], timestamps=[None, None])
    b = AssetSeries(asset_id=2, symbol="B", closes=[50, 55], timestamps=[None, None])
    # timestamps None -> alignment has no common non-None timestamps
    res = compute_pair(a, b, ret_method="SIMPLE")
    assert res["calculation_status"] == "INSUFFICIENT_DATA"
    assert res["correlation"] is None


def test_correlation_matrix_pairs_i_lt_j():
    from datetime import datetime, timezone
    ts = [datetime(2026, 1, i + 1, tzinfo=timezone.utc) for i in range(5)]
    a = AssetSeries(1, "A", [1, 2, 3, 4, 5], ts)
    b = AssetSeries(2, "B", [2, 4, 6, 8, 10], ts)
    c = AssetSeries(3, "C", [5, 4, 3, 2, 1], ts)
    m = correlation_matrix([a, b, c])
    # 3 assets -> 3 pairs (A,B),(A,C),(B,C)
    assert len(m) == 3
    symbols = [tuple(sorted((p["asset_a_symbol"], p["asset_b_symbol"]))) for p in m]
    assert ("A", "B") in symbols
    assert ("A", "C") in symbols
    assert ("B", "C") in symbols


# ---------- endpoint + persistence (client fixtures) ----------

def test_correlation_endpoint_no_holdings(client, portfolio_id):
    pid = str(portfolio_id)
    resp = client.get(f"/api/v1/analytics/correlation", params={"portfolio_id": pid})
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["calculation_status"] == "INSUFFICIENT_DATA"
    assert body["correlation_matrix"] == []


def test_correlation_endpoint_unknown_portfolio_404(client, seeded_universe):
    import uuid
    resp = client.get(f"/api/v1/analytics/correlation",
                      params={"portfolio_id": str(uuid.uuid4())})
    assert resp.status_code == 404


def test_correlation_endpoint_invalid_id_422(client):
    resp = client.get(f"/api/v1/analytics/correlation",
                      params={"portfolio_id": "not-a-uuid"})
    assert resp.status_code == 422


# ---------- end-to-end persistence (real candles + holdings) ----------

def test_correlation_endpoint_persists_results(client, db_session, portfolio_id, seeded_universe):
    """Portfolio with 2 holdings + stored candles -> engine computes a real
    correlation and persists an analytics_run (CORRELATION) + correlation_results.

    Calls the engine directly on db_session (single session) to avoid cross-session
    visibility issues; endpoint smoke covered by the no-holdings/404/422 tests."""
    from app.data.storage.candles import upsert_candles
    from tests.conftest import synthetic_candles, to_storage
    from app.database.models import Holding, AnalyticsRun, CorrelationResult
    from app.engines.correlation.engine import run_correlation_for_portfolio

    universe = seeded_universe
    provider = universe["providers"][1]  # YAHOO (crypto_provider default; matches resolve_provider_id)
    assets = list(universe["assets"].values())
    if len(assets) < 2:
        pytest.skip("need >=2 seeded assets")
    a, b = assets[0], assets[1]

    # distinct synthetic series so correlation is defined (1h, matches seeded mapping)
    for asset, drift in [(a, 0.002), (b, 0.006)]:
        upsert_candles(
            db_session, asset_id=asset.id, provider_id=provider.id,
            timeframe="1h", normalized=to_storage(synthetic_candles(count=60, drift=drift)),
            currency="USD", feed_type="TEST",
        )
    db_session.commit()

    # add holdings for the portfolio
    db_session.add(Holding(portfolio_id=portfolio_id, asset_id=a.id, quantity=10,
                           average_cost=100.0, calculation_status="VALID"))
    db_session.add(Holding(portfolio_id=portfolio_id, asset_id=b.id, quantity=10,
                           average_cost=50.0, calculation_status="VALID"))
    db_session.commit()

    holdings = db_session.query(Holding).filter_by(portfolio_id=portfolio_id).all()
    result = run_correlation_for_portfolio(
        db_session, portfolio_id, holdings,
        timeframe="1h", ret_method="SIMPLE", rolling_window=0, limit=300,
    )
    db_session.commit()

    assert result["calculation_status"] == "COMPLETED"
    assert result["pairs_computed"] >= 1
    pair = result["correlation_matrix"][0]
    assert pair["correlation"] is not None
    assert -1.0 <= pair["correlation"] <= 1.0

    # persisted to DB
    run_id = result["analytics_run_id"]
    run = db_session.get(AnalyticsRun, run_id)
    assert run is not None
    assert run.engine_type == "CORRELATION"
    rows = db_session.query(CorrelationResult).filter_by(analytics_run_id=run_id).all()
    assert len(rows) >= 1
    assert all(-1.0 <= float(r.correlation_value) <= 1.0 for r in rows)
