"""Security Q2 (QA S7): 500 responses must be generic, not leak str(exc)."""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SECRET = "postgresql://pims:S3CRETPW@db:5432/pims Traceback"
GENERIC = "Internal error (see server logs)"


def _make_portfolio() -> str:
    r = client.post(
        "/api/v1/portfolios", json={"name": "Q2 Portfolio", "base_currency": "USD"}
    )
    assert r.status_code == 201
    return r.json()["data"]["id"]


def _boom(*_args, **_kwargs):
    raise RuntimeError(SECRET)


def test_analytics_get_500_hides_exception(db_session, monkeypatch):
    pid = _make_portfolio()
    monkeypatch.setattr("app.api.rest.analytics_v2.risk_for_portfolio", _boom)

    r = client.get(f"/api/v1/analytics/risk?portfolio_id={pid}")

    assert r.status_code == 500
    assert "S3CRETPW" not in r.text
    assert SECRET not in r.text
    assert r.json()["error"]["message"] == GENERIC


def test_analytics_get_allocation_500_hides_exception(db_session, monkeypatch):
    pid = _make_portfolio()
    monkeypatch.setattr("app.api.rest.analytics_v2.allocation_for_portfolio", _boom)

    r = client.get(f"/api/v1/analytics/allocation?portfolio_id={pid}")

    assert r.status_code == 500
    assert SECRET not in r.text
    assert r.json()["error"]["message"] == GENERIC


def test_analytics_runs_post_500_hides_exception(db_session, monkeypatch):
    pid = _make_portfolio()
    monkeypatch.setattr("app.api.rest.analytics.persist_analytics", _boom)

    r = client.post(
        f"/api/v1/portfolios/{pid}/analytics/runs",
        json={"analysis_type": "performance"},
    )

    assert r.status_code == 500
    assert SECRET not in r.text
    assert r.json()["error"]["message"] == GENERIC
