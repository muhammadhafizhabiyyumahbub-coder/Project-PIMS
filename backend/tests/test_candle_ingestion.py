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


def test_ingest_candles_timeout_failed(db_session):
    """timeout error -> failed with read timeout reason, other assets processed."""
    provider = _get_or_create_provider(db_session)
    asset1 = Asset(symbol="TIMEOUT_1", name="Timeout 1", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    asset2 = Asset(symbol="SUCCESS_2", name="Success 2", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    db_session.add_all([asset1, asset2])
    db_session.commit()
    
    with db_session.no_autoflush:
        db_session.add(ProviderInstrument(asset_id=asset1.id, provider_id=provider.id, provider_symbol="T1", is_active=True))
        db_session.add(ProviderInstrument(asset_id=asset2.id, provider_id=provider.id, provider_symbol="S2", is_active=True))
        db_session.commit()

    class TimeoutTransport:
        def handle_request(self, request):
            if "T1" in str(request.url):
                raise httpx.TimeoutException("The read operation timed out")
            return httpx.Response(200, json={"chart": {"result": [{"timestamp": [int(datetime.now(timezone.utc).timestamp())], "indicators": {"quote": [{"open": [10.0], "high": [11.0], "low": [9.0], "close": [10.5], "volume": [100.0]}]}}]}})
            
    import app.data.ingestion.ingest as ing
    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(base_url="http://timeout", transport=TimeoutTransport())
    
    res = ingest_candles()
    ing.YahooProvider = orig
    
    assert res["failed"]
    assert any("timed out" in f["reason"] for f in res["failed"])
    assert res["written"] == 1

# === Restored pipeline tests (removed by a later round without replacement) ===

def test_ingest_candles_success(db_session):
    provider = _get_or_create_provider(db_session)
    asset = Asset(symbol="BTC_CANDLE_TEST", name="Bitcoin Candle", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    db_session.add(asset)
    db_session.commit()

    with db_session.no_autoflush:
        pi = db_session.query(ProviderInstrument).filter_by(asset_id=asset.id, provider_id=provider.id).first()
        if not pi:
            db_session.add(ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="BTC-USD", is_active=True))
            db_session.commit()

    payload = {
        "chart": {
            "result": [{
                "timestamp": [int(datetime.now(timezone.utc).timestamp())],
                "indicators": {"quote": [{"open": [50000.0], "high": [51000.0], "low": [49000.0], "close": [50500.0], "volume": [1000.0]}]},
            }]
        }
    }
    transport = MockTransport({"BTC-USD": payload})

    import app.data.ingestion.ingest as ing
    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)
    try:
        res = ingest_candles()
    finally:
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
    """The provider must be asked for the mapped symbol, not the internal one."""
    provider = _get_or_create_provider(db_session)
    asset = Asset(symbol="TEST_SYMBOL", name="Test Symbol", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    db_session.add(asset)
    db_session.commit()

    with db_session.no_autoflush:
        db_session.add(ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="MAPPED_SYMBOL", is_active=True))
        db_session.commit()

    transport = MockTransport({"MAPPED_SYMBOL": {"chart": {"result": []}}})
    import app.data.ingestion.ingest as ing
    orig = ing.YahooProvider
    ing.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)
    try:
        ingest_candles()
    finally:
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
    try:
        res = ingest_candles()
    finally:
        ing.YahooProvider = orig

    assert res["failed"]
    assert "Connection failed" in res["failed"][0]["reason"]
