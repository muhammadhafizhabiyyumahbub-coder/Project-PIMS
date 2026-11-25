import pytest
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from app.database.models import Asset, DataProvider, MarketCandle, ScannerResult, ScannerRun, Market
from app.api.rest.dashboard import _opportunity

def test_scanner_currency_provenance_labels(db_session: Session):
    """Assets with different source and quote currencies show both."""
    from app.data.storage.universe import ensure_universe
    univ = ensure_universe(db_session)
    
    # Use assets already created by ensure_universe
    # ensure_universe creates assets as (symbol, name, base, quote, yahoo_symbol)
    asset1 = db_session.query(Asset).filter_by(symbol="BTCUSDT").one()
    asset1.quote_currency = "USDT" # Force specific quote
    db_session.commit()
    
    asset2 = db_session.query(Asset).filter_by(symbol="ETHUSDT").one()
    asset2.quote_currency = "IDR" # Simulate stock-like asset
    db_session.commit()
    
    m_crypto = db_session.query(Market).filter_by(code="CRYPTO").one()
    provider = db_session.query(DataProvider).filter_by(code="YAHOO").one()

    # Seed candles
    now = datetime.now(UTC)
    db_session.add_all([
        MarketCandle(asset_id=asset1.id, provider_id=provider.id, timeframe="1h", open_time=now, open_price=50000, high_price=51000, low_price=49000, close_price=50000, currency="USD", candle_status="CLOSED"),
        MarketCandle(asset_id=asset2.id, provider_id=provider.id, timeframe="1h", open_time=now, open_price=9000, high_price=9100, low_price=8900, close_price=9000, currency="IDR", candle_status="CLOSED"),
    ])
    db_session.commit()

    # Mock ScannerRun and Result
    from app.database.models import ScannerResult, ScannerRun
    run = ScannerRun(execution_mode="MANUAL", execution_status="COMPLETED", started_at=now, completed_at=now)
    db_session.add(run)
    db_session.commit()

    r1 = ScannerResult(scanner_run_id=run.id, asset_id=asset1.id, timeframe="1h", score=90.0, rank=1, result_status="ELIGIBLE", freshness_status="LIVE", data_timestamp=now, created_at=now)
    r2 = ScannerResult(scanner_run_id=run.id, asset_id=asset2.id, timeframe="1h", score=80.0, rank=2, result_status="ELIGIBLE", freshness_status="LIVE", data_timestamp=now, created_at=now)
    db_session.add_all([r1, r2])
    db_session.commit()

    # Test opportunity objects
    opp1 = _opportunity(db_session, r1, asset1, m_crypto, "1h")
    assert opp1["quote_currency"] == "USDT"
    assert opp1["data_currency"] == "USD"

    opp2 = _opportunity(db_session, r2, asset2, m_crypto, "1h")
    assert opp2["quote_currency"] == "IDR"
    assert opp2["data_currency"] == "IDR"

def test_scanner_data_currency_none(db_session: Session):
    """Asset without candles -> data_currency is None."""
    from app.database.models import ScannerResult, ScannerRun
    now = datetime.now(UTC)
    # Use empty asset
    asset = Asset(symbol="EMPTY_TEST", name="E TEST", asset_type="CRYPTO", quote_currency="USD", is_active=True)
    db_session.add(asset)
    db_session.commit()
    
    run = ScannerRun(execution_mode="MANUAL", execution_status="COMPLETED", started_at=now, completed_at=now)
    db_session.add(run)
    db_session.commit()
    
    r = ScannerResult(scanner_run_id=run.id, asset_id=asset.id, timeframe="1h", score=10.0, rank=1, result_status="ELIGIBLE", freshness_status="LIVE", data_timestamp=now, created_at=now)
    db_session.add(r)
    db_session.commit()
    
    opp = _opportunity(db_session, r, asset, None, "1h")
    assert opp["data_currency"] is None
