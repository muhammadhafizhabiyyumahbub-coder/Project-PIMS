"""Analytics persistence integration tests (Stage Q/R).

SYNTHETIC fixtures only (from seeded universe); never presented as market data.
Hand-computed expectations are written in comments where exact.
"""
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.models import MarketCandle


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def portfolio_id(client):
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "Analytics Test Portfolio", "base_currency": "USD"},
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def deposit(client, pid, amount, key=None):
    headers = {"Idempotency-Key": key} if key else {}
    return client.post(
        "/api/v1/transactions",
        json={"portfolio_id": pid, "transaction_type": "DEPOSIT", "gross_amount": amount},
        headers=headers,
    )


def trade(client, pid, ttype, asset_id, qty, price, fee, key=None):
    headers = {"Idempotency-Key": key} if key else {}
    return client.post(
        "/api/v1/transactions",
        json={
            "portfolio_id": pid,
            "asset_id": asset_id,
            "transaction_type": ttype,
            "quantity": qty,
            "price": price,
            "fee": fee,
        },
        headers=headers,
    )


def store_candle(db_session, asset_id, provider_id, close, open_time):
    db_session.add(
        MarketCandle(
            asset_id=asset_id,
            provider_id=provider_id,
            timeframe="1h",
            open_price=close,
            high_price=close,
            low_price=close,
            close_price=close,
            volume=1000.0,
            quote_volume=close * D(1000),
            candle_status="CLOSED",
            open_time=open_time,
            close_time=open_time + timedelta(hours=1),
            currency="USD",
        )
    )
    db_session.commit()


def snapshot(client, pid, key):
    return client.post(f"/api/v1/portfolios/{pid}/snapshots", headers={"Idempotency-Key": key})


def post_run(client, pid, analysis_type, **params):
    body = {"analysis_type": analysis_type}
    body.update(params)
    return client.post(f"/api/v1/portfolios/{pid}/analytics/runs", json=body)


# ---------------------------------------------------------------------------
# performance
# ---------------------------------------------------------------------------


def test_persist_performance_matches_on_demand(client, db_session, portfolio_id, seeded_universe):
    """Deposit 1000, BUY 1 @100 fee 0; candles close 120 then 150.

    Snapshot 1 total 1020, snapshot 2 total 1050 -> TWR = 1050/1020 - 1
    = 0.029411764705882..., simple return identical (no flows between snapshots).
    Persisted row must equal on-demand result bit-for-bit (as decimal strings).
    """
    asset = seeded_universe["assets"]["BTCUSDT"]
    provider = seeded_universe["providers"][1]
    pid = portfolio_id
    assert deposit(client, pid, "1000", key="an-perf-dep").status_code == 201
    assert trade(client, pid, "BUY", str(asset.id), "1", "100", "0", key="an-perf-buy").status_code == 201
    now = datetime.now(tz=UTC)
    store_candle(
        db_session,
        asset.id,
        provider.id,
        D(120),
        now - timedelta(hours=2),
    )
    store_candle(
        db_session,
        asset.id,
        provider.id,
        D(150),
        now - timedelta(hours=1),
    )
    assert snapshot(client, pid, "an-perf-snap1").status_code == 201
    assert snapshot(client, pid, "an-perf-snap2").status_code == 201

    start = now - timedelta(hours=3)
    end = now

    on_demand = client.get(
        f"/api/v1/portfolios/{pid}/performance",
        params={"start": start.isoformat(), "end": end.isoformat()},
    )
    assert on_demand.status_code == 200, on_demand.text
    on_demand_data = on_demand.json()["data"]

    response = post_run(client, pid, "performance", start=start.isoformat(), end=end.isoformat())
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["run"]["engine_type"] == "PERFORMANCE"
    assert data["run"]["input_metadata"]["portfolio_id"] == pid
    assert data["results"], "expected at least one performance result row"

    row = data["results"][0]
    # Numbers identical to on-demand (DB scale is 10).
    assert D(row["total_return"]) == pytest.approx(D(on_demand_data["twr"]), abs=D("1e-10"))
    assert row["daily_return"] is None
    assert D(row["realized_pnl"]) == pytest.approx(D(on_demand_data["realized_pnl"]), abs=D("1e-12"))
    assert D(row["unrealized_pnl"]) == pytest.approx(D(on_demand_data["unrealized_pnl"]), abs=D("1e-12"))
    assert row["cagr"] is None and on_demand_data["cagr"] is None  # < 365 days
    assert row["methodology"] == "time_weighted_return"
    # FK chain intact: result points at this run, run belongs to portfolio.
    assert row["analytics_run_id"] == data["run"]["id"]

    # Detail endpoint returns the same stored row.
    detail = client.get(f"/api/v1/portfolios/{pid}/analytics/runs/{data['run']['id']}")
    assert detail.status_code == 200, detail.text
    detail_data = detail.json()["data"]
    assert detail_data["run"]["id"] == data["run"]["id"]
    assert len(detail_data["results"]) == 1
    assert D(detail_data["results"][0]["total_return"]) == pytest.approx(
        D(on_demand_data["twr"]), abs=D("1e-10")
    )

    # No JSON floats anywhere.
    import json as _json

    raw = _json.dumps(response.json())
    assert not re.search(r'":\s*-?\d+\.\d+', raw), raw


