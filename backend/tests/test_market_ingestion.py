"Tests for quote and FX ingestion (mock transport)."
import pytest
import uuid
from datetime import datetime, UTC, timedelta
from decimal import Decimal

import httpx
from app.database.models import Asset, DataProvider, MarketQuote, FXRate, ProviderInstrument, Market
from app.data.ingestion.quotes import ingest_quotes, ingest_fx_rates

class MockTransport:
    """Mock transport that returns controlled Yahoo payloads."""
    def __init__(self, payloads: dict[str, dict]):
        self.payloads = payloads
        self.requests = []

    def handle_request(self, request):
        self.requests.append(request)
        url = str(request.url)
        for pattern, payload in self.payloads.items():
            if pattern in url:
                return httpx.Response(
                    status_code=200,
                    json=payload,
                    request=request,
                )
        return httpx.Response(
            status_code=404,
            json={"chart": {"error": {"description": "Not found"}}},
            request=request,
        )


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
        return httpx.Response(
            status_code=404,
            json={"chart": {"error": {"description": "Not found"}}},
            request=request,
        )


def test_ingest_quotes_success(db_session):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="BTC",
        name="Bitcoin",
        asset_type="CRYPTO",
        quote_currency="USDT",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="BTC-USD")
    db_session.add(pi)
    db_session.commit()

    now = datetime.now(UTC)
    payload = {
        "chart": {
            "result": [{
                "meta": {"currency": "USD"},
                "timestamp": [int(now.timestamp())],
                "indicators": {
                    "quote": [{
                        "open": [50000.0],
                        "high": [51000.0],
                        "low": [49000.0],
                        "close": [50500.0],
                        "volume": [1000.0],
                    }]
                }
            }],
            "error": None
        }
    }
    transport = MockTransport({"BTC-USD": payload})

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    res = ingest_quotes(db_session)
    iq.YahooProvider = orig

    assert res["written"] == 1
    assert any("BTC-USD" in str(r.url) for r in transport.requests)

    quote = db_session.query(MarketQuote).filter_by(asset_id=asset.id).one()
    assert quote.last_price == Decimal("50500.0")
    assert quote.currency == "USD"
    assert quote.source_timestamp is not None
    assert quote.freshness_status in ("LIVE", "STALE", "UNKNOWN")
    assert quote.provider_id == provider.id


def test_ingest_quotes_provider_failure(db_session):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="BTC",
        name="Bitcoin",
        asset_type="CRYPTO",
        quote_currency="USDT",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="BTC-USD")
    db_session.add(pi)
    db_session.commit()

    transport = MockTransport({})

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    res = ingest_quotes(db_session)
    iq.YahooProvider = orig

    assert res["written"] == 0
    assert res["skipped"] == 1
    assert len(res["skipped_reasons"]) == 1
    assert "provider does not offer BTC-USD" in res["skipped_reasons"][0]["reason"]

    count = db_session.query(MarketQuote).filter_by(asset_id=asset.id).count()
    assert count == 0


def test_ingest_quotes_empty_payload(db_session):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="BTC",
        name="Bitcoin",
        asset_type="CRYPTO",
        quote_currency="USDT",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="BTC-USD")
    db_session.add(pi)
    db_session.commit()

    payload = {"chart": {"result": [{"timestamp": [], "indicators": {"quote": [{}]}}], "error": None}}
    transport = MockTransport({"BTC-USD": payload})

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    res = ingest_quotes(db_session)
    iq.YahooProvider = orig

    assert res["written"] == 0
    assert res["skipped"] == 1
    assert len(res["skipped_reasons"]) == 1
    assert "provider returned no data" in res["skipped_reasons"][0]["reason"]


