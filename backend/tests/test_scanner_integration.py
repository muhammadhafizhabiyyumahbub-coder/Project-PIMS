import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
from app.database.models import (
    Asset, DataProvider, ProviderInstrument, MarketCandle, 
    ScannerRun, ScannerResult, Market
)
from app.engines.scanner.service import run_scanner

@pytest.fixture
def scanner_setup(db_session):
    # Providers
    yahoo = db_session.query(DataProvider).filter_by(code="YAHOO").first()
    if not yahoo:
        yahoo = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="GENERAL")
        db_session.add(yahoo)
    
    bybit = db_session.query(DataProvider).filter_by(code="BYBIT").first()
    if not bybit:
        bybit = DataProvider(code="BYBIT", name="Bybit", provider_type="CRYPTO")
        db_session.add(bybit)
    
    db_session.flush()

    # Markets
    crypto_m = db_session.query(Market).filter_by(code="CRYPTO").first()
    if not crypto_m:
        crypto_m = Market(code="CRYPTO", name="Cryptocurrency", market_type="CRYPTO")
        db_session.add(crypto_m)
    
    us_m = db_session.query(Market).filter_by(code="US").first()
    if not us_m:
        us_m = Market(code="US", name="US Stocks", market_type="STOCK")
        db_session.add(us_m)
        
    idx_m = db_session.query(Market).filter_by(code="IDX").first()
    if not idx_m:
        idx_m = Market(code="IDX", name="IDX Stocks", market_type="STOCK")
        db_session.add(idx_m)

    db_session.commit()
    return {"yahoo": yahoo, "bybit": bybit, "crypto_m": crypto_m, "us_m": us_m, "idx_m": idx_m}

def create_candles(db_session, asset_id, provider_id, count=65, base_price=100.0, volume=2000.0, stale_hours=0, currency="USD"):
    now = datetime.now(timezone.utc) - timedelta(hours=stale_hours)
    candles = []
    for i in range(count):
        # price drift for momentum/trend calculations
        price = base_price + i
        open_time = now - timedelta(hours=count - i)
        close_time = now - timedelta(hours=count - i - 1)
        candle = MarketCandle(
            asset_id=asset_id,
            provider_id=provider_id,
            timeframe="1h",
            open_time=open_time,
            close_time=close_time,
            open_price=price - 1,
            high_price=price + 1,
            low_price=price - 2,
            close_price=price,
            volume=volume,
            quote_volume=price * volume,
            currency=currency,
            candle_status="CLOSED"
        )
        db_session.add(candle)
        candles.append(candle)
    db_session.flush()
    return candles

def test_scanner_crypto_only(db_session, scanner_setup):
    """Test scanner with only crypto assets."""
    with patch("app.engines.scanner.service.get_settings") as mock_settings:
        mock_settings.return_value.crypto_provider = "BYBIT"
        # BTC: crypto, market_id=crypto_m.id
        btc = Asset(symbol="BTC", name="Bitcoin", asset_type="CRYPTO", market_id=scanner_setup["crypto_m"].id)
        db_session.add(btc)
        db_session.flush()
        db_session.add(ProviderInstrument(asset_id=btc.id, provider_id=scanner_setup["bybit"].id, provider_symbol="BTCUSDT"))
        
        create_candles(db_session, btc.id, scanner_setup["bybit"].id)
        db_session.commit()
        
        run = run_scanner(db_session, timeframe="1h", markets=["CRYPTO"])
        assert run.result_count == 1
        res = db_session.query(ScannerResult).filter_by(scanner_run_id=run.id).one()
        assert res.score == 50.0

def test_scanner_us_stocks_only(db_session, scanner_setup):
    """Test scanner with only US stocks (Yahoo)."""
    with patch("app.engines.scanner.service.get_settings") as mock_settings:
        mock_settings.return_value.crypto_provider = "BYBIT"
        aapl = Asset(symbol="AAPL", name="Apple", asset_type="STOCK", market_id=scanner_setup["us_m"].id)
        db_session.add(aapl)
        db_session.flush()
        db_session.add(ProviderInstrument(asset_id=aapl.id, provider_id=scanner_setup["yahoo"].id, provider_symbol="AAPL"))
        
        create_candles(db_session, aapl.id, scanner_setup["yahoo"].id)
        db_session.commit()
        
        run = run_scanner(db_session, timeframe="1h", markets=["US"])
        assert run.result_count == 1
        res = db_session.query(ScannerResult).filter_by(scanner_run_id=run.id).one()
        assert res.score == 50.0

