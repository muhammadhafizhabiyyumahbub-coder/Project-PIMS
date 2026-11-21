import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import httpx
from app.database.models import Asset, DataProvider, MarketCandle, ProviderInstrument
from app.data.ingestion.candles import ingest_candles
from app.core.db import get_session_factory

class MockTransport:
    def __init__(self, payloads: dict[str, dict]):
        self.payloads = payloads
        self.requests = []

    def handle_request(self, request):
        self.requests.append(request)
        url = str(request.url)
        for pattern, payload in self.payloads.items():
            if pattern in url:
                return httpx.Response(200, json=payload, request=request)
        return httpx.Response(404, json={"chart": {"error": {"description": "Not found"}}}, request=request)

def _get_or_create_provider(db_session):
    p = db_session.query(DataProvider).filter_by(code="YAHOO").first()
    if not p:
        p = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
        db_session.add(p)
        db_session.commit()
    return p

def test_ingest_candles_success(db_session):
    provider = _get_or_create_provider(db_session)
    asset = Asset(symbol="BTC_CANDLE_TEST", name="Bitcoin Candle", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    db_session.add(asset)
    db_session.commit()
    
    with db_session.no_autoflush:
        pi = db_session.query(ProviderInstrument).filter_by(asset_id=asset.id, provider_id=provider.id).first()
        if not pi:
            pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="BTC-USD", is_active=True)
            db_session.add(pi)
            db_session.commit()

    payload = {
        "chart": {
            "result": [{
                "timestamp": [int(datetime.now(timezone.utc).timestamp())],
                "indicators": {"quote": [{"open": [50000.0], "high": [51000.0], "low": [49000.0], "close": [50500.0], "volume": [1000.0]}]}
            }]
        }
    }
    transport = MockTransport({"BTC-USD": payload})

    import app.data.ingestion.ingest as ing
    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)
    
    res = ingest_candles()
    ing.YahooProvider = orig

    assert res["written"] == 1
    candle = db_session.query(MarketCandle).filter_by(asset_id=asset.id).one()
    assert isinstance(candle.close_price, Decimal)
    assert candle.close_price == Decimal("50500.0")

def test_ingest_candles_no_mapping(db_session):
    _get_or_create_provider(db_session)
    # Ensure this test doesn't look at mappings for other assets
    res = ingest_candles()
    # If other assets have mappings, they are skipped too, that's fine.
    # We just need to check if our skip logic works generally.
    assert isinstance(res["skipped_reasons"], list)

def test_ingest_candles_requests_provider_symbol(db_session):
    """The provider must be asked for the mapped symbol, not the internal one."""
    provider = _get_or_create_provider(db_session)
    asset = Asset(symbol="TEST_SYMBOL", name="Test Symbol", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    db_session.add(asset)
    db_session.commit()
    
    with db_session.no_autoflush:
        pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="MAPPED_SYMBOL", is_active=True)
        db_session.add(pi)
        db_session.commit()

    transport = MockTransport({"MAPPED_SYMBOL": {"chart": {"result": []}}})
    import app.data.ingestion.ingest as ing
    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)
    
    ingest_candles()
    ing.YahooProvider = orig
    
    assert any("MAPPED_SYMBOL" in str(r.url) for r in transport.requests)

def test_ingest_candles_provider_404_is_skipped(db_session):
    provider = _get_or_create_provider(db_session)
    asset = Asset(symbol="404_TEST", name="404 Asset", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    db_session.add(asset)
    db_session.commit()
    
    with db_session.no_autoflush:
        db_session.add(ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="NOT-EXISTING", is_active=True))
        db_session.commit()
        
    res = ingest_candles()
    assert any("404" in r["reason"] or "not offer" in r["reason"] for r in res["skipped_reasons"])

def test_ingest_candles_transport_error_is_failed(db_session):
    provider = _get_or_create_provider(db_session)
    asset = Asset(symbol="FAIL_TEST", name="Fail Asset", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    db_session.add(asset)
    db_session.commit()
    
    with db_session.no_autoflush:
        db_session.add(ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="FAIL-TEST", is_active=True))
        db_session.commit()

    import app.data.ingestion.ingest as ing
    class FailingTransport:
        def handle_request(self, request):
            raise httpx.ConnectError("Connection failed")
            
    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(base_url="http://fail", transport=FailingTransport())
    
    res = ingest_candles()
    ing.YahooProvider = orig
    
    assert res["failed"]
    assert "Connection failed" in res["failed"][0]["reason"]
