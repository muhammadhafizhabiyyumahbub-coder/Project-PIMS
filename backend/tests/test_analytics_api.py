"""Tests for analytics API endpoints (§15)."""
import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

@pytest.fixture()
def portfolio_id():
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "Analytics Test Portfolio", "base_currency": "USD"},
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]

def test_analytics_performance_basic(db_session, portfolio_id):
    """Test GET /api/v1/analytics/performance with valid portfolio."""
    pid = portfolio_id
    
    response = client.get(f"/api/v1/analytics/performance?portfolio_id={pid}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["portfolio_id"] == pid
    assert "period_start" in data
    assert "period_end" in data
    assert "twr" in data
    assert "simple_return" in data
    assert "cagr" in data
    assert "realized_pnl" in data
    assert "unrealized_pnl" in data
    assert "return_status" in data
    # Decimal values should be strings if present
    if data["twr"] is not None:
        assert isinstance(data["twr"], str)
    if data["realized_pnl"] is not None:
        assert isinstance(data["realized_pnl"], str)

def test_analytics_performance_portfolio_not_found(db_session):
    """Test GET /api/v1/analytics/performance with non-existent portfolio."""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/analytics/performance?portfolio_id={fake_id}")
    assert response.status_code == 404

def test_analytics_performance_invalid_portfolio_id(db_session):
    """Test GET /api/v1/analytics/performance with invalid UUID format."""
    response = client.get("/api/v1/analytics/performance?portfolio_id=not-a-uuid")
    assert response.status_code == 422

def test_analytics_risk_basic(db_session, portfolio_id):
    """Test GET /api/v1/analytics/risk with valid portfolio."""
    pid = portfolio_id
    
    response = client.get(f"/api/v1/analytics/risk?portfolio_id={pid}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["portfolio_id"] == pid
    assert "observation_start" in data
    assert "observation_end" in data
    assert "window_days" in data
    assert "metrics" in data
    assert isinstance(data["metrics"], dict)
    # Decimal values should be strings
    for v in data["metrics"].values():
        if v is not None:
            assert isinstance(v, str)

def test_analytics_risk_custom_window(db_session, portfolio_id):
    """Test GET /api/v1/analytics/risk with custom window."""
    pid = portfolio_id
    
    response = client.get(f"/api/v1/analytics/risk?portfolio_id={pid}&window_days=180")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["window_days"] == 180

def test_analytics_risk_invalid_window(db_session, portfolio_id):
    """Test GET /api/v1/analytics/risk with invalid window."""
    pid = portfolio_id
    response = client.get(f"/api/v1/analytics/risk?portfolio_id={pid}&window_days=10")
    assert response.status_code == 422

def test_analytics_allocation_basic(db_session, portfolio_id):
    """Test GET /api/v1/analytics/allocation with valid portfolio."""
    pid = portfolio_id
    
    response = client.get(f"/api/v1/analytics/allocation?portfolio_id={pid}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["portfolio_id"] == pid
    assert "valuation_timestamp" in data
    assert "reporting_currency" in data
    assert "total_value" in data
    assert "cash_value" in data
    assert "invested_value" in data
    assert "slices" in data
    assert "asset_class" in data["slices"]
    assert "market" in data["slices"]
    assert "currency" in data["slices"]
    assert "individual_asset" in data["slices"]
    assert "cash" in data["slices"]

def test_analytics_technical_basic(db_session, analyzed_universe):
    """Test GET /api/v1/analytics/technical with valid asset."""
    asset = analyzed_universe["assets"]["BTCUSDT"]
    aid = str(asset.id)
    
    response = client.get(f"/api/v1/analytics/technical?asset_id={aid}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["asset_id"] == aid
    assert data["symbol"] == "BTCUSDT"
    assert "calculation_status" in data
    assert "values" in data
    assert "sma_20" in data["values"]
    assert "sma_50" in data["values"]
    assert "rsi_14" in data["values"]
    assert "atr_14" in data["values"]
    assert "macd" in data["values"]
    assert "last_close" in data["values"]
    # Decimal values should be strings if present
    if data["values"]["sma_20"] is not None:
        assert isinstance(data["values"]["sma_20"], str)

def test_analytics_technical_asset_not_found(db_session):
    """Test GET /api/v1/analytics/technical with non-existent asset."""
    fake_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/analytics/technical?asset_id={fake_id}")
    assert response.status_code == 404

def test_analytics_market_regime_basic(db_session, analyzed_universe):
    """Test GET /api/v1/analytics/market-regime with valid asset."""
    asset = analyzed_universe["assets"]["BTCUSDT"]
    aid = str(asset.id)
    
    response = client.get(f"/api/v1/analytics/market-regime?asset_id={aid}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["asset_id"] == aid
    assert data["symbol"] == "BTCUSDT"
    assert "trend_regime" in data
    assert "volatility_regime" in data
    assert "momentum_regime" in data
    assert "confidence_score" in data
    assert "atr_pct" in data
    assert "calculation_status" in data

def test_analytics_correlation_no_holdings(portfolio_id):
    """GET /api/v1/analytics/correlation on a portfolio with no holdings returns
    an honest INSUFFICIENT_DATA status with an empty (not None) matrix."""
    pid = str(portfolio_id)

    response = client.get(f"/api/v1/analytics/correlation?portfolio_id={pid}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["portfolio_id"] == pid
    assert data["correlation_matrix"] == []
    assert data["calculation_status"] == "INSUFFICIENT_DATA"
    assert data["pairs_computed"] == 0
