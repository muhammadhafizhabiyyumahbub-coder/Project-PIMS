"""Test: Scanner uses single-provider series via load_candles provider_id filter."""
import pytest
from datetime import datetime, UTC, timedelta
from sqlalchemy.orm import Session
from app.database.models import Asset, DataProvider, Market, ProviderInstrument, MarketCandle, ScannerRun, ScannerResult
from app.engines.scanner.service import run_scanner

def test_scanner_provider_isolation(db_session: Session):
    """Asset with candles from two providers -> scan uses only resolved provider (YAHOO)."""
    # Setup providers
    provider_yahoo = db_session.query(DataProvider).filter_by(code="YAHOO").first()
    if not provider_yahoo:
        provider_yahoo = DataProvider(code="YAHOO", name="Yahoo", provider_type="CRYPTO")
        db_session.add(provider_yahoo)
    
    provider_bybit = DataProvider(code="BYBIT", name="Bybit", provider_type="CRYPTO")
    db_session.add(provider_bybit)
    db_session.commit()

    # Setup market
    m_crypto = db_session.query(Market).filter_by(code="CRYPTO").first()
    if not m_crypto:
        m_crypto = Market(code="CRYPTO", name="Crypto", market_type="CRYPTO")
        db_session.add(m_crypto)
    db_session.commit()

    # Create asset with dual provider mappings
    asset = Asset(symbol="BTCUSDT", name="Bitcoin", asset_type="CRYPTO", quote_currency="USDT", market_id=m_crypto.id, is_active=True)
    db_session.add(asset)
    db_session.commit()

    db_session.add_all([
        ProviderInstrument(asset_id=asset.id, provider_id=provider_yahoo.id, provider_symbol="BTC-USD", is_active=True),
        ProviderInstrument(asset_id=asset.id, provider_id=provider_bybit.id, provider_symbol="BTCUSDT", is_active=True),
    ])
    db_session.commit()

    # Seed candles: Yahoo provides 60 candles (sufficient), Bybit provides different values
    now = datetime.now(UTC)
    yahoo_candles = []
    bybit_candles = []
    for i in range(60):
        t = now - timedelta(hours=59 - i)
        # Use high volume to meet MIN_QUOTE_VOLUME_24H (1M USDT)
        yahoo_candles.append(MarketCandle(
            asset_id=asset.id, provider_id=provider_yahoo.id, timeframe="1h",
            open_time=t, close_time=t, open_price=50000 + i, high_price=51000 + i,
            low_price=49000 + i, close_price=50500 + i, volume=100000, currency="USD", candle_status="CLOSED"
        ))
        # Bybit has only 30 candles (insufficient), and different values
        if i < 30:
            bybit_candles.append(MarketCandle(
                asset_id=asset.id, provider_id=provider_bybit.id, timeframe="1h",
                open_time=t, close_time=t, open_price=60000 + i, high_price=61000 + i,
                low_price=59000 + i, close_price=60500 + i, volume=100000, currency="USD", candle_status="CLOSED"
            ))
    db_session.add_all(yahoo_candles + bybit_candles)
    db_session.commit()

    # Run scanner - should use YAHOO provider (settings.crypto_provider=YAHOO)
    run = run_scanner(db_session, timeframe="1h")
    
    # Verify scan completed successfully using Yahoo data
    print("SKIPPED REASONS:", run.execution_metadata.get("skipped"))
    assert run.execution_status == "COMPLETED"
    assert run.result_count == 1
    result = db_session.query(ScannerResult).filter_by(scanner_run_id=run.id).one()
    assert result.asset_id == asset.id
    
    # Verify scanner used Yahoo candles (close prices around 50500, not Bybit's 60500)
    # The momentum calculation would use Yahoo's ~50000 range
    # We assert the run didn't fail and produced a result from the YAHOO series
    assert result.result_status == "COMPLETED"
    
    # Additional: run scan with explicit provider override
    from app.engines.runner import load_candles
    yahoo_candles_loaded = load_candles(db_session, asset.id, "1h", provider_id=provider_yahoo.id)
    bybit_candles_loaded = load_candles(db_session, asset.id, "1h", provider_id=provider_bybit.id)
    
    assert len(yahoo_candles_loaded) == 60
    assert len(bybit_candles_loaded) == 30
    # First candle close should be 50500 (Yahoo) not 60500 (Bybit)
    assert abs(yahoo_candles_loaded[0]["close"] - 50500) < 1
    assert abs(bybit_candles_loaded[0]["close"] - 60500) < 1