def test_ingest_quotes_idempotent(db_session):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="BTC",
        name="Bitcoin",
        asset_type="CRYPTO",
        quote_currency="USD",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="BTC-USD")
    db_session.add(pi)
    db_session.commit()

    now = datetime.now(UTC)
    payload = {
        "chart": {
            "result": [{
                "timestamp": [int(now.timestamp())],
                "indicators": {
                    "quote": [{
                        "open": [50000.0],
                        "high": [51000.0],
                        "low": [49000.0],
                        "close": [50500.0],
                        "volume": [1000.0],
                    }]
                }
            }],
            "error": None
        }
    }
    transport = MockTransport({"BTC-USD": payload})

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    ingest_quotes(db_session)
    res2 = ingest_quotes(db_session)
    iq.YahooProvider = orig

    count = db_session.query(MarketQuote).filter_by(asset_id=asset.id).count()
    assert count == 1
    assert res2["written"] == 1


def test_ingest_quotes_freshness_stale(db_session):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="BTC",
        name="Bitcoin",
        asset_type="CRYPTO",
        quote_currency="USD",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="BTC-USD")
    db_session.add(pi)
    db_session.commit()

    old_time = datetime.now(UTC) - timedelta(hours=6)
    payload = {
        "chart": {
            "result": [{
                "timestamp": [int(old_time.timestamp())],
                "indicators": {
                    "quote": [{
                        "open": [50000.0],
                        "high": [51000.0],
                        "low": [49000.0],
                        "close": [50500.0],
                        "volume": [1000.0],
                    }]
                }
            }],
            "error": None
        }
    }
    transport = MockTransport({"BTC-USD": payload})

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    res = ingest_quotes(db_session)
    iq.YahooProvider = orig

    assert res["written"] == 1
    quote = db_session.query(MarketQuote).filter_by(asset_id=asset.id).one()
    assert quote.freshness_status == "STALE"


def test_ingest_quotes_without_mapping_skipped(db_session):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="B2",
        name="Asset B2",
        asset_type="CRYPTO",
        quote_currency="USD",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()

    res = ingest_quotes(db_session)
    assert res["written"] == 0
    assert res["skipped"] == 1
    assert "no provider instrument mapping for B2" in res["skipped_reasons"][0]["reason"]


def test_ingest_fx_success(db_session):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="FX")
    db_session.add(provider)
    db_session.commit()

    now = datetime.now(UTC)
    payload = {
        "chart": {
            "result": [{
                "timestamp": [int(now.timestamp())],
                "indicators": {
                    "quote": [{
                        "open": [15000.0],
                        "high": [16000.0],
                        "low": [14000.0],
                        "close": [15500.0],
                        "volume": [100.0],
                    }]
                }
            }],
            "error": None
        }
    }
    transport = MockTransport({"USDIDR=X": payload})

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    res = ingest_fx_rates(db_session, pairs=[("USD", "IDR")])
    iq.YahooProvider = orig

    assert res["written"] == 1
    fx = db_session.query(FXRate).filter_by(base_currency="USD", quote_currency="IDR").one()
    assert fx.rate == Decimal("15500.0")
    assert fx.base_currency == "USD"
    assert fx.quote_currency == "IDR"
    assert fx.provider_id == provider.id


def test_ingest_fx_invalid_rate(db_session):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="FX")
    db_session.add(provider)
    db_session.commit()

    payload = {
        "chart": {
            "result": [{
                "timestamp": [int(datetime.now(UTC).timestamp())],
                "indicators": {
                    "quote": [{"close": [0.0]}]
                }
            }],
            "error": None
        }
    }
    transport = MockTransport({"USDIDR=X": payload})

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    res = ingest_fx_rates(db_session, pairs=[("USD", "IDR")])
    iq.YahooProvider = orig

    assert res["written"] == 0
    assert len(res["failed"]) == 1
    count = db_session.query(FXRate).filter_by(base_currency="USD", quote_currency="IDR").count()
    assert count == 0


