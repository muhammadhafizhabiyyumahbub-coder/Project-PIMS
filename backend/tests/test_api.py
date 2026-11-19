"Seam 4: REST API contract via TestClient (envelope, honesty of dashboard)."
import pytest

from app.main import app


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    # Migrations already applied; skip startup event DB churn by calling routes
    # directly through TestClient (startup handler runs only for lifespans).
    with TestClient(app) as c:
        yield c


def test_health_envelope(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) >= {"data", "meta"}
    assert body["data"]["status"] == "ok"


def test_ready_checks_database(client):
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["data"]["database"] == "connected"


def test_candles_unknown_symbol_404(client, db_session):
    response = client.get("/api/v1/market-data/candles", params={"symbol": "NOPE"})
    assert response.status_code == 404


def test_opportunities_empty_without_scanner_results(client, db_session):
    """Dashboard must not fabricate anything when scanner has never run."""
    response = client.get("/api/v1/dashboard/instrument-opportunities")
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["meta"]["count"] == 0


def test_opportunities_shape_and_truthfulness(client, analyzed_universe):
    response = client.get("/api/v1/dashboard/instrument-opportunities")
    assert response.status_code == 200
    rows = response.json()["data"]
    assert len(rows) == 3

    required_fields = {
        "scanner_result_id",
        "instrument",
        "market",
        "current_price",
        "daily_change_pct",
        "scanner_score",
        "market_regime",
        "risk_status",
        "approval_status",
        "passed_by",
        "updated_at",
        "data_status",
    }
    row = rows[0]
    assert required_fields.issubset(row.keys())
    # Traceable values: every passed engine actually has a READY state.
    for engine in row["passed_by"]:
        assert row["engine_readiness"][engine]["label"] == "PASSED"
    # Optional engines never appear as PASSED.
    for engine in ("CORRELATION", "FUNDAMENTAL", "SENTIMENT"):
        assert row["engine_readiness"][engine]["label"] == "NOT AVAILABLE"
    assert row["market_regime"] in {"BULLISH", "BEARISH", "SIDEWAYS"}
    assert row["data_status"] in {"LIVE", "STALE"}
    assert row["approval_status"] in {"QUALIFIED", "PARTIAL", "NOT_QUALIFIED", "STALE"}
    # The id must be usable for the qualification detail the scanner page expands.
    detail = client.get(f"/api/v1/scanner/results/{row['scanner_result_id']}/qualification")
    assert detail.status_code == 200
    assert detail.json()["data"]["instrument"] == row["instrument"]["symbol"]


def test_opportunities_filter_by_market(client, analyzed_universe):
    response = client.get(
        "/api/v1/dashboard/instrument-opportunities", params={"market": "CRYPTO"}
    )
    assert response.json()["meta"]["count"] == 3
    response = client.get(
        "/api/v1/dashboard/instrument-opportunities", params={"market": "IDX"}
    )
    assert response.json()["data"] == []


def test_opportunities_sorting_by_score(client, analyzed_universe):
    response = client.get("/api/v1/dashboard/instrument-opportunities")
    scores = [row["scanner_score"] for row in response.json()["data"]]
    assert scores == sorted(scores, reverse=True)


def test_research_request_blocked_without_engines(client, seeded_universe):
    response = client.post(
        "/api/v1/research/requests", json={"symbol": "BTCUSDT", "timeframe": "1h"}
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["job"]["status"] == "BLOCKED"
    assert data["job"]["error_code"] == "ENGINES_NOT_READY"


def test_research_request_unknown_symbol(client, db_session):
    response = client.post("/api/v1/research/requests", json={"symbol": "NOPE"})
    assert response.json()["error"]["code"] == "UNKNOWN_SYMBOL"


def test_research_request_valid_body_enforced(client, db_session, analyzed_universe):
    response = client.post(
        "/api/v1/research/requests",
        json={"symbol": "BTCUSDT", "bogus_field": 1},
    )
    assert response.status_code == 422  # pydantic extra=forbid


def test_research_report_endpoint_404(client, db_session):
    response = client.get("/api/v1/research/reports/00000000-0000-0000-0000-000000000000")
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_scanner_qualification_endpoint(client, analyzed_universe):
    from app.core.db import get_session_factory
    from app.database.models import Asset
    from app.qualification.service import _latest_scanner_result

    session = get_session_factory()()
    try:
        btc = session.query(Asset).filter_by(symbol="BTCUSDT").one()
        scanner_result = _latest_scanner_result(session, btc.id)
        scanner_result_id = scanner_result.id
    finally:
        session.close()

    response = client.get(f"/api/v1/scanner/results/{scanner_result_id}/qualification")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["instrument"] == "BTCUSDT"
    assert "passed_by" in body
    assert body["data_status"] in {"LIVE", "STALE"}


def test_websocket_endpoint_accepts_connection(client):
    with client.websocket_connect("/api/v1/ws/research") as ws:
        assert ws is not None
