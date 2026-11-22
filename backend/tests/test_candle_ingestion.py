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


def _get_or_create_provider(db_session):
    p = db_session.query(DataProvider).filter_by(code="YAHOO").first()
    if not p:
        p = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
        db_session.add(p)
        db_session.commit()
    return p


# === Multi-market and filter tests ===

def test_candle_ingestion_mixed_universe(db_session):
    """Mixed CRYPTO + US + IDX universe -> all three ingested using provider symbols."""
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
    assert res["skipped"] == 0
    requested_symbols = {str(r.url).split("/chart/")[1].split("?")[0] for r in transport.requests}
    assert requested_symbols == {"BTC-USD", "AAPL", "BBCA.JK"}


def test_candle_ingestion_markets_filter_us_only(db_session):
    """markets=['US'] -> only US assets ingested."""
    provider = _get_or_create_provider(db_session)
    
    m_crypto = Market(code="CRYPTO", name="Crypto", market_type="CRYPTO")
    m_us = Market(code="US", name="US Stocks", market_type="STOCK")
    db_session.add_all([m_crypto, m_us])
    db_session.commit()
    
    btc = Asset(symbol="BTCUSDT", name="Bitcoin", asset_type="CRYPTO", quote_currency="USDT", market_id=m_crypto.id, is_active=True)
    aapl = Asset(symbol="AAPL", name="Apple Inc.", asset_type="STOCK", quote_currency="USD", market_id=m_us.id, is_active=True)
    
    db_session.add_all([btc, aapl])
    db_session.commit()
    
    with db_session.no_autoflush:
        db_session.add(ProviderInstrument(asset_id=btc.id, provider_id=provider.id, provider_symbol="BTC-USD", is_active=True))
        db_session.add(ProviderInstrument(asset_id=aapl.id, provider_id=provider.id, provider_symbol="AAPL", is_active=True))
        db_session.commit()
    
    now = datetime.now(timezone.utc)
    payload_aapl = {"chart": {"result": [{"timestamp": [int(now.timestamp())], "indicators": {"quote": [{"open": [150.0], "high": [155.0], "low": [148.0], "close": [153.0], "volume": [1000000.0]}]}}]}}
    
    transport = MockTransport({"AAPL": payload_aapl})
    
    import app.data.ingestion.ingest as ing
    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)
    
    res = ingest_candles(markets="US")
    ing.YahooProvider = orig
    
    assert res["requested"] == 1
    assert res["written"] == 1
    assert len(transport.requests) == 1
    assert "AAPL" in str(transport.requests[0].url)


def test_candle_ingestion_no_mapping_skipped(db_session):
    """Asset without provider mapping -> skipped with reason."""
    provider = _get_or_create_provider(db_session)
    m_us = Market(code="US", name="US Stocks", market_type="STOCK")
    db_session.add(m_us)
    db_session.commit()
    
    aapl = Asset(symbol="AAPL", name="Apple Inc.", asset_type="STOCK", quote_currency="USD", market_id=m_us.id, is_active=True)
    db_session.add(aapl)
    db_session.commit()
    
    res = ingest_candles()
    assert res["requested"] == 1
    assert res["skipped"] == 1
    assert any("no provider instrument mapping for AAPL" in r["reason"] for r in res["skipped_reasons"])



# === New retry tests ===

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


def test_candle_ingestion_retry_429_then_200(db_session):
    """429 on first attempt then 200 -> row written, retry proven (assert request count > 1)."""
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
    assert len(transport.requests) == 2  # retry happened


def test_candle_ingestion_retry_500_twice_then_200(db_session):
    """500 twice then 200 -> row written, retry proven."""
    provider = _get_or_create_provider(db_session)
    asset = Asset(symbol="RETRY_500", name="Retry 500", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    db_session.add(asset)
    db_session.commit()
    
    with db_session.no_autoflush:
        pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="RETRY-500", is_active=True)
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
    transport = RetryMockTransport({"RETRY-500": [500, 500, payload]})
    
    import app.data.ingestion.ingest as ing
    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)
    
    res = ingest_candles()
    ing.YahooProvider = orig

    assert res["written"] == 1
    assert len(transport.requests) == 3  # 2 retries + 1 success


def test_candle_ingestion_retry_429_continuous_fails(db_session):
    """429 continuously -> failed with real reason, attempt count matches limit, no hang."""
    provider = _get_or_create_provider(db_session)
    asset = Asset(symbol="RETRY_429_FAIL", name="Retry 429 Fail", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    db_session.add(asset)
    db_session.commit()
    
    with db_session.no_autoflush:
        pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="RETRY-429-FAIL", is_active=True)
        db_session.add(pi)
        db_session.commit()

    transport = RetryMockTransport({"RETRY-429-FAIL": [429, 429, 429]})  # 3 retries = 3 attempts
    
    import app.data.ingestion.ingest as ing
    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)
    
    res = ingest_candles()
    ing.YahooProvider = orig

    assert res["failed"]
    assert "429" in res["failed"][0]["reason"]
    assert len(transport.requests) == 3  # exactly 3 attempts (default retries=3)


def test_candle_ingestion_404_no_retry(db_session):
    """404 -> skipped, NO retry (assert request count == 1)."""
    provider = _get_or_create_provider(db_session)
    asset = Asset(symbol="RETRY_404", name="Retry 404", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    db_session.add(asset)
    db_session.commit()
    
    with db_session.no_autoflush:
        pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="RETRY-404", is_active=True)
        db_session.add(pi)
        db_session.commit()

    transport = RetryMockTransport({})  # no payload -> 404
    
    import app.data.ingestion.ingest as ing
    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)
    
    res = ingest_candles()
    ing.YahooProvider = orig

    assert res["skipped"] >= 1
    assert any("not offer" in r["reason"] or "404" in r["reason"] for r in res["skipped_reasons"])
    assert len(transport.requests) == 1  # no retry for 404


def test_candle_ingestion_transport_error_failed(db_session):
    """transport error -> failed with real message."""
    provider = _get_or_create_provider(db_session)
    asset = Asset(symbol="RETRY_TRANSPORT", name="Retry Transport", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    db_session.add(asset)
    db_session.commit()
    
    with db_session.no_autoflush:
        pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="RETRY-TRANSPORT", is_active=True)
        db_session.add(pi)
        db_session.commit()

    class FailingTransport:
        def handle_request(self, request):
            raise httpx.ConnectError("connection reset by peer")
            
    import app.data.ingestion.ingest as ing
    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(base_url="http://fail", transport=FailingTransport())
    
    res = ingest_candles()
    ing.YahooProvider = orig
    
    assert res["failed"]
    assert "connection reset by peer" in res["failed"][0]["reason"]