def test_ingest_fx_reverse_skipped(db_session):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="FX")
    db_session.add(provider)
    db_session.commit()

    now = datetime.now(UTC)
    payload = {
        "chart": {
            "result": [{
                "timestamp": [int(now.timestamp())],
                "indicators": {
                    "quote": [{"close": [0.0000645]}]
                }
            }],
            "error": None
        }
    }
    transport = MockTransport({"IDRUSD=X": payload})

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    res = ingest_fx_rates(db_session, pairs=[("USD", "IDR")])
    iq.YahooProvider = orig

    assert res["written"] == 0
    assert res["skipped"] == 1
    assert res["failed"] == []
    assert res["skipped_reasons"], "skipped rows must carry an explicit reason"
    assert "direction" in res["skipped_reasons"][0]["reason"]
    count = db_session.query(FXRate).filter_by(base_currency="USD", quote_currency="IDR").count()
    assert count == 0


def test_ingest_fx_unexpected_error_failed(db_session):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="FX")
    db_session.add(provider)
    db_session.commit()

    class ExplodingTransport:
        def handle_request(self, request):
            raise RuntimeError("connection reset by peer")

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(
        base_url="https://query1.finance.yahoo.com", transport=ExplodingTransport()
    )

    res = ingest_fx_rates(db_session, pairs=[("USD", "IDR")])
    iq.YahooProvider = orig

    assert res["written"] == 0
    assert res["skipped"] == 0
    assert len(res["failed"]) == 1
    assert res["failed"][0]["reason"] != ""
    count = db_session.query(FXRate).count()
    assert count == 0


# === New retry tests ===

def test_quotes_ingestion_retry_429_then_200(db_session):
    """429 on first attempt then 200 -> row written, retry proven (assert request count > 1)."""
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="RETRY429",
        name="Retry 429",
        asset_type="CRYPTO",
        quote_currency="USDT",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="RETRY-429")
    db_session.add(pi)
    db_session.commit()

    now = datetime.now(UTC)
    payload = {
        "chart": {
            "result": [{
                "meta": {"currency": "USD"},
                "timestamp": [int(now.timestamp())],
                "indicators": {
                    "quote": [{
                        "open": [50000.0],
                        "high": [51000.0],
                        "low": [49000.0],
                        "close": [50500.0],
                        "volume": [1000.0],
                    }]
                }
            }],
            "error": None
        }
    }
    transport = RetryMockTransport({"RETRY-429": [429, payload]})

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    res = ingest_quotes(db_session)
    iq.YahooProvider = orig

    assert res["written"] == 1
    assert len(transport.requests) == 2


def test_quotes_ingestion_retry_500_twice_then_200(db_session):
    """500 twice then 200 -> row written, retry proven."""
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="RETRY500",
        name="Retry 500",
        asset_type="CRYPTO",
        quote_currency="USDT",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="RETRY-500")
    db_session.add(pi)
    db_session.commit()

    now = datetime.now(UTC)
    payload = {
        "chart": {
            "result": [{
                "meta": {"currency": "USD"},
                "timestamp": [int(now.timestamp())],
                "indicators": {
                    "quote": [{
                        "open": [50000.0],
                        "high": [51000.0],
                        "low": [49000.0],
                        "close": [50500.0],
                        "volume": [1000.0],
                    }]
                }
            }],
            "error": None
        }
    }
    transport = RetryMockTransport({"RETRY-500": [500, 500, payload]})

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    res = ingest_quotes(db_session)
    iq.YahooProvider = orig

    assert res["written"] == 1
    assert len(transport.requests) == 3


def test_quotes_ingestion_retry_429_continuous_fails(db_session):
    """429 continuously -> failed with real reason, attempt count matches limit, no hang."""
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="RETRY429F",
        name="Retry 429 Fail",
        asset_type="CRYPTO",
        quote_currency="USDT",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="RETRY-429-F")
    db_session.add(pi)
    db_session.commit()

    transport = RetryMockTransport({"RETRY-429-F": [429, 429, 429]})

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    res = ingest_quotes(db_session)
    iq.YahooProvider = orig

    assert res["failed"]
    assert "429" in res["failed"][0]["reason"]
    assert len(transport.requests) == 3