def test_scanner_idx_only(db_session, scanner_setup):
    """Test scanner with only IDX stocks (Yahoo)."""
    with patch("app.engines.scanner.service.get_settings") as mock_settings:
        mock_settings.return_value.crypto_provider = "BYBIT"
        bbca = Asset(symbol="BBCA", name="BBCA", asset_type="STOCK", market_id=scanner_setup["idx_m"].id)
        db_session.add(bbca)
        db_session.flush()
        db_session.add(ProviderInstrument(asset_id=bbca.id, provider_id=scanner_setup["yahoo"].id, provider_symbol="BBCA.JK"))
        
        create_candles(db_session, bbca.id, scanner_setup["yahoo"].id)
        db_session.commit()
        
        run = run_scanner(db_session, timeframe="1h", markets=["IDX"])
        assert run.result_count == 1

def test_scanner_mixed_markets(db_session, scanner_setup):
    """Test scanner with mixed markets."""
    with patch("app.engines.scanner.service.get_settings") as mock_settings:
        mock_settings.return_value.crypto_provider = "BYBIT"
        btc = Asset(symbol="BTC2", name="Bitcoin", asset_type="CRYPTO", market_id=scanner_setup["crypto_m"].id)
        aapl = Asset(symbol="AAPL2", name="Apple", asset_type="STOCK", market_id=scanner_setup["us_m"].id)
        db_session.add_all([btc, aapl])
        db_session.flush()
        db_session.add(ProviderInstrument(asset_id=btc.id, provider_id=scanner_setup["bybit"].id, provider_symbol="BTC2USDT"))
        db_session.add(ProviderInstrument(asset_id=aapl.id, provider_id=scanner_setup["yahoo"].id, provider_symbol="AAPL2"))
        
        create_candles(db_session, btc.id, scanner_setup["bybit"].id, base_price=100)
        create_candles(db_session, aapl.id, scanner_setup["yahoo"].id, base_price=200)
        db_session.commit()
        
        run = run_scanner(db_session, timeframe="1h")
        assert run.result_count == 2
        results = db_session.query(ScannerResult).filter_by(scanner_run_id=run.id).order_by(ScannerResult.rank).all()
        assert results[0].asset_id == btc.id

def test_scanner_missing_provider_mapping(db_session, scanner_setup):
    """Asset without mapping should be skipped."""
    with patch("app.engines.scanner.service.get_settings") as mock_settings:
        mock_settings.return_value.crypto_provider = "BYBIT"
        nomap = Asset(symbol="NOMAP", name="No Map", asset_type="CRYPTO", market_id=scanner_setup["crypto_m"].id)
        db_session.add(nomap)
        db_session.commit()
        
        run = run_scanner(db_session, timeframe="1h")
        skipped = [s["symbol"] for s in run.execution_metadata["skipped"]]
        assert "NOMAP" in skipped
        assert any("no provider mapping" in s["reason"] for s in run.execution_metadata["skipped"] if s["symbol"] == "NOMAP")

def test_scanner_insufficient_candles(db_session, scanner_setup):
    """Asset with < 50 candles should be skipped."""
    with patch("app.engines.scanner.service.get_settings") as mock_settings:
        mock_settings.return_value.crypto_provider = "BYBIT"
        lowdata = Asset(symbol="LOW", name="Low Data", asset_type="CRYPTO", market_id=scanner_setup["crypto_m"].id)
        db_session.add(lowdata)
        db_session.flush()
        db_session.add(ProviderInstrument(asset_id=lowdata.id, provider_id=scanner_setup["bybit"].id, provider_symbol="LOWUSDT"))
        
        create_candles(db_session, lowdata.id, scanner_setup["bybit"].id, count=10)
        db_session.commit()
        
        run = run_scanner(db_session, timeframe="1h")
        skipped = [s["symbol"] for s in run.execution_metadata["skipped"]]
        assert "LOW" in skipped
        assert any("insufficient candles" in s["reason"] for s in run.execution_metadata["skipped"] if s["symbol"] == "LOW")