def test_persist_performance_unavailable_stores_null(client, portfolio_id):
    """Explicit period but no snapshots: totals NULL, status UNAVAILABLE, not 0."""
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 1, 31, tzinfo=UTC)
    response = post_run(
        client, portfolio_id, "performance", start=start.isoformat(), end=end.isoformat()
    )
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    row = data["results"][0]
    assert row["total_return"] is None
    assert row["realized_pnl"] is None
    assert row["cagr"] is None
    assert row["result_metadata"]["return_status"] == "UNAVAILABLE"
    assert row["result_metadata"]["twr_reason"]
    assert row["period_start"] == start.isoformat()
    assert row["period_end"] == end.isoformat()


# ---------------------------------------------------------------------------
# risk
# ---------------------------------------------------------------------------


def test_persist_risk_matches_on_demand(client, db_session, portfolio_id, seeded_universe):
    """40 daily closes -> 39 returns >= 30 -> risk row equals on-demand metrics."""
    asset = seeded_universe["assets"]["BTCUSDT"]
    provider = seeded_universe["providers"][1]
    pid = portfolio_id
    assert deposit(client, pid, "10000", key="an-risk-dep").status_code == 201
    assert trade(client, pid, "BUY", str(asset.id), "1", "100", "0", key="an-risk-buy").status_code == 201

    closes = [100.0]
    for i in range(39):
        closes.append(closes[-1] * (1.10 if i % 2 == 0 else 0.95))
    base = datetime.now(tz=UTC) - timedelta(days=len(closes) + 2)
    for i, close in enumerate(closes):
        store_candle(
            db_session,
            asset.id,
            provider.id,
            D(str(close)),
            base + timedelta(days=i),
        )

    on_demand = client.get(f"/api/v1/portfolios/{pid}/risk?window=90")
    assert on_demand.status_code == 200, on_demand.text
    on_demand_data = on_demand.json()["data"]

    response = post_run(client, pid, "risk", window_days=90)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["run"]["engine_type"] == "RISK"

    row = data["results"][0]
    assert row["observation_period"] == "90d"
    assert D(row["volatility"]) == pytest.approx(D(on_demand_data["metrics"]["volatility"]), abs=D("1e-10"))
    assert D(row["max_drawdown"]) == pytest.approx(D(on_demand_data["metrics"]["max_drawdown"]), abs=D("1e-10"))
    assert D(row["value_at_risk"]) == pytest.approx(D(on_demand_data["metrics"]["var_95"]), abs=D("1e-10"))
    assert row["result_metadata"]["method"] == "current_weights_buy_and_hold_approximation"
    assert row["result_metadata"]["risk_free_rate"] == on_demand_data["risk_free_rate"]
    assert row["result_metadata"]["annualization"] == on_demand_data["annualization"]
    assert row["result_metadata"]["observation_count"] == on_demand_data["return_count"]

    detail = client.get(f"/api/v1/portfolios/{pid}/analytics/runs/{data['run']['id']}")
    assert detail.status_code == 200
    assert D(detail.json()["data"]["results"][0]["volatility"]) == pytest.approx(
        D(on_demand_data["metrics"]["volatility"]), abs=D("1e-10")
    )


def test_persist_risk_unavailable_stores_null(client, portfolio_id):
    """Empty portfolio -> risk row with NULL metrics + UNAVAILABLE status."""
    response = post_run(client, portfolio_id, "risk", window_days=90)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    row = data["results"][0]
    assert row["volatility"] is None
    assert row["max_drawdown"] is None
    assert row["value_at_risk"] is None
    assert row["result_metadata"]["data_status"] == "UNAVAILABLE"
    assert row["result_metadata"]["data_status_reason"]


# ---------------------------------------------------------------------------
# allocation
# ---------------------------------------------------------------------------


