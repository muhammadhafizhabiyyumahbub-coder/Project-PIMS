"""Tests for research API endpoint aliases (§18)."""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_research_post_alias_creates_request(db_session, btc_asset):
    """Test POST /api/v1/research (alias for /requests) creates request."""
    response = client.post("/api/v1/research", json={
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "request_summary": "Test via alias"
    })
    assert response.status_code == 200
    data = response.json()["data"]
    assert "action" in data
    assert "job" in data
    assert data["job"]["status"] in ["WAITING_FOR_ENGINES", "BLOCKED", "COMPLETED", "FAILED"]

def test_research_get_list_alias(db_session, analyzed_universe):
    """Test GET /api/v1/research returns report history."""
    response = client.get("/api/v1/research")
    assert response.status_code == 200
    data = response.json()["data"]
    assert isinstance(data, list)

def test_research_get_report_alias(db_session, analyzed_universe):
    """Test GET /api/v1/research/{report_id} (alias for /reports/{report_id})."""
    import uuid
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/research/{fake_id}")
    assert response.status_code == 404

def test_research_delete_report_alias(db_session, analyzed_universe):
    """Test DELETE /api/v1/research/{report_id}."""
    import uuid
    fake_id = str(uuid.uuid4())
    response = client.delete(f"/api/v1/research/{fake_id}")
    assert response.status_code == 404

def test_research_old_endpoints_still_work(db_session, btc_asset):
    """Regression: old endpoints /requests, /reports/{id} still work."""
    # POST /requests
    response = client.post("/api/v1/research/requests", json={
        "symbol": "BTCUSDT",
        "timeframe": "1h"
    })
    assert response.status_code == 200
    
    # GET /requests/{id}
    data = response.json()["data"]
    req_id = data["job"]["request_id"]
    response = client.get(f"/api/v1/research/requests/{req_id}")
    assert response.status_code == 200
