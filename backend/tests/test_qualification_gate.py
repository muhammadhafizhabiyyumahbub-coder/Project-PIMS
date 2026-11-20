import pytest
import uuid
from datetime import datetime
from fastapi.testclient import TestClient
from app.main import app
from app.database.models import RiskResult, AnalyticsRun, Asset, DataProvider

@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c

def test_qualification_gate_failed_risk(client, db_session):
    # Get existing
    provider = db_session.query(DataProvider).filter_by(code="BYBIT").first()
    asset = db_session.query(Asset).filter_by(symbol="BTCUSDT").first()
    
    # Run
    run = AnalyticsRun(engine_type="RISK", asset_id=asset.id, timeframe="1h", execution_status="COMPLETED", started_at=datetime.utcnow(), calculation_version="1")
    db_session.add(run)
    db_session.commit()
    
    # Risk FAILED due to high vol
    risk = RiskResult(analytics_run_id=run.id, asset_id=asset.id, volatility=0.9, risk_classification="HIGH")
    db_session.add(risk)
    db_session.commit()
    
    response = client.post("/api/v1/research/requests", json={"symbol": "BTCUSDT", "timeframe": "1h"})
    assert response.status_code == 200
    assert response.json()["data"]["job"]["status"] == "BLOCKED"
    assert response.json()["data"]["job"]["error_code"] == "ENGINES_NOT_READY"
