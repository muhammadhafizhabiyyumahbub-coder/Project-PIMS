import pytest
import uuid
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.database.models import Asset, DataProvider, ProviderInstrument, MarketCandle, ScannerRun, ScannerResult
from app.core.db import get_session_factory

@pytest.fixture()
def seeded_provider(db_session):
    p = db_session.query(DataProvider).filter_by(code="YAHOO").first()
    if not p:
        p = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
        db_session.add(p)
        db_session.commit()
    return p

@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c

def test_scanner_run_endpoint_success(client, db_session, seeded_provider):
    asset = Asset(symbol="BTC_RUN_TEST", name="Bitcoin Run Test", asset_type="CRYPTO", is_active=True)
    db_session.add(asset)
    db_session.commit()
    
    with db_session.no_autoflush:
        pi = db_session.query(ProviderInstrument).filter_by(asset_id=asset.id, provider_id=seeded_provider.id).first()
        if not pi:
            pi = ProviderInstrument(asset_id=asset.id, provider_id=seeded_provider.id, provider_symbol="BTC_RUN_TEST-USD", is_active=True)
            db_session.add(pi)
            db_session.commit()
    
    now = datetime.now(timezone.utc)
    for i in range(60):
        db_session.add(MarketCandle(
            asset_id=asset.id,
            provider_id=seeded_provider.id,
            timeframe="1h",
            open_time=now - timedelta(seconds=(60 - i) * 3600),
            close_time=now - timedelta(seconds=(59 - i) * 3600),
            open_price=50000 + i,
            high_price=51000 + i,
            low_price=49000 + i,
            close_price=50500 + i,
            volume=1000,
            currency="USD",
            candle_status="CLOSED"
        ))
    db_session.commit()

    response = client.post("/api/v1/scanner/run", params={"timeframe": "1h"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["execution_status"] == "COMPLETED"
    assert data["eligible_count"] >= 1
    
    session_factory = get_session_factory()
    with session_factory() as s2:
        run = s2.query(ScannerRun).filter_by(id=uuid.UUID(data["scanner_run_id"])).one()
        assert run.execution_status == "COMPLETED"
        results = s2.query(ScannerResult).filter_by(scanner_run_id=run.id).all()
        assert len(results) >= 1

def test_scanner_run_endpoint_insufficient_data(client, db_session, seeded_provider):
    asset = Asset(symbol="ETH_RUN_TEST", name="Ethereum Run Test", asset_type="CRYPTO", is_active=True)
    db_session.add(asset)
    db_session.commit()
    
    with db_session.no_autoflush:
        pi = db_session.query(ProviderInstrument).filter_by(asset_id=asset.id, provider_id=seeded_provider.id).first()
        if not pi:
            pi = ProviderInstrument(asset_id=asset.id, provider_id=seeded_provider.id, provider_symbol="ETH_RUN_TEST-USD", is_active=True)
            db_session.add(pi)
            db_session.commit()

    response = client.post("/api/v1/scanner/run", params={"timeframe": "1h"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["eligible_count"] == 0

def test_scanner_run_endpoint_invalid_timeframe(client):
    response = client.post("/api/v1/scanner/run", params={"timeframe": "invalid"})
    assert response.status_code == 200
    assert response.json()["data"]["eligible_count"] == 0
