import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from app.main import app
from app.database.models import RiskResult, AnalyticsRun, Asset, DataProvider

@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c

def test_qualification_gate_failed_risk(client, db_session):
    # Setup asset
    provider = db_session.query(DataProvider).filter_by(code="BYBIT").first()
    asset = db_session.query(Asset).filter_by(symbol="BTCUSDT").first()
    
    # Run
    run = AnalyticsRun(engine_type="RISK", asset_id=asset.id, timeframe="1h", execution_status="COMPLETED", started_at=datetime.now(timezone.utc), calculation_version="1")
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

def test_qualification_gate_risk_none_vol(client, db_session):
    # Setup
    asset = db_session.query(Asset).filter_by(symbol="BTCUSDT").first()
    now = datetime.now(timezone.utc)
    run = AnalyticsRun(
        engine_type="RISK", 
        asset_id=asset.id, 
        timeframe="1h", 
        execution_status="COMPLETED", 
        started_at=now,
        observation_end=now,
        calculation_version="1"
    )
    db_session.add(run)
    db_session.commit()
    
    # Volatility None
    risk = RiskResult(analytics_run_id=run.id, asset_id=asset.id, volatility=None, risk_classification="NONE")
    db_session.add(risk)
    db_session.commit()
    
    # Need to access service to verify status as per requirement
    from app.qualification.service import evaluate_engine_readiness, qualification_summary
    readiness = evaluate_engine_readiness(db_session, asset.id, "1h")
    summary = qualification_summary(readiness)
    assert summary["status"] == "NOT_QUALIFIED"
    assert readiness["RISK"]["label"] == "FAILED"
    assert readiness["RISK"]["detail"]["reason"] == "risk metric unavailable"

def test_qualification_gate_timeframe_mismatch(client, db_session):
    # Setup
    asset = db_session.query(Asset).filter_by(symbol="BTCUSDT").first()
    now = datetime.now(timezone.utc)
    # Risk only for 1d
    run = AnalyticsRun(
        engine_type="RISK", 
        asset_id=asset.id, 
        timeframe="1d", 
        execution_status="COMPLETED", 
        started_at=now,
        observation_end=now,
        calculation_version="1"
    )
    db_session.add(run)
    db_session.commit()
    risk = RiskResult(analytics_run_id=run.id, asset_id=asset.id, volatility=0.1, risk_classification="LOW")
    db_session.add(risk)
    db_session.commit()
    
    from app.qualification.service import evaluate_engine_readiness
    readiness = evaluate_engine_readiness(db_session, asset.id, "1h")
    assert readiness["RISK"]["state"] != "READY"
    assert readiness["RISK"]["state"] == "PENDING"
