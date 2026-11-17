"Idempotent seeding of the development market universe (Bybit spot, small set)."
from sqlalchemy.orm import Session

from app.database.models import Asset, DataProvider, Market, ProviderInstrument

BYBIT_UNIVERSE = [
    # (symbol, name, base, quote, yahoo_symbol)
    ("BTCUSDT", "Bitcoin", "BTC", "USDT", "BTC-USD"),
    ("ETHUSDT", "Ethereum", "ETH", "USDT", "ETH-USD"),
    ("SOLUSDT", "Solana", "SOL", "USDT", "SOL-USD"),
]


def ensure_universe(session: Session) -> dict:
    """Create provider/market/asset rows once; returns ids used by ingestion."""
    provider = session.query(DataProvider).filter_by(code="BYBIT").one_or_none()
    if provider is None:
        provider = DataProvider(code="BYBIT", name="Bybit", provider_type="CRYPTO_EXCHANGE")
        session.add(provider)

    yahoo = session.query(DataProvider).filter_by(code="YAHOO").one_or_none()
    if yahoo is None:
        yahoo = DataProvider(code="YAHOO", name="Yahoo Finance", provider_type="DATA_AGGREGATOR")
        session.add(yahoo)

    market = session.query(Market).filter_by(code="CRYPTO").one_or_none()
    if market is None:
        market = Market(code="CRYPTO", name="Cryptocurrency", market_type="CRYPTO")
        session.add(market)

    session.flush()

    assets: dict[str, Asset] = {}
    for symbol, name, base, quote, yahoo_symbol in BYBIT_UNIVERSE:
        asset = session.query(Asset).filter_by(symbol=symbol, asset_type="CRYPTO").one_or_none()
        if asset is None:
            asset = Asset(
                symbol=symbol,
                name=name,
                asset_type="CRYPTO",
                market_id=market.id,
                base_currency=base,
                quote_currency=quote,
            )
            session.add(asset)
            session.flush()
        for provider_obj, provider_symbol, feed in (
            (provider, symbol, "REST_PUBLIC"),
            (yahoo, yahoo_symbol, "REST_PUBLIC"),
        ):
            instrument = (
                session.query(ProviderInstrument)
                .filter_by(provider_id=provider_obj.id, provider_symbol=provider_symbol)
                .one_or_none()
            )
            if instrument is None:
                session.add(
                    ProviderInstrument(
                        asset_id=asset.id,
                        provider_id=provider_obj.id,
                        provider_symbol=provider_symbol,
                        feed_type=feed,
                    )
                )
        assets[symbol] = asset

    session.commit()
    return {"provider": provider, "providers": [provider, yahoo], "market": market, "assets": assets}
