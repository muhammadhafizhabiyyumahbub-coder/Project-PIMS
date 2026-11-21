import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_invalid_uuid_handling():
    # List of endpoints to test and their malformed/non-existent IDs
    endpoints = [
        "/api/v1/research/requests/abc",
        "/api/v1/research/reports/abc",
        "/api/v1/scanner/results/abc/qualification",
        "/api/v1/scanner/runs/abc",
        "/api/v1/markets/abc",
        "/api/v1/market-data/instruments/abc/quote",
        "/api/v1/market-data/instruments/abc/candles",
        "/api/v1/assets/abc",
        "/api/v1/portfolios/abc",
        "/api/v1/transactions/abc",
        "/api/v1/portfolios/abc/analytics/runs",
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        # Should be 404 (if not found in DB) or 422 (if validated)
        # Definitely NOT 500
        assert response.status_code in [404, 422], f"Endpoint {endpoint} returned {response.status_code} for invalid ID"

    # Test valid but non-existent
    valid_uuid = "123e4567-e89b-12d3-a456-426614174000"
    endpoints_non_existent = [
        f"/api/v1/research/requests/{valid_uuid}",
        f"/api/v1/research/reports/{valid_uuid}",
    ]
    for endpoint in endpoints_non_existent:
        response = client.get(endpoint)
        assert response.status_code == 404
