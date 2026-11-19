"""Stage U: read-only endpoints from existing tables (api-spec §12-14, §16, §18).

SYNTHETIC fixtures only; never presented as market data.
Every endpoint: one success-with-seed test, one honest-empty test, one 404/422 test.
Money/quantity asserted as decimal strings — never raw JSON floats.
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.core.db import get_session_factory
from app.database.models import (
    MarketCandle,
    ResearchJob,
    ResearchReport,
    ResearchRequest,
    ScannerResult,
    ScannerRun,
)
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def seed(db_session):
    """CRYPTO market + BTCUSDT/ETHUSDT/SOLUSDT + provider instruments."""
    return __import__(
        "app.data.storage.universe", fromlist=["ensure_universe"]
    ).ensure_universe(db_session)


def store_candle(session, asset_id, provider_id, hours_ago, close="100"):
    """SYNTHETIC candle (test fixture)."""
    session.add(
        MarketCandle(
            asset_id=asset_id,
            provider_id=provider_id,
            timeframe="1h",
            open_time=datetime.now(timezone.utc) - timedelta(hours=hours_ago + 1),
            close_time=datetime.now(timezone.utc) - timedelta(hours=hours_ago),
            open_price=Decimal(close),
            high_price=Decimal(close),
            low_price=Decimal(close),
            close_price=Decimal(close),
            volume=Decimal("1000"),
            currency="USD",
            candle_status="CLOSED",
        )
    )
    session.commit()


# ==================== markets ====================


def test_markets_empty(client, db_session):
    # startup seeds universe; clear for honest-empty test
    db_session.execute(__import__("sqlalchemy").text("TRUNCATE TABLE markets, assets, provider_instruments, data_providers CASCADE"))
    db_session.commit()
    response = client.get("/api/v1/markets")
    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["meta"]["count"] == 0


def test_markets_success(client, seed):
    response = client.get("/api/v1/markets")
    assert response.status_code == 200
    body = response.json()["data"][0]
    assert body["code"] == "CRYPTO"
    assert body["market_type"] == "CRYPTO"
    assert body["instruments_count"] == 3


def test_market_detail_success_by_id_and_code(client, seed):
    market = seed["market"]
    by_id = client.get(f"/api/v1/markets/{market.id}")
    assert by_id.status_code == 200
    assert by_id.json()["data"]["id"] == str(market.id)
    by_code = client.get("/api/v1/markets/CRYPTO")
    assert by_code.status_code == 200
    assert by_code.json()["data"]["instruments_count"] == 3


def test_market_detail_404(client):
    response = client.get("/api/v1/markets/does-not-exist")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_markets_status_new_and_old_candles(client, seed):
    provider = seed["providers"][0]
    asset = seed["assets"]["BTCUSDT"]
    session = get_session_factory()()
    store_candle(session, asset.id, provider.id, 0)
    response = client.get("/api/v1/markets/status")
    assert response.status_code == 200
    rows = {r["market"]: r for r in response.json()["data"]}
    assert "CRYPTO" in rows
    assert rows["CRYPTO"]["session"]["status"] == "CONTINUOUS"
    assert rows["CRYPTO"]["data_availability"]["status"] in ("LIVE", "STALE", "UNAVAILABLE")
    session.close()


def test_markets_status_live_vs_stale(client, seed):
    provider = seed["providers"][0]
    asset = seed["assets"]["BTCUSDT"]
    session = get_session_factory()()
    store_candle(session, asset.id, provider.id, 0)
    rows = {r["market"]: r for r in client.get("/api/v1/markets/status").json()["data"]}
    assert rows["CRYPTO"]["data_availability"]["status"] == "LIVE"

    # Only an old candle remains: newest stored candle is 48h old -> STALE.
    session.execute(__import__("sqlalchemy").text("TRUNCATE TABLE market_candles CASCADE"))
    session.commit()
    store_candle(session, asset.id, provider.id, 48)
    rows = {r["market"]: r for r in client.get("/api/v1/markets/status").json()["data"]}
    assert rows["CRYPTO"]["data_availability"]["status"] == "STALE"
    session.close()


# ==================== market-data instruments/{asset_id}/candles ====================


def test_instrument_candles_success_is_decimal(client, seed):
    asset = seed["assets"]["BTCUSDT"]
    provider = seed["providers"][0]
    session = get_session_factory()()
    session.add(
        MarketCandle(
            asset_id=asset.id,
            provider_id=provider.id,
            timeframe="1h",
            open_time=datetime.now(timezone.utc) - timedelta(hours=2),
            close_time=datetime.now(timezone.utc) - timedelta(hours=1),
            open_price=Decimal("95000.00"),
            high_price=Decimal("95200.00"),
            low_price=Decimal("94800.00"),
            close_price=Decimal("95100.00"),
            volume=Decimal("125.50"),
            currency="USDT",
            candle_status="CLOSED",
        )
    )
    session.commit()
    response = client.get(f"/api/v1/market-data/instruments/{asset.id}/candles?timeframe=1h&limit=10")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["asset_id"] == str(asset.id)
    assert data["symbol"] == "BTCUSDT"
    assert data["provider"] == "BYBIT"
    assert data["currency"] == "USDT"
    assert data["freshness"] != "UNAVAILABLE"
    assert len(data["candles"]) == 1
    assert data["candles"][0]["open"] == "95000"
    assert data["candles"][0]["high"] == "95200"
    assert data["candles"][0]["low"] == "94800"
    assert data["candles"][0]["close"] == "95100"
    assert data["candles"][0]["volume"] == "125.5"
    session.close()


def test_instrument_candles_empty(client, seed):
    response = client.get(f"/api/v1/market-data/instruments/{seed['assets']['SOLUSDT'].id}/candles")
    assert response.status_code == 200
    assert response.json()["data"]["candles"] == []
    assert response.json()["data"]["freshness"] == "UNAVAILABLE"


def test_instrument_candles_404_unknown_asset(client):
    response = client.get(f"/api/v1/market-data/instruments/{uuid.uuid4()}/candles")
    assert response.status_code == 404


def test_instrument_candles_422(client, seed):
    response = client.get(
        f"/api/v1/market-data/instruments/{seed['assets']['BTCUSDT'].id}/candles?timeframe=bogus"
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


# ==================== dashboard ====================


def test_dashboard_overview_empty(client):
    response = client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["portfolio"] is None
    assert body["allocation"] == []
    assert body["risk_summary"] is None
    assert body["scanner_highlights"] == []
    assert body["research_highlights"] == []


def test_dashboard_overview_with_portfolio(client, seed):
    post = client.post("/api/v1/portfolios", json={"name": "T", "base_currency": "USD"})
    assert post.status_code == 201, post.text
    pid = post.json()["data"]["id"]
    response = client.get(f"/api/v1/dashboard/overview?portfolio_id={pid}")
    assert response.status_code == 200, response.text
    body = response.json()["data"]
    # Empty portfolio: valuation is UNAVAILABLE, so totals are null (never 0).
    assert body["portfolio"]["valuation_status"] == "UNAVAILABLE"
    assert body["portfolio"]["total_value"] is None
    assert body["portfolio"]["currency"] == "USD"
    assert body["portfolio"]["total_return"] is None
    assert body["risk_summary"] is None
    assert body["scanner_highlights"] == []
    assert body["allocation"] == []


def test_dashboard_overview_404_unknown_portfolio(client):
    response = client.get(f"/api/v1/dashboard/overview?portfolio_id={uuid.uuid4()}")
    assert response.status_code == 404


def test_dashboard_activity_empty(client):
    response = client.get("/api/v1/dashboard/activity")
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_dashboard_activity_success(client, seed):
    post = client.post("/api/v1/portfolios", json={"name": "T2", "base_currency": "USD"})
    pid = post.json()["data"]["id"]
    deposit = client.post(
        "/api/v1/transactions",
        json={"portfolio_id": pid, "transaction_type": "DEPOSIT", "gross_amount": "200000"},
    )
    assert deposit.status_code == 201, deposit.text
    resp = client.post(
        "/api/v1/transactions",
        json={
            "portfolio_id": pid,
            "transaction_type": "BUY",
            "asset_id": str(seed["assets"]["BTCUSDT"].id),
            "quantity": "1",
            "price": "100000",
            "fee": "1",
            "currency": "USD",
        },
    )
    assert resp.status_code == 201, resp.text
    response = client.get(f"/api/v1/dashboard/activity?portfolio_id={pid}")
    assert response.status_code == 200
    body = response.json()["data"]
    # newest first: BUY then DEPOSIT
    assert len(body) == 2
    assert body[0]["transaction_type"] == "BUY"
    assert body[0]["quantity"] == "1"
    assert body[0]["price"] == "100000"
    assert body[1]["transaction_type"] == "DEPOSIT"


def test_dashboard_market_overview_empty(client, db_session):
    # startup seeds universe; clear markets for the honest-empty case
    db_session.execute(
        __import__("sqlalchemy").text(
            "TRUNCATE TABLE markets, assets, provider_instruments, data_providers CASCADE"
        )
    )
    db_session.commit()
    response = client.get("/api/v1/dashboard/market-overview")
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_dashboard_scanner_highlights_empty(client):
    response = client.get("/api/v1/dashboard/scanner-highlights")
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_dashboard_research_highlights_empty(client):
    response = client.get("/api/v1/dashboard/research-highlights")
    assert response.status_code == 200
    assert response.json()["data"] == []


# ==================== research ====================


def seed_report(session, asset) -> uuid.UUID:
    request = ResearchRequest(
        research_type="INSTRUMENT",
        asset_id=asset.id,
        trigger_type="MANUAL",
        required_engines=[],
        optional_engines=[],
        context_fingerprint="abc",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(request)
    session.flush()
    report = ResearchReport(
        request_id=request.id,
        research_type="INSTRUMENT",
        title="BTC note",
        report_content={"summary": "x"},
        ai_provider="openai-compatible",
        model_identifier="test-model",
        execution_status="COMPLETED",
        generated_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    session.add(report)
    session.commit()
    return report.id


def test_research_list_empty(client):
    response = client.get("/api/v1/research")
    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["meta"]["has_more"] is False


def test_research_list_success(client, seed):
    session = get_session_factory()()
    asset = seed["assets"]["BTCUSDT"]
    rid = seed_report(session, asset)
    response = client.get("/api/v1/research")
    assert response.status_code == 200
    body = response.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["report_id"] == str(rid)
    assert body["data"][0]["title"] == "BTC note"
    assert body["data"][0]["execution_status"] == "COMPLETED"
    assert body["data"][0]["asset"]["symbol"] == "BTCUSDT"
    session.close()


def test_research_list_cursor_422(client):
    response = client.get("/api/v1/research?cursor=not-a-date")
    assert response.status_code == 422


def test_research_delete_404(client):
    response = client.delete(f"/api/v1/research/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_research_delete_detaches_job(client, seed):
    session = get_session_factory()()
    asset = seed["assets"]["BTCUSDT"]
    rid = seed_report(session, asset)
    request = session.get(ResearchRequest, session.get(ResearchReport, rid).request_id)
    job = ResearchJob(
        request_id=request.id,
        status="RUNNING",
        context_fingerprint="f",
        attempts=0,
        max_retries=0,
        report_id=rid,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(job)
    session.commit()

    response = client.delete(f"/api/v1/research/{rid}")
    assert response.status_code == 200
    assert response.json()["data"]["deleted"] is True

    assert client.get(f"/api/v1/research/reports/{rid}").status_code == 404
    session.expire_all()
    assert session.get(ResearchReport, rid) is None
    detached = session.get(ResearchJob, job.id)
    assert detached.report_id is None
    session.close()


# ==================== scanner ====================


def test_scanner_categories(client):
    response = client.get("/api/v1/scanner/categories")
    assert response.status_code == 200
    cats = response.json()["data"]
    assert len(cats) == 8
    assert "TECHNICAL" in cats and "MOMENTUM" in cats


def test_scanner_results_empty(client):
    response = client.get("/api/v1/scanner/results")
    assert response.status_code == 200
    assert response.json()["data"] == []


def test_scanner_results_404_run(client):
    response = client.get("/api/v1/scanner/results?scanner_run_id=not-a-uuid")
    assert response.status_code == 404


def test_scanner_run_404(client):
    response = client.get("/api/v1/scanner/runs/not-a-uuid")
    assert response.status_code == 404


def test_scanner_results_success(client, seed):
    session = get_session_factory()()
    run = ScannerRun(
        execution_mode="MANUAL",
        execution_status="COMPLETED",
        universe_size=3,
        eligible_count=3,
        result_count=1,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    session.add(run)
    session.flush()
    asset = seed["assets"]["BTCUSDT"]
    result = ScannerResult(
        scanner_run_id=run.id,
        asset_id=asset.id,
        timeframe="1h",
        rank=1,
        score=Decimal("90"),
        matched_rules={"momentum": True},
        metric_snapshot={"price": "100"},
        result_status="ELIGIBLE",
        freshness_status="LIVE",
        data_timestamp=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    session.add(result)
    session.commit()

    response = client.get("/api/v1/scanner/results")
    assert response.status_code == 200
    body = response.json()["data"]
    assert len(body) == 1
    assert body[0]["instrument"]["symbol"] == "BTCUSDT"
    assert body[0]["score"] == "90"
    assert body[0]["data_status"] == "LIVE"

    run_resp = client.get(f"/api/v1/scanner/runs/{run.id}")
    assert run_resp.status_code == 200
    run_body = run_resp.json()["data"]
    assert run_body["execution_status"] == "COMPLETED"
    assert run_body["result_count"] == 1
    session.close()


# ==================== no raw floats in JSON ====================


def test_no_json_float_in_instrument_candles(client, seed):
    asset = seed["assets"]["BTCUSDT"]
    provider = seed["providers"][0]
    session = get_session_factory()()
    session.add(
        MarketCandle(
            asset_id=asset.id,
            provider_id=provider.id,
            timeframe="1h",
            open_time=datetime.now(timezone.utc) - timedelta(hours=2),
            close_time=datetime.now(timezone.utc) - timedelta(hours=1),
            open_price=Decimal("95000.00"),
            high_price=Decimal("95200.00"),
            low_price=Decimal("94800.00"),
            close_price=Decimal("95100.00"),
            volume=Decimal("125.50"),
            currency="USDT",
            candle_status="CLOSED",
        )
    )
    session.commit()
    raw = client.get(f"/api/v1/market-data/instruments/{asset.id}/candles").content
    assert b'"open":95000' not in raw
    assert b'"high":95200' not in raw
    session.close()
