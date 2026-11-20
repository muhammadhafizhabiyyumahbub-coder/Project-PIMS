import pytest
import uuid
import json
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from fastapi.testclient import TestClient

from app.main import app
from app.database.models import MarketQuote, FXRate, DataProvider, Asset

@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture()
def seeded_data(db_session):
    provider = db_session.query(DataProvider).filter_by(code="BYBIT").first()
    if not provider:
        provider = DataProvider(code="BYBIT", name="Bybit", provider_type="CRYPTO")
        db_session.add(provider)
        db_session.commit()
    
    asset = db_session.query(Asset).filter_by(symbol="BTCUSDT").first()
    if not asset:
        asset = Asset(symbol="BTCUSDT", name="Bitcoin", asset_type="CRYPTO", quote_currency="USD")
        db_session.add(asset)
        db_session.commit()
    
    return {"provider": provider, "asset": asset}

def test_fx_rate_db_constraints(db_session, seeded_data):
    provider = seeded_data["provider"]
    # rate <= 0
    with pytest.raises(IntegrityError):
        db_session.add(FXRate(base_currency="USD", quote_currency="IDR", rate=0, provider_id=provider.id, source_timestamp=datetime.utcnow(), freshness_status="FRESH"))
        db_session.commit()
    db_session.rollback()

    # base == quote
    with pytest.raises(IntegrityError):
        db_session.add(FXRate(base_currency="USD", quote_currency="USD", rate=1.0, provider_id=provider.id, source_timestamp=datetime.utcnow(), freshness_status="FRESH"))
        db_session.commit()
    db_session.rollback()

    # duplicate
    ts = datetime.utcnow()
    db_session.add(FXRate(base_currency="USD", quote_currency="IDR", rate=15000.0, provider_id=provider.id, source_timestamp=ts, freshness_status="FRESH"))
    db_session.commit()
    with pytest.raises(IntegrityError):
        db_session.add(FXRate(base_currency="USD", quote_currency="IDR", rate=15001.0, provider_id=provider.id, source_timestamp=ts, freshness_status="FRESH"))
        db_session.commit()
    db_session.rollback()

def test_quote_freshness_status(client, db_session, seeded_data):
    provider = seeded_data["provider"]
    asset = seeded_data["asset"]
    
    # New quote
    db_session.add(MarketQuote(
        asset_id=asset.id,
        provider_id=provider.id,
        last_price=Decimal("100"),
        currency="USD",
        source_timestamp=datetime.utcnow(),
        received_at=datetime.utcnow() + timedelta(seconds=1),
        freshness_status="AVAILABLE"
    ))
    db_session.commit()
    
    response = client.get(f"/api/v1/market-data/instruments/{asset.id}/quote")
    assert response.json()["meta"]["feed_status"] == "AVAILABLE"
    
    # Old quote
    db_session.add(MarketQuote(
        asset_id=asset.id,
        provider_id=provider.id,
        last_price=Decimal("100"),
        currency="USD",
        source_timestamp=datetime.utcnow() - timedelta(hours=5),
        received_at=datetime.utcnow() + timedelta(seconds=10),
        freshness_status="STALE"
    ))
    db_session.commit()
    
    response = client.get(f"/api/v1/market-data/instruments/{asset.id}/quote")
    assert response.json()["meta"]["feed_status"] == "STALE"

def test_no_json_float_in_quotes(client, db_session, seeded_data):
    provider = seeded_data["provider"]
    asset = seeded_data["asset"]
    db_session.add(MarketQuote(
        asset_id=asset.id,
        provider_id=provider.id,
        currency="USD",
        last_price=Decimal("100.55"),
        source_timestamp=datetime.utcnow(),
        received_at=datetime.utcnow(),
        freshness_status="AVAILABLE"
    ))
    db_session.commit()
    
    response = client.get("/api/v1/market-data/quotes")
    assert response.status_code == 200
    assert '"100.55"' in response.text
    # Verify no unquoted floats
    def no_float(x): raise ValueError("Found float!")
    json.loads(response.text, parse_float=no_float)

def test_scanner_config_validation(client):
    uid = uuid.uuid4()
    # universe_config/filter_config not objects
    response = client.post("/api/v1/scanner/configurations", json={
        "name": "test", "category": "TECHNICAL", "universe_config": "not-obj", "filter_config": {}
    })
    assert response.status_code == 422
    
    # PATCH id not exists
    response = client.patch(f"/api/v1/scanner/configurations/{uid}", json={"name": "new"})
    assert response.status_code == 404
    
    # DELETE id not exists
    response = client.delete(f"/api/v1/scanner/configurations/{uid}")
    assert response.status_code == 404
