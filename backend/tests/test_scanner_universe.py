import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.database.models import Asset, DataProvider, ProviderInstrument, MarketCandle, ScannerRun, ScannerResult, Market
from app.engines.scanner.service import run_scanner
import app.engines.runner as runner

@pytest.fixture()
def seeded_provider(db_session):
    p = db_session.query(DataProvider).filter_by(code="YAHOO").first()
    if not p:
        p = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="CRYPTO")
        db_session.add(p)
        db_session.commit()
    return p

@pytest.fixture()
def universe_data(db_session, seeded_provider):
    provider = seeded_provider
    # Markets - Ensure uniqueness/existence
    for code, name, mtype in [("CRYPTO", "Crypto", "CRYPTO"), ("US", "US Stocks", "STOCK"), ("IDX", "IDX Stocks", "STOCK")]:
        m = db_session.query(Market).filter_by(code=code).first()
        if not m:
            db_session.add(Market(code=code, name=name, market_type=mtype))
    db_session.flush()
    crypto_m = db_session.query(Market).filter_by(code="CRYPTO").one()
    us_m = db_session.query(Market).filter_by(code="US").one()
    idx_m = db_session.query(Market).filter_by(code="IDX").one()
    
    # Assets
    assets = {
        "CRYPTO": Asset(symbol="BTC_TEST", name="Bitcoin", asset_type="CRYPTO", market_id=crypto_m.id, is_active=True),
        "US": Asset(symbol="AAPL_TEST", name="Apple", asset_type="STOCK", market_id=us_m.id, is_active=True),
        "IDX": Asset(symbol="BBCA_TEST", name="BBCA", asset_type="STOCK", market_id=idx_m.id, is_active=True),
        "NOMAP": Asset(symbol="NOMAP_TEST", name="NoMap", asset_type="CRYPTO", market_id=crypto_m.id, is_active=True),
        "LOWDATA": Asset(symbol="LOWDATA_TEST", name="LowData", asset_type="CRYPTO", market_id=crypto_m.id, is_active=True)
    }
    db_session.add_all(assets.values())
    db_session.flush()
    
    # Provider mapping
    yahoo = db_session.query(DataProvider).filter_by(code="YAHOO").one()
    for key, a in assets.items():
        if key == "NOMAP": continue
        p = provider if key == "CRYPTO" else yahoo
        db_session.add(ProviderInstrument(asset_id=a.id, provider_id=p.id, provider_symbol=f"{a.symbol}-USD", is_active=True))
    db_session.flush()
    
    # Candles
    now = datetime.now(timezone.utc)
    for key, a in assets.items():
        if key == "NOMAP": continue
        count = 5 if key == "LOWDATA" else 60
        p = provider if key == "CRYPTO" else yahoo
        for i in range(count):
            db_session.add(MarketCandle(
                asset_id=a.id, provider_id=p.id, timeframe="1h",
                open_time=now - timedelta(seconds=(count - i) * 3600), close_time=now - timedelta(seconds=(count - 1 - i) * 3600),
                open_price=100, high_price=110, low_price=90, close_price=10500,
                volume=1000, currency="USD", candle_status="CLOSED"
            ))
    db_session.commit()
    return assets

def test_scanner_market_filter(db_session, universe_data):
    run = run_scanner(db_session, timeframe="1h", markets=["CRYPTO"])
    res = db_session.query(ScannerResult).filter_by(scanner_run_id=run.id).all()
    symbols = [db_session.get(Asset, r.asset_id).symbol for r in res]
    assert "BTC_TEST" in symbols
    assert "AAPL_TEST" not in symbols
    assert "BBCA_TEST" not in symbols

def test_scanner_no_mapping(db_session, universe_data):
    run = run_scanner(db_session, timeframe="1h")
    skipped = [s["symbol"] for s in run.execution_metadata["skipped"]]
    assert "NOMAP_TEST" in skipped

def test_scanner_insufficient_candles(db_session, universe_data):
    run = run_scanner(db_session, timeframe="1h")
    skipped = [s["symbol"] for s in run.execution_metadata["skipped"]]
    assert "LOWDATA_TEST" in skipped

def test_scanner_engine_failure_isolated(db_session, universe_data):
    orig = runner.run_instrument_engines
    runner.run_instrument_engines = lambda s, a, t: exec('raise RuntimeError("fail")') if a.symbol == "BTC_TEST" else orig(s, a, t)
    try:
        run = run_scanner(db_session, timeframe="1h", markets=["CRYPTO"])
        assert run.execution_status == "COMPLETED"
        skipped = [s["symbol"] for s in run.execution_metadata["skipped"]]
        assert "BTC_TEST" in skipped
        res = db_session.query(ScannerResult).filter_by(scanner_run_id=run.id).all()
        assert not any(db_session.get(Asset, r.asset_id).symbol == "BTC_TEST" for r in res)
    finally:
        runner.run_instrument_engines = orig

def test_scanner_all_eligible_regression(db_session, universe_data):
    run = run_scanner(db_session, timeframe="1h")
    res = db_session.query(ScannerResult).filter_by(scanner_run_id=run.id).all()
    symbols = [db_session.get(Asset, r.asset_id).symbol for r in res]
    assert "BTC_TEST" in symbols
    assert "AAPL_TEST" in symbols
    assert "BBCA_TEST" in symbols
