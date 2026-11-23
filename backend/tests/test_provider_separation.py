import pytest
import uuid
from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session
from app.database.models import Asset, DataProvider, Market, ProviderInstrument, MarketCandle
from app.engines.runner import load_candles, resolve_provider_id

def test_provider_separation(db_session: Session):
    """Seed candle for one asset from two providers -> load_candles returns only one."""
    provider1 = db_session.query(DataProvider).filter_by(code="YAHOO").first()
    if not provider1:
        provider1 = DataProvider(code="YAHOO", name="Yahoo", provider_type="CRYPTO")
        db_session.add(provider1)
    
    # Try to get or create BYBIT
    provider2 = db_session.query(DataProvider).filter_by(code="BYBIT").first()
    if not provider2:
        provider2 = DataProvider(code="BYBIT", name="Bybit", provider_type="CRYPTO")
        db_session.add(provider2)
    
    db_session.commit()

    # Try to get or create Market
    m_crypto = db_session.query(Market).filter_by(code="CRYPTO").first()
    if not m_crypto:
        m_crypto = Market(code="CRYPTO", name="Crypto", market_type="CRYPTO")
        db_session.add(m_crypto)
    
    db_session.commit()

    asset = Asset(symbol="BTCUSDT", name="Bitcoin", asset_type="CRYPTO", quote_currency="USDT", market_id=m_crypto.id, is_active=True)
    db_session.add(asset)
    db_session.commit()

    db_session.add_all([
        ProviderInstrument(asset_id=asset.id, provider_id=provider1.id, provider_symbol="BTC-USD", is_active=True),
        ProviderInstrument(asset_id=asset.id, provider_id=provider2.id, provider_symbol="BTCUSDT", is_active=True),
    ])
    db_session.commit()

    # Seed 2 candles each
    now = datetime.now(UTC)
    db_session.add_all([
        MarketCandle(asset_id=asset.id, provider_id=provider1.id, timeframe="1h", open_time=now, open_price=100, high_price=100, low_price=100, close_price=100, currency="USD", candle_status="CLOSED"),
        MarketCandle(asset_id=asset.id, provider_id=provider2.id, timeframe="1h", open_time=now, open_price=200, high_price=200, low_price=200, close_price=200, currency="USD", candle_status="CLOSED"),
    ])
    db_session.commit()

    # Test load_candles without provider (should resolve to YAHOO per settings.crypto_provider=YAHOO)
    candles = load_candles(db_session, asset.id, "1h")
    assert len(candles) == 1
    assert candles[0]["close"] == 100.0
    
    # Test load_candles with BYBIT
    candles_bybit = load_candles(db_session, asset.id, "1h", provider_id=provider2.id)
    assert len(candles_bybit) == 1
    assert candles_bybit[0]["close"] == 200.0


def test_load_candles_neutralises_silent_provider_mixing(db_session: Session):
    """Asset without a configured mapping must not mix providers silently.

    Resolution falls back to the provider that wrote the most recent candle, so the
    returned series is still single-source instead of interleaving two providers.
    """
    p_yahoo = db_session.query(DataProvider).filter_by(code="YAHOO").one_or_none()
    if p_yahoo is None:
        p_yahoo = DataProvider(code="YAHOO", name="Yahoo", provider_type="CRYPTO")
        db_session.add(p_yahoo)
    p_bybit = db_session.query(DataProvider).filter_by(code="BYBIT").one_or_none()
    if p_bybit is None:
        p_bybit = DataProvider(code="BYBIT", name="Bybit", provider_type="CRYPTO")
        db_session.add(p_bybit)
    db_session.commit()

    # No market_id -> resolve_provider_id returns None (no mapping to trust).
    asset = Asset(
        symbol="NOMAPUSDT", name="No Mapping", asset_type="CRYPTO",
        quote_currency="USDT", market_id=None, is_active=True,
    )
    db_session.add(asset)
    db_session.commit()

    now = datetime.now(UTC)
    older = now - timedelta(hours=1)
    db_session.add_all([
        MarketCandle(asset_id=asset.id, provider_id=p_bybit.id, timeframe="1h", open_time=older,
                     open_price=10, high_price=10, low_price=10, close_price=10,
                     currency="USD", candle_status="CLOSED"),
        # Latest candle belongs to YAHOO -> that provider must win, alone.
        MarketCandle(asset_id=asset.id, provider_id=p_yahoo.id, timeframe="1h", open_time=now,
                     open_price=20, high_price=20, low_price=20, close_price=20,
                     currency="USD", candle_status="CLOSED"),
    ])
    db_session.commit()

    candles = load_candles(db_session, asset.id, "1h")
    assert [c["close"] for c in candles] == [20.0], "series must come from a single provider"
    assert len(candles) == 1, "candles from the other provider must not be interleaved"
