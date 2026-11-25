import pytest
import os
import httpx
from datetime import datetime, UTC
from sqlalchemy.orm import Session
from app.data.providers.crypto.yahoo import YahooProvider
from app.database.models import MarketCandle, Asset, DataProvider, ProviderInstrument

# Set this env var to run this test
# PIMS_REAL_PROVIDER=1 pytest tests/test_real_integration.py

@pytest.mark.skipif(os.getenv("PIMS_REAL_PROVIDER") != "1", reason="Real provider integration disabled")
def test_real_yahoo_integration(db_session: Session):
    """Real network call to Yahoo Finance for BTC-USD and BBCA.JK."""
    # Use ensure_universe to have providers and assets
    from app.data.storage.universe import ensure_universe
    ensure_universe(db_session)
    provider = db_session.query(DataProvider).filter_by(code="YAHOO").first()
    assert provider is not None
    
    # We use YahooProvider directly, not the storage-ingestion layer, 
    # to avoid persistent database clutter unless desired.
    yahoo = YahooProvider(base_url="https://query1.finance.yahoo.com")
    
    # Test BTC-USD
    res_btc, curr_btc = yahoo.fetch_klines_with_meta("BTC-USD", "1h", limit=100)
    assert len(res_btc) > 0
    assert curr_btc == "USD"
    print(f"\nBTC-USD currency: {curr_btc}, count: {len(res_btc)}")

    # Test BBCA.JK
    res_bbca, curr_bbca = yahoo.fetch_klines_with_meta("BBCA.JK", "1h", limit=100)
    assert len(res_bbca) > 0
    assert curr_bbca == "IDR"
    print(f"BBCA.JK currency: {curr_bbca}, count: {len(res_bbca)}")
