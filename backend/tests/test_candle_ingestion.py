import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import httpx
from app.database.models import Asset, DataProvider, MarketCandle, ProviderInstrument, Market
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


class RetryMockTransport:
    """Mock transport that can simulate retries by tracking call counts per symbol."""
    def __init__(self, responses: dict[str, list]):
        self.responses = responses
        self.call_counts = {k: 0 for k in responses}
        self.requests = []

    def handle_request(self, request):
        self.requests.append(request)
        url = str(request.url)
        for pattern, response_list in self.responses.items():
            if pattern in url:
                idx = self.call_counts.get(pattern, 0)
                self.call_counts[pattern] = idx + 1
                if idx < len(response_list):
                    resp = response_list[idx]
                    if isinstance(resp, int):
                        return httpx.Response(resp, json={"chart": {"error": {"description": f"Status {resp}"}}}, request=request)
                    return httpx.Response(200, json=resp, request=request)
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
    res = ingest_candles()
    assert isinstance(res["skipped_reasons"], list)


def test_ingest_candles_requests_provider_symbol(db_session):
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


def test_candle_ingestion_retry_429_then_200(db_session):
    provider = _get_or_create_provider(db_session)
    asset = Asset(symbol="RETRY_429", name="Retry 429", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    db_session.add(asset)
    db_session.commit()
    
    with db_session.no_autoflush:
        pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="RETRY-429", is_active=True)
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
    transport = RetryMockTransport({"RETRY-429": [429, payload]})
    
    import app.data.ingestion.ingest as ing
    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)
    
    res = ingest_candles()
    ing.YahooProvider = orig

    assert res["written"] == 1
    assert len(transport.requests) == 2


def test_candle_ingestion_mixed_universe(db_session):
    provider = _get_or_create_provider(db_session)
    
    m_crypto = Market(code="CRYPTO", name="Crypto", market_type="CRYPTO")
    m_us = Market(code="US", name="US Stocks", market_type="STOCK")
    m_idx = Market(code="IDX", name="IDX Stocks", market_type="STOCK")
    db_session.add_all([m_crypto, m_us, m_idx])
    db_session.commit()
    
    btc = Asset(symbol="BTCUSDT", name="Bitcoin", asset_type="CRYPTO", quote_currency="USDT", market_id=m_crypto.id, is_active=True)
    aapl = Asset(symbol="AAPL", name="Apple Inc.", asset_type="STOCK", quote_currency="USD", market_id=m_us.id, is_active=True)
    bbca = Asset(symbol="BBCA", name="Bank Central Asia", asset_type="STOCK", quote_currency="IDR", market_id=m_idx.id, is_active=True)
    
    for asset in [btc, aapl, bbca]:
        db_session.add(asset)
    db_session.commit()
    
    with db_session.no_autoflush:
        db_session.add(ProviderInstrument(asset_id=btc.id, provider_id=provider.id, provider_symbol="BTC-USD", is_active=True))
        db_session.add(ProviderInstrument(asset_id=aapl.id, provider_id=provider.id, provider_symbol="AAPL", is_active=True))
        db_session.add(ProviderInstrument(asset_id=bbca.id, provider_id=provider.id, provider_symbol="BBCA.JK", is_active=True))
        db_session.commit()
    
    now = datetime.now(timezone.utc)
    payload_btc = {"chart": {"result": [{"timestamp": [int(now.timestamp())], "indicators": {"quote": [{"open": [50000.0], "high": [51000.0], "low": [49000.0], "close": [50500.0], "volume": [1000.0]}]}}]}}
    payload_aapl = {"chart": {"result": [{"timestamp": [int(now.timestamp())], "indicators": {"quote": [{"open": [150.0], "high": [155.0], "low": [148.0], "close": [153.0], "volume": [1000000.0]}]}}]}}
    payload_bbca = {"chart": {"result": [{"timestamp": [int(now.timestamp())], "indicators": {"quote": [{"open": [9000.0], "high": [9100.0], "low": [8900.0], "close": [9050.0], "volume": [500000.0]}]}}]}}
    
    transport = MockTransport({
        "BTC-USD": payload_btc,
        "AAPL": payload_aapl,
        "BBCA.JK": payload_bbca,
    })
    
    import app.data.ingestion.ingest as ing
    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)
    
    res = ingest_candles()
    ing.YahooProvider = orig
    
    assert res["requested"] == 3
    assert res["written"] == 3
    requested_symbols = {str(r.url).split("/chart/")[1].split("?")[0] for r in transport.requests}
    assert requested_symbols == {"BTC-USD", "AAPL", "BBCA.JK"}
