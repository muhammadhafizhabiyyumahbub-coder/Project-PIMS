"Fetch candles from a provider adapter and persist normalized rows."
from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.data.normalization.normalize import normalize_kline
from app.data.providers.base import MarketDataProvider
from app.data.providers.crypto.bybit import BybitProvider
from app.data.providers.crypto.yahoo import YahooProvider
from app.data.storage.candles import upsert_candles
from app.database.models import Asset, DataProvider, ProviderInstrument

ADAPTERS = {"BYBIT": BybitProvider, "YAHOO": YahooProvider}


def resolve_provider(session: Session) -> tuple[DataProvider, MarketDataProvider]:
    """Pick the configured crypto provider and its adapter."""
    code = get_settings().crypto_provider.upper()
    if code not in ADAPTERS:
        raise ValueError(f"Unknown PIMS_CRYPTO_PROVIDER: {code}")
    provider = session.query(DataProvider).filter_by(code=code).one()
    if code == "BYBIT":
        return provider, BybitProvider()
    return provider, YahooProvider()


def refresh_asset_candles(session: Session, asset: Asset, timeframe: str, limit: int = 300) -> int:
    """Fetch klines for one asset through the adapter pipeline and upsert them."""
    provider = (
        session.query(DataProvider).filter_by(code=get_settings().crypto_provider.upper()).one()
    )
    instrument = (
        session.query(ProviderInstrument)
        .filter_by(asset_id=asset.id, provider_id=provider.id, is_active=True)
        .one()
    )
    _, adapter = resolve_provider(session)
    raw = adapter.fetch_klines(instrument.provider_symbol, timeframe, limit)
    normalized = [normalize_kline(k) for k in raw]
    # Yahoo candles are USD-denominated; provider carries provenance for this.
    currency = getattr(adapter, "currency", None) or asset.quote_currency or "USDT"
    return upsert_candles(
        session,
        asset_id=asset.id,
        provider_id=provider.id,
        timeframe=timeframe,
        normalized=normalized,
        currency=currency,
        feed_type=adapter.feed_type,
        source_timestamp=normalized[-1]["close_time"] if normalized else None,
    )