def test_scanner_provider_timeout(db_session, scanner_setup):
    """Simulate provider timeout (load_candles failure)."""
    btc = Asset(symbol="BTC_TO", name="Bitcoin Timeout", asset_type="CRYPTO", market_id=scanner_setup["crypto_m"].id)
    eth = Asset(symbol="ETH_OK", name="Ethereum OK", asset_type="CRYPTO", market_id=scanner_setup["crypto_m"].id)
    db_session.add_all([btc, eth])
    db_session.flush()
    db_session.add(ProviderInstrument(asset_id=btc.id, provider_id=scanner_setup["bybit"].id, provider_symbol="BTCUSDT"))
    db_session.add(ProviderInstrument(asset_id=eth.id, provider_id=scanner_setup["bybit"].id, provider_symbol="ETHUSDT"))
    
    create_candles(db_session, eth.id, scanner_setup["bybit"].id)
    db_session.commit()
    
    import app.engines.scanner.service as scanner_service
    original_load = scanner_service.load_candles
    
    def mock_load(session, asset_id, timeframe, provider_id=None):
        if asset_id == btc.id:
            raise ValueError("Timeout")
        return original_load(session, asset_id, timeframe, provider_id)
        
    with patch("app.engines.runner.load_candles", side_effect=mock_load):
        run = run_scanner(db_session, timeframe="1h")
    
    assert eth.symbol in [db_session.get(Asset, r.asset_id).symbol for r in db_session.query(ScannerResult).filter_by(scanner_run_id=run.id).all()]
    skipped = [s["symbol"] for s in run.execution_metadata["skipped"]]
    assert "BTC_TO" in skipped

def test_scanner_stale_data(db_session, scanner_setup):
    """Test freshness_status = STALE for old data."""
    stale = Asset(symbol="STALE", name="Stale Asset", asset_type="CRYPTO", market_id=scanner_setup["crypto_m"].id)
    db_session.add(stale)
    db_session.flush()
    db_session.add(ProviderInstrument(asset_id=stale.id, provider_id=scanner_setup["bybit"].id, provider_symbol="STALEUSDT"))
    
    # 24 hours old data
    create_candles(db_session, stale.id, scanner_setup["bybit"].id, stale_hours=24)
    db_session.commit()
    
    run = run_scanner(db_session, timeframe="1h")
    res = db_session.query(ScannerResult).filter_by(scanner_run_id=run.id, asset_id=stale.id).one()
    assert res.freshness_status == "STALE"

def test_scanner_currency_mismatch(db_session, scanner_setup):
    """Test mismatch between candle currency and asset quote_currency (should not crash)."""
    mismatch = Asset(symbol="MISMATCH", name="Mismatch", asset_type="CRYPTO", market_id=scanner_setup["crypto_m"].id, quote_currency="USD")
    db_session.add(mismatch)
    db_session.flush()
    db_session.add(ProviderInstrument(asset_id=mismatch.id, provider_id=scanner_setup["bybit"].id, provider_symbol="MISMATCHUSDT"))
    
    # Candle in EUR
    create_candles(db_session, mismatch.id, scanner_setup["bybit"].id, currency="EUR")
    db_session.commit()
    
    run = run_scanner(db_session, timeframe="1h")
    assert run.result_count == 1
    res = db_session.query(ScannerResult).filter_by(scanner_run_id=run.id, asset_id=mismatch.id).one()
    assert res.result_status == "COMPLETED"

def test_scanner_provider_isolation(db_session, scanner_setup):
    """One series = one provider, no mixing."""
    with patch("app.engines.scanner.service.get_settings") as mock_settings:
        mock_settings.return_value.crypto_provider = "BYBIT"
        iso = Asset(symbol="ISO", name="Isolated", asset_type="CRYPTO", market_id=scanner_setup["crypto_m"].id)
        db_session.add(iso)
        db_session.flush()
        db_session.add(ProviderInstrument(asset_id=iso.id, provider_id=scanner_setup["bybit"].id, provider_symbol="ISOUSDT"))
        db_session.add(ProviderInstrument(asset_id=iso.id, provider_id=scanner_setup["yahoo"].id, provider_symbol="ISO-USD"))
        
        # Candles in both
        create_candles(db_session, iso.id, scanner_setup["bybit"].id, base_price=100)
        create_candles(db_session, iso.id, scanner_setup["yahoo"].id, base_price=500)
        db_session.commit()
        
        # Bybit is default for CRYPTO
        run = run_scanner(db_session, timeframe="1h")
        res = db_session.query(ScannerResult).filter_by(scanner_run_id=run.id, asset_id=iso.id).one()
        assert res.metric_snapshot["last_close"] == 164.0