def test_persist_allocation_matches_on_demand(client, db_session, portfolio_id, seeded_universe):
    """Deposit 1000, BUY 1 @100: allocation rows equal on-demand values."""
    asset = seeded_universe["assets"]["BTCUSDT"]
    provider = seeded_universe["providers"][1]
    pid = portfolio_id
    assert deposit(client, pid, "1000", key="an-alloc-dep").status_code == 201
    assert trade(client, pid, "BUY", str(asset.id), "1", "100", "0", key="an-alloc-buy").status_code == 201
    store_candle(
        db_session,
        asset.id,
        provider.id,
        D(120),
        datetime.now(tz=UTC) - timedelta(hours=1),
    )

    on_demand = client.get(f"/api/v1/portfolios/{pid}/allocation")
    assert on_demand.status_code == 200, on_demand.text
    on_demand_data = on_demand.json()["data"]

    response = post_run(client, pid, "allocation")
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["run"]["engine_type"] == "ALLOCATION"
    assert len(data["results"]) >= 1, "expected allocation rows: at least cash + asset"

    types = {row["allocation_type"] for row in data["results"]}
    assert {"ASSET", "CASH"} <= types

    asset_rows = [r for r in data["results"] if r["allocation_type"] == "ASSET"]
    assert asset_rows
    asset_row = asset_rows[0]
    assert D(asset_row["market_value"]) == D(on_demand_data["categories"]["individual_asset"][0]["market_value"])
    assert D(asset_row["allocation_percentage"]) == D(on_demand_data["categories"]["individual_asset"][0]["weight"])
    assert asset_row["allocation_key"] == "BTCUSDT"
    assert asset_row["result_metadata"]["weight_base"] == on_demand_data["weight_base"]

    cash_rows = [r for r in data["results"] if r["allocation_type"] == "CASH"]
    assert cash_rows
    assert D(cash_rows[0]["market_value"]) == D(on_demand_data["categories"]["cash"]["value"])

    # Detail endpoint.
    detail = client.get(f"/api/v1/portfolios/{pid}/analytics/runs/{data['run']['id']}")
    assert detail.status_code == 200
    assert {r["allocation_type"] for r in detail.json()["data"]["results"]} == types


# ---------------------------------------------------------------------------
# list / detail / validation
# ---------------------------------------------------------------------------


def test_list_runs_paginated_and_ordered(client, portfolio_id):
    """Newest first; limit + cursor pagination."""
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 1, 31, tzinfo=UTC)
    for i in range(3):
        post_run(client, portfolio_id, "performance", start=start.isoformat(), end=end.isoformat())

    page1 = client.get(f"/api/v1/portfolios/{portfolio_id}/analytics/runs?limit=2")
    assert page1.status_code == 200, page1.text
    p1 = page1.json()["data"]
    assert len(p1) == 2
    assert page1.json()["meta"]["pagination"]["has_more"] is True
    cursor = page1.json()["meta"]["pagination"]["next_cursor"]

    page2 = client.get(
        f"/api/v1/portfolios/{portfolio_id}/analytics/runs?limit=2&cursor={cursor}"
    )
    assert page2.status_code == 200
    p2 = page2.json()["data"]
    assert len(p2) == 1
    assert page2.json()["meta"]["pagination"]["has_more"] is False
    assert p1[0]["id"] != p2[0]["id"]


def test_detail_run_not_found_404(client, portfolio_id):
    response = client.get(f"/api/v1/portfolios/{portfolio_id}/analytics/runs/{uuid.uuid4()}")
    assert response.status_code == 404


def test_detail_run_wrong_portfolio_404(client, portfolio_id):
    other = client.post(
        "/api/v1/portfolios", json={"name": "Other", "base_currency": "USD"}
    ).json()["data"]["id"]
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 1, 31, tzinfo=UTC)
    run = post_run(client, portfolio_id, "performance", start=start.isoformat(), end=end.isoformat())
    assert run.status_code == 201
    run_id = run.json()["data"]["run"]["id"]

    response = client.get(f"/api/v1/portfolios/{other}/analytics/runs/{run_id}")
    assert response.status_code == 404


def test_unknown_analysis_type_422(client, portfolio_id):
    response = post_run(client, portfolio_id, "not_a_real_type")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_unknown_portfolio_404(client):
    response = client.post(
        "/api/v1/portfolios/" + str(uuid.uuid4()) + "/analytics/runs",
        json={"analysis_type": "risk"},
    )
    assert response.status_code == 404
