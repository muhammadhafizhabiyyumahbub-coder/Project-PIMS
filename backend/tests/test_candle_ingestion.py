import pytest
from datetime import datetime, UTC
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

def test_ingest_candles_success(db_session):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(symbol="BTC", name="Bitcoin", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    db_session.add(asset)
    db_session.commit()
    pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="BTC-USD", is_active=True)
    db_session.add(pi)
    db_session.commit()

    payload = {
        "chart": {
            "result": [{
                "timestamp": [int(datetime.now(UTC).timestamp())],
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
    # Verify persistence with new session
    session_factory = get_session_factory()
    with session_factory() as s2:
        count = s2.query(MarketCandle).filter_by(asset_id=asset.id).count()
        assert count == 1

def test_ingest_candles_no_mapping(db_session):
    # Setup data
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    db_session.commit()
    asset = Asset(symbol="B2", name="Asset B2", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    db_session.add(asset)
    db_session.commit()

    res = ingest_candles()
    assert res["written"] == 0
    assert res["skipped"] == 1
    assert "no provider instrument mapping" in res["skipped_reasons"][0]["reason"]


def _seed_mapped_asset(db_session, asset_symbol: str, provider_symbol: str):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol=asset_symbol,
        name=asset_symbol,
        asset_type="CRYPTO",
        quote_currency="USD",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    db_session.add(
        ProviderInstrument(
            asset_id=asset.id,
            provider_id=provider.id,
            provider_symbol=provider_symbol,
            is_active=True,
        )
    )
    db_session.commit()
    return asset


def test_ingest_candles_requests_provider_symbol(db_session):
    """The provider must be asked for the mapped symbol, not the internal one."""
    _seed_mapped_asset(db_session, "BTCUSDT", "BTC-USD")

    payload = {
        "chart": {
            "result": [
                {
                    "timestamp": [int(datetime.now(UTC).timestamp())],
                    "indicators": {
                        "quote": [
                            {
                                "open": [50000.0],
                                "high": [51000.0],
                                "low": [49000.0],
                                "close": [50500.0],
                                "volume": [1000.0],
                            }
                        ]
                    },
                }
            ]
        }
    }
    transport = MockTransport({"BTC-USD": payload})

    import app.data.ingestion.ingest as ing

    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(
        base_url="https://query1.finance.yahoo.com", transport=transport
    )
    try:
        res = ingest_candles()
    finally:
        ing.YahooProvider = orig

    urls = [str(r.url) for r in transport.requests]
    assert any("/chart/BTC-USD" in u for u in urls), urls
    assert not any("/chart/BTCUSDT" in u for u in urls), urls
    assert res["written"] == 1


def test_ingest_candles_provider_404_is_skipped(db_session):
    """A mapped symbol the provider does not carry is skipped, never guessed."""
    asset = _seed_mapped_asset(db_session, "FAKEUSDT", "FAKE-USD")
    transport = MockTransport({})  # every symbol answers 404

    import app.data.ingestion.ingest as ing

    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(
        base_url="https://query1.finance.yahoo.com", transport=transport
    )
    try:
        res = ingest_candles()
    finally:
        ing.YahooProvider = orig

    assert res["written"] == 0
    assert res["skipped"] == 1
    assert res["failed"] == []
    assert "FAKE-USD" in res["skipped_reasons"][0]["reason"]
    assert db_session.query(MarketCandle).filter_by(asset_id=asset.id).count() == 0


def test_ingest_candles_transport_error_is_failed(db_session):
    """Transport errors are failures with a real message, not silent skips."""
    _seed_mapped_asset(db_session, "ERRUSDT", "ERR-USD")

    class ExplodingTransport:
        def handle_request(self, request):
            raise RuntimeError("connection reset by peer")

    import app.data.ingestion.ingest as ing

    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(
        base_url="https://query1.finance.yahoo.com", transport=ExplodingTransport()
    )
    try:
        res = ingest_candles()
    finally:
        ing.YahooProvider = orig

    assert res["written"] == 0
    assert res["skipped"] == 0
    assert len(res["failed"]) == 1
    assert res["failed"][0]["reason"] != ""
