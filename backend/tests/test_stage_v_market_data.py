import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
import uuid
import json
from decimal import Decimal

from app.main import app
from app.database.models import MarketQuote, ScannerConfiguration

client = TestClient(app)

def test_get_market_quotes_empty(db_session: Session):
    response = client.get("/api/v1/market-data/quotes")
    assert response.status_code == 200
    data = response.json()
    assert data["data"] == []
    assert "meta" in data

def test_get_instrument_quote_unavailable(db_session: Session):
    asset_id = uuid.uuid4()
    response = client.get(f"/api/v1/market-data/instruments/{asset_id}/quote")
    assert response.status_code == 200
    data = response.json()
    assert data["data"] is None
    assert data["meta"]["feed_status"] == "UNAVAILABLE"

def test_scanner_crud_cycle(db_session: Session):
    # Create
    payload = {
        "name": "Test Scanner",
        "category": "TECHNICAL",
        "universe_config": {"assets": ["BTC"]},
        "filter_config": {"min_volume": 1000}
    }
    response = client.post("/api/v1/scanner/configurations", json=payload)
    assert response.status_code == 200
    config_id = response.json()["data"]["id"]
    
    # Invalid Category
    payload["category"] = "INVALID"
    response = client.post("/api/v1/scanner/configurations", json=payload)
    assert response.status_code == 422

    # Patch
    response = client.patch(f"/api/v1/scanner/configurations/{config_id}", json={"name": "New Name"})
    assert response.status_code == 200
    
    # Delete
    response = client.delete(f"/api/v1/scanner/configurations/{config_id}")
    assert response.status_code == 200
