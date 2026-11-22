"Quote and FX rates ingestion service."
import uuid
import logging
import json
from datetime import datetime, UTC
from decimal import Decimal

from httpx import HTTPStatusError
from sqlalchemy.orm import Session
from httpx import HTTPStatusError

from app.core.db import get_session_factory
from app.database.models import Asset, DataProvider, ProviderInstrument
from app.database.repositories.market import upsert_quote, upsert_fx_rate
from app.data.providers.crypto.yahoo import YahooProvider
from app.data.validation.freshness import freshness_status

logger = logging.getLogger(__name__)


def ingest_quotes(
    session: Session,
    asset_ids: list[uuid.UUID] | None = None,
    provider_code: str | None = None,
    feed_timeframe: str = "1h",
    markets: str | None = None,
) -> dict:
    code = provider_code or "YAHOO"
    provider = session.query(DataProvider).filter_by(code=code).first()
    if not provider:
        provider = DataProvider(code=code, name="Yahoo Finance", provider_type="CRYPTO")
        session.add(provider)
        session.commit()

    query = (
        session.query(Asset, ProviderInstrument)
        .join(ProviderInstrument, Asset.id == ProviderInstrument.asset_id)
        .filter(
            Asset.is_active == True,
            ProviderInstrument.provider_id == provider.id,
            ProviderInstrument.is_active == True,
        )
    )
    if markets:
        market_list = [m.strip() for m in markets.split(",")]
        query = query.filter(Asset.market.in_(market_list))
    
    if asset_ids:
        query = query.filter(Asset.id.in_(asset_ids))
    results = query.all()

    # Also identify skipped ones
    asset_query = session.query(Asset).filter_by(is_active=True)
    if markets:
        asset_query = asset_query.filter(Asset.market.in_([m.strip() for m in markets.split(",")]))
    all_active_assets = asset_query.all()
    
    requested_ids = {a.id for a in all_active_assets}
    processed_ids = {a.id for a, pi in results}
    
    skipped_count = 0
    skipped_reasons: list = []
    for asset in all_active_assets:
        if asset.id not in processed_ids:
            skipped_count += 1
            skipped_reasons.append({"asset_id": str(asset.id), "symbol": asset.symbol, "reason": f"no provider instrument mapping for {asset.symbol}"})

    written = 0
    failed = []

    yahoo = YahooProvider()

    for asset, pi in results:
        try:
            klines, currency = yahoo.fetch_klines_with_meta(pi.provider_symbol, feed_timeframe, limit=1)
            if not klines:
                skipped_count += 1
                skipped_reasons.append(
                    {
                        "asset_id": str(asset.id),
                        "symbol": asset.symbol,
                        "reason": f"provider returned no data for {pi.provider_symbol}",
                    }
                )
                continue
            latest = klines[-1]
            price = Decimal(str(latest.close_price))
            if price <= 0:
                failed.append({"asset_id": str(asset.id), "symbol": asset.symbol, "reason": "invalid price"})
                continue
            
            source_ts = latest.close_time
            now = datetime.now(UTC)
            feed_stat = freshness_status(source_ts, now, feed_timeframe)

            # NOTE: Currency sourced from provider metadata, fallback to asset.quote_currency
            final_currency = currency or asset.quote_currency or "USD"

            upsert_quote(
                session,
                asset_id=asset.id,
                provider_id=provider.id,
                price=price,
                currency=final_currency,
                source_timestamp=source_ts,
                received_at=now,
                feed_status=feed_stat,
            )
            written += 1
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                skipped_count += 1
                skipped_reasons.append(
                    {
                        "asset_id": str(asset.id),
                        "symbol": asset.symbol,
                        "reason": f"provider does not offer {pi.provider_symbol}",
                    }
                )
            else:
                logger.error(f"Provider error for {asset.symbol}: {e}")
                failed.append({"asset_id": str(asset.id), "symbol": asset.symbol, "reason": str(e)})
        except (ValueError, RuntimeError) as e:
            failed.append({"asset_id": str(asset.id), "symbol": asset.symbol, "reason": str(e)})
        except Exception as e:
            logger.exception(f"Unexpected error for {asset.symbol}")
            failed.append({"asset_id": str(asset.id), "symbol": asset.symbol, "reason": str(e)})

    session.commit()
    return {
        "requested": len(all_active_assets),
        "written": written,
        "skipped": skipped_count,
        "skipped_reasons": skipped_reasons,
        "failed": failed,
        "provider": code,
        "is_realtime": False,
    }


def ingest_fx_rates(
    session: Session,
    pairs: list[tuple[str, str]] = [("USD", "IDR")],
    provider_code: str | None = None,
    feed_timeframe: str = "1h",
) -> dict:
    code = provider_code or "YAHOO"
    provider = session.query(DataProvider).filter_by(code=code).first()
    if not provider:
        provider = DataProvider(code=code, name="Yahoo Finance", provider_type="FX")
        session.add(provider)
        session.commit()

    requested = len(pairs)
    written = 0
    skipped_count = 0
    skipped_reasons: list = []
    failed = []

    yahoo = YahooProvider()

    for base, quote in pairs:
        # Yahoo symbol for USD/IDR is USDIDR=X
        symbol = f"{base}{quote}=X"
        try:
            klines, currency = yahoo.fetch_klines_with_meta(symbol, feed_timeframe, limit=1)
            if not klines:
                skipped_count += 1
                skipped_reasons.append(
                    {
                        "pair": f"{base}/{quote}",
                        "reason": f"provider returned no data for {base}/{quote}",
                    }
                )
                continue
            
            latest = klines[-1]
            rate = Decimal(str(latest.close_price))
            if rate <= 0:
                failed.append({"pair": f"{base}/{quote}", "reason": "invalid rate <= 0"})
                continue

            source_ts = latest.close_time
            now = datetime.now(UTC)
            feed_stat = freshness_status(source_ts, now, feed_timeframe)

            upsert_fx_rate(
                session,
                base_currency=base,
                quote_currency=quote,
                rate=rate,
                provider_id=provider.id,
                source_timestamp=source_ts,
                freshness_status=feed_stat,
            )
            written += 1
        except HTTPStatusError as e:
            if e.response.status_code == 404:
                skipped_count += 1
                skipped_reasons.append(
                    {
                        "pair": f"{base}/{quote}",
                        "reason": f"provider does not offer {base}/{quote} direction",
                    }
                )
            else:
                logger.error(f"Provider error for {base}/{quote}: {e}")
                failed.append({"pair": f"{base}/{quote}", "reason": str(e)})
        except Exception as e:
            logger.exception(f"Unexpected error for {base}/{quote}")
            failed.append({"pair": f"{base}/{quote}", "reason": str(e)})

    session.commit()
    return {
        "requested": requested,
        "written": written,
        "skipped": skipped_count,
        "skipped_reasons": skipped_reasons,
        "failed": failed,
        "provider": code,
    }


if __name__ == "__main__":
    session_factory = get_session_factory()
    with session_factory() as session:
        quotes_res = ingest_quotes(session)
        fx_res = ingest_fx_rates(session)
        print(json.dumps({"quotes": quotes_res, "fx": fx_res}, default=str))