def test_quotes_ingestion_404_no_retry(db_session):
    """404 -> skipped, NO retry (assert request count == 1)."""
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="RETRY404",
        name="Retry 404",
        asset_type="CRYPTO",
        quote_currency="USDT",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="RETRY-404")
    db_session.add(pi)
    db_session.commit()

    transport = RetryMockTransport({})

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    res = ingest_quotes(db_session)
    iq.YahooProvider = orig

    assert res["skipped"] >= 1
    assert any("not offer" in r["reason"] or "404" in r["reason"] for r in res["skipped_reasons"])
    assert len(transport.requests) == 1


def test_quotes_ingestion_transport_error_failed(db_session):
    """transport error -> failed with real message."""
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="RETRYTRANS",
        name="Retry Transport",
        asset_type="CRYPTO",
        quote_currency="USDT",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()
    pi = ProviderInstrument(asset_id=asset.id, provider_id=provider.id, provider_symbol="RETRY-TRANS")
    db_session.add(pi)
    db_session.commit()

    class FailingTransport:
        def handle_request(self, request):
            raise httpx.ConnectError("connection reset by peer")

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="http://fail", transport=FailingTransport())

    res = ingest_quotes(db_session)
    iq.YahooProvider = orig

    assert res["failed"]
    assert "connection reset by peer" in res["failed"][0]["reason"]


# FX retry tests

def test_fx_ingestion_retry_429_then_200(db_session):
    """FX: 429 then 200 -> written."""
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="FX")
    db_session.add(provider)
    db_session.commit()

    now = datetime.now(UTC)
    payload = {
        "chart": {
            "result": [{
                "meta": {"currency": "USD"},
                "timestamp": [int(now.timestamp())],
                "indicators": {
                    "quote": [{
                        "open": [15500.0],
                        "high": [15600.0],
                        "low": [15400.0],
                        "close": [15500.0],
                        "volume": [100.0],
                    }]
                }
            }],
            "error": None
        }
    }
    transport = RetryMockTransport({"USDIDR=X": [429, payload]})

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    res = ingest_fx_rates(db_session, pairs=[("USD", "IDR")])
    iq.YahooProvider = orig

    assert res["written"] == 1
    assert len(transport.requests) == 2


def test_fx_ingestion_404_no_retry(db_session):
    """FX: 404 -> skipped, no retry."""
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="FX")
    db_session.add(provider)
    db_session.commit()

    transport = RetryMockTransport({})

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    res = ingest_fx_rates(db_session, pairs=[("USD", "IDR")])
    iq.YahooProvider = orig

    assert res["skipped"] == 1
    assert len(transport.requests) == 1


# === Multi-market ingestion tests ===

def test_quotes_ingestion_mixed_universe(db_session):
    """Mixed CRYPTO + US + IDX universe -> all three ingested using provider symbols."""
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    db_session.commit()
    
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
        db_session.add(ProviderInstrument(asset_id=btc.id, provider_id=provider.id, provider_symbol="BTC-USD"))
        db_session.add(ProviderInstrument(asset_id=aapl.id, provider_id=provider.id, provider_symbol="AAPL"))
        db_session.add(ProviderInstrument(asset_id=bbca.id, provider_id=provider.id, provider_symbol="BBCA.JK"))
        db_session.commit()
    
    now = datetime.now(UTC)
    payload_btc = {"chart": {"result": [{"meta": {"currency": "USD"}, "timestamp": [int(now.timestamp())], "indicators": {"quote": [{"open": [50000.0], "high": [51000.0], "low": [49000.0], "close": [50500.0], "volume": [1000.0]}]}}], "error": None}}
    payload_aapl = {"chart": {"result": [{"meta": {"currency": "USD"}, "timestamp": [int(now.timestamp())], "indicators": {"quote": [{"open": [150.0], "high": [155.0], "low": [148.0], "close": [153.0], "volume": [1000000.0]}]}}], "error": None}}
    payload_bbca = {"chart": {"result": [{"meta": {"currency": "USD"}, "timestamp": [int(now.timestamp())], "indicators": {"quote": [{"open": [9000.0], "high": [9100.0], "low": [8900.0], "close": [9050.0], "volume": [500000.0]}]}}], "error": None}}
    
    transport = MockTransport({
        "BTC-USD": payload_btc,
        "AAPL": payload_aapl,
        "BBCA.JK": payload_bbca,
    })
    
    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)
    
    res = ingest_quotes(db_session)
    iq.YahooProvider = orig
    
    assert res["requested"] == 3
    assert res["written"] == 3
    assert res["skipped"] == 0
    assert len(transport.requests) == 3
    requested_symbols = {str(r.url).split("/chart/")[1].split("?")[0] for r in transport.requests}
    assert requested_symbols == {"BTC-USD", "AAPL", "BBCA.JK"}


