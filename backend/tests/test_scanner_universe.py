import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.database.models import Asset, DataProvider, ProviderInstrument, MarketCandle, ScannerRun, ScannerResult
from app.engines.scanner.service import run_scanner

@pytest.fixture()
def seeded_provider(db_session):
    p = db_session.query(DataProvider).filter_by(code="YAHOO").first()
    if not p:
        p = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
        db_session.add(p)
        db_session.commit()
    return p

def test_scanner_universe_mixed_assets(db_session, seeded_provider):
    provider = seeded_provider
    # Ensure market exists
    from app.database.models import Market
    crypto_m = db_session.query(Market).filter_by(code="CRYPTO").first()
    if not crypto_m:
        crypto_m = Market(code="CRYPTO", name="Crypto", market_type="CRYPTO")
        db_session.add(crypto_m)
    us_m = Market(code="US", name="US Stocks", market_type="STOCK")
    db_session.add(us_m)
    db_session.commit()
    
    # Use unique symbols
    crypto = Asset(symbol="BTC_TEST", name="Bitcoin Test", asset_type="CRYPTO", market_id=crypto_m.id, is_active=True)
    db_session.add(crypto)
    stock = Asset(symbol="AAPL_TEST", name="Apple Test", asset_type="STOCK", market_id=us_m.id, is_active=True)
    db_session.add(stock)
    nomap = Asset(symbol="NOMAP_TEST", name="No Mapping Test", asset_type="CRYPTO", market_id=crypto_m.id, is_active=True)
    db_session.add(nomap)
    lowdata = Asset(symbol="LOWDATA_TEST", name="Low Data Test", asset_type="CRYPTO", market_id=crypto_m.id, is_active=True)
    db_session.add(lowdata)
    
    db_session.commit()
    
    # Add mappings
    # Mapping for US stock needs YAHOO provider
    yahoo = db_session.query(DataProvider).filter_by(code="YAHOO").one()
    for a in [crypto, stock, lowdata]:
        p = provider if a.asset_type == "CRYPTO" else yahoo
        db_session.add(ProviderInstrument(asset_id=a.id, provider_id=p.id, provider_symbol=f"{a.symbol}-USD", is_active=True))
    
    now = datetime.now(timezone.utc)
    for a in [crypto, stock]:
        for i in range(60):
            db_session.add(MarketCandle(
                asset_id=a.id, provider_id=provider.id if a.asset_type=="CRYPTO" else yahoo.id, timeframe="1h",
                open_time=now - timedelta(seconds=(60 - i) * 3600), close_time=now - timedelta(seconds=(59 - i) * 3600),
                open_price=100, high_price=110, low_price=90, close_price=105,
                volume=1000, currency="USD", candle_status="CLOSED"
            ))
            
    for i in range(5):
        db_session.add(MarketCandle(
            asset_id=lowdata.id, provider_id=provider.id, timeframe="1h",
            open_time=now - timedelta(seconds=(5 - i) * 3600), close_time=now - timedelta(seconds=(4 - i) * 3600),
            open_price=100, high_price=110, low_price=90, close_price=105,
            volume=1000, currency="USD", candle_status="CLOSED"
        ))
    
    db_session.commit()
    
    # Run scanner - crypto only
    run = run_scanner(db_session, timeframe="1h", markets=["CRYPTO"])
    
    assert run.execution_status == "COMPLETED"
    
    # verify crypto appears
    res = db_session.query(ScannerResult).filter_by(scanner_run_id=run.id).all()
    symbols = [db_session.get(Asset, r.asset_id).symbol for r in res]
    assert "BTC_TEST" in symbols
    assert "AAPL_TEST" not in symbols
    
    # verify skip
    skipped = run.execution_metadata["skipped"]
    assert any(s["symbol"] == "LOWDATA_TEST" for s in skipped)

def test_scanner_engine_failure_isolated(db_session, seeded_provider):
    provider = seeded_provider
    asset = Asset(symbol="FAIL_TEST", name="Fail Test", asset_type="CRYPTO", is_active=True)
    db_session.add(asset)
    asset2 = Asset(symbol="PASS_TEST", name="Pass Test", asset_type="CRYPTO", is_active=True)
    db_session.add(asset2)
    db_session.commit()
    
    for a in [asset, asset2]:
        with db_session.no_autoflush:
            pi = db_session.query(ProviderInstrument).filter_by(asset_id=a.id, provider_id=provider.id).first()
            if not pi:
                db_session.add(ProviderInstrument(asset_id=a.id, provider_id=provider.id, provider_symbol=f"{a.symbol}-USD", is_active=True))
        now = datetime.now(timezone.utc)
        for i in range(60):
            db_session.add(MarketCandle(
                asset_id=a.id, provider_id=provider.id, timeframe="1h",
                open_time=now - timedelta(seconds=(60 - i) * 3600), close_time=now - timedelta(seconds=(59 - i) * 3600),
                open_price=100, high_price=110, low_price=90, close_price=105,
                volume=1000, currency="USD", candle_status="CLOSED"
            ))
    db_session.commit()
    
    import app.engines.runner as runner
    orig_run_engines = runner.run_instrument_engines
    
    def mock_run_engines(session, asset_obj, timeframe):
        if asset_obj.symbol == "FAIL_TEST":
            raise RuntimeError("Engine crashed!")
        return orig_run_engines(session, asset_obj, timeframe)
    
    runner.run_instrument_engines = mock_run_engines
    
    try:
        run = run_scanner(db_session, timeframe="1h")
        assert run.execution_status == "COMPLETED"
        assert run.eligible_count >= 1
        
        metadata = run.execution_metadata
        skipped = metadata["skipped"]
        assert any(s["symbol"] == "FAIL_TEST" and "engine failure" in s["reason"] for s in skipped)
    finally:
        runner.run_instrument_engines = orig_run_engines