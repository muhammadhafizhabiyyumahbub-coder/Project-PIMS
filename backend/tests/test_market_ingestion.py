"Tests for quote and FX ingestion (mock transport)."
import pytest
import uuid
from datetime import datetime, UTC, timedelta
from decimal import Decimal

import httpx
from app.database.models import Asset, DataProvider, MarketQuote, FXRate
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


def test_ingest_quotes_success(db_session):
    # Setup asset
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="BTC-USD",
        name="Bitcoin",
        asset_type="CRYPTO",
        quote_currency="USD",
        is_active=True,
    )
    db_session.add(asset)
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

    res = ingest_quotes(db_session)
    iq.YahooProvider = orig

    assert res["written"] == 1
    assert res["failed"] == []
    assert res["is_realtime"] is False

    quote = db_session.query(MarketQuote).filter_by(asset_id=asset.id).one()
    assert quote.last_price == Decimal("50500.0")
    assert quote.currency == "USD"
    assert quote.source_timestamp is not None
    assert quote.source_timestamp.tzinfo is not None
    assert quote.freshness_status in ("LIVE", "STALE", "UNKNOWN")
    assert quote.provider_id == provider.id


def test_ingest_quotes_provider_failure(db_session):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="BTC-USD",
        name="Bitcoin",
        asset_type="CRYPTO",
        quote_currency="USD",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()

    transport = MockTransport({})  # no payload → 404

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    res = ingest_quotes(db_session)
    iq.YahooProvider = orig

    assert res["written"] == 0
    assert len(res["failed"]) == 1
    assert res["failed"][0]["reason"] != ""

    count = db_session.query(MarketQuote).filter_by(asset_id=asset.id).count()
    assert count == 0


def test_ingest_quotes_empty_payload(db_session):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="BTC-USD",
        name="Bitcoin",
        asset_type="CRYPTO",
        quote_currency="USD",
        is_active=True,
    )
    db_session.add(asset)
    db_session.commit()

    payload = {"chart": {"result": [{"timestamp": [], "indicators": {"quote": [{}]}}], "error": None}}
    transport = MockTransport({"BTC-USD": payload})

    import app.data.ingestion.quotes as iq
    orig = iq.YahooProvider
    iq.YahooProvider = lambda *a, **kw: orig(base_url="https://query1.finance.yahoo.com", transport=transport)

    res = ingest_quotes(db_session)
    iq.YahooProvider = orig

    assert res["written"] == 0
    assert len(res["failed"]) == 1


def test_ingest_quotes_idempotent(db_session):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="BTC-USD",
        name="Bitcoin",
        asset_type="CRYPTO",
        quote_currency="USD",
        is_active=True,
    )
    db_session.add(asset)
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
    assert res2["written"] == 1  # same row returned


def test_ingest_quotes_freshness_stale(db_session):
    provider = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
    db_session.add(provider)
    asset = Asset(
        symbol="BTC-USD",
        name="Bitcoin",
        asset_type="CRYPTO",
        quote_currency="USD",
        is_active=True,
    )
    db_session.add(asset)
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

    # Only provide IDR→USD, not USD→IDR
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

    # Should skip because inverse not auto-flipped
    assert res["written"] == 0
    assert res["skipped"] >= 1 or len(res["failed"]) >= 1  # either skipped or failed
    count = db_session.query(FXRate).filter_by(base_currency="USD", quote_currency="IDR").count()
    assert count == 0