def test_quotes_ingestion_markets_filter_idx_only(db_session):
    """markets=['IDX'] -> only IDX assets ingested."""
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    db_session.commit()
    
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
        db_session.add(ProviderInstrument(asset_id=btc.id, provider_id=provider.id, provider_symbol="BTC-USD"))
        db_session.add(ProviderInstrument(asset_id=aapl.id, provider_id=provider.id, provider_symbol="AAPL"))
        db_session.add(ProviderInstrument(asset_id=bbca.id, provider_id=provider.id, provider_symbol="BBCA.JK"))
        db_session.commit()
    
    now = datetime.now(UTC)
    payload_bbca = {"chart": {"result": [{"meta": {"currency": "USD"}, "timestamp": [int(now.timestamp())], "indicators": {"quote": [{"open": [9000.0], "high": [9100.0], "low": [8900.0], "close": [9050.0], "volume": [500000.0]}]}}], "error": None}}
    
    transport = MockTransport({"BBCA.JK": payload_bbca})
    
    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)
    
    res = ingest_quotes(db_session, markets="IDX")
    iq.YahooProvider = orig
    
    assert res["requested"] == 1  # only BBCA
    assert res["written"] == 1
    assert len(transport.requests) == 1
    assert "BBCA.JK" in str(transport.requests[0].url)


def test_quotes_ingestion_no_mapping_skipped(db_session):
    """Asset without provider mapping -> skipped with reason."""
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    db_session.commit()
    
    m_crypto = Market(code="CRYPTO", name="Crypto", market_type="CRYPTO")
    m_us = Market(code="US", name="US Stocks", market_type="STOCK")
    db_session.add_all([m_crypto, m_us])
    db_session.commit()
    
    btc = Asset(symbol="BTCUSDT", name="Bitcoin", asset_type="CRYPTO", quote_currency="USDT", market_id=m_crypto.id, is_active=True)
    aapl = Asset(symbol="AAPL", name="Apple Inc.", asset_type="STOCK", quote_currency="USD", market_id=m_us.id, is_active=True)
    
    db_session.add(btc)
    db_session.add(aapl)
    db_session.commit()
    
    # Only BTC has mapping
    with db_session.no_autoflush:
        db_session.add(ProviderInstrument(asset_id=btc.id, provider_id=provider.id, provider_symbol="BTC-USD"))
        db_session.commit()
    
    now = datetime.now(UTC)
    payload_btc = {"chart": {"result": [{"meta": {"currency": "USD"}, "timestamp": [int(now.timestamp())], "indicators": {"quote": [{"open": [50000.0], "high": [51000.0], "low": [49000.0], "close": [50500.0], "volume": [1000.0]}]}}], "error": None}}
    
    transport = MockTransport({"BTC-USD": payload_btc})
    
    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)
    
    res = ingest_quotes(db_session)
    iq.YahooProvider = orig
    
    assert res["requested"] == 2
    assert res["written"] == 1
    assert res["skipped"] == 1
    assert any("no provider instrument mapping for AAPL" in r["reason"] for r in res["skipped_reasons"])