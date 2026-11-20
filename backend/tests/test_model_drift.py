import pytest
from app.database.models import MarketQuote, FXRate
from sqlalchemy import inspect

def test_market_models_columns_count():
    # MarketQuote: §6.1 specifies 13 columns
    # id, asset_id, provider_id, provider_instrument_id, feed_type, bid_price, ask_price, last_price, currency, source_timestamp, received_at, freshness_status, metadata
    mapper = inspect(MarketQuote)
    assert len(mapper.columns) == 13, f"MarketQuote columns mismatch, found: {mapper.columns.keys()}"

    # FXRate: §6.2 specifies 8 columns
    # id, base_currency, quote_currency, rate, provider_id, source_timestamp, received_at, freshness_status
    mapper_fx = inspect(FXRate)
    assert len(mapper_fx.columns) == 8, f"FXRate columns mismatch, found: {mapper_fx.columns.keys()}"
