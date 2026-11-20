"Quote and FX rates ingestion service."
import uuid
import sys
import json
from datetime import datetime, UTC
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.db import get_session_factory
from app.database.models import Asset, DataProvider
from app.database.repositories.market import upsert_quote, upsert_fx_rate
from app.data.providers.crypto.yahoo import YahooProvider
from app.data.validation.freshness import freshness_status


def ingest_quotes(
    session: Session,
    asset_ids: list[uuid.UUID] | None = None,
    provider_code: str | None = None,
) -> dict:
    code = provider_code or "YAHOO"
    provider = session.query(DataProvider).filter_by(code=code).first()
    if not provider:
        provider = DataProvider(code=code, name="Yahoo Finance", provider_type="CRYPTO")
        session.add(provider)
        session.commit()

    query = session.query(Asset).filter_by(is_active=True, asset_type="CRYPTO")
    if asset_ids:
        query = query.filter(Asset.id.in_(asset_ids))
    assets = query.all()
    print(f"DEBUG: Found {len(assets)} assets")

    requested = len(assets)
    written = 0
    skipped = 0
    failed = []

    yahoo = YahooProvider()

    for asset in assets:
        print(f"DEBUG: Processing asset {asset.symbol}")
        try:
            klines = yahoo.fetch_klines(asset.symbol, "1h", limit=1)
            print(f"DEBUG: Fetched {len(klines)} klines for {asset.symbol}")
            if not klines:
                failed.append({"asset_id": str(asset.id), "symbol": asset.symbol, "reason": "empty payload"})
                continue
            latest = klines[-1]
            price = Decimal(str(latest.close_price))
            print(f"DEBUG: Price={price}, source_ts={latest.close_time}, is_realtime=False")
            if price <= 0:
                failed.append({"asset_id": str(asset.id), "symbol": asset.symbol, "reason": "invalid price"})
                continue
            
            source_ts = latest.close_time
            now = datetime.now(UTC)
            feed_stat = freshness_status(source_ts, now, "1h")

            upsert_quote(
                session,
                asset_id=asset.id,
                provider_id=provider.id,
                price=price,
                currency=asset.quote_currency or "USD",
                source_timestamp=source_ts,
                received_at=now,
                is_realtime=False,
                feed_status=feed_stat,
            )
            written += 1
        except Exception as e:
            print(f"DEBUG: Exception caught: {e}")
            import traceback
            traceback.print_exc()
            failed.append({"asset_id": str(asset.id), "symbol": asset.symbol, "reason": str(e)})

    session.commit()
    return {
        "requested": requested,
        "written": written,
        "skipped": skipped,
        "failed": failed,
        "provider": code,
        "is_realtime": False,
    }


def ingest_fx_rates(
    session: Session,
    pairs: list[tuple[str, str]] = [("USD", "IDR")],
    provider_code: str | None = None,
) -> dict:
    code = provider_code or "YAHOO"
    provider = session.query(DataProvider).filter_by(code=code).first()
    if not provider:
        provider = DataProvider(code=code, name="Yahoo Finance", provider_type="FX")
        session.add(provider)
        session.commit()

    requested = len(pairs)
    written = 0
    skipped = 0
    failed = []

    yahoo = YahooProvider()

    for base, quote in pairs:
        # Yahoo symbol for USD/IDR is USDIDR=X
        symbol = f"{base}{quote}=X"
        try:
            klines = yahoo.fetch_klines(symbol, "1h", limit=1)
            if not klines:
                failed.append({"pair": f"{base}/{quote}", "reason": "empty payload"})
                continue
            latest = klines[-1]
            rate = Decimal(str(latest.close_price))
            if rate <= 0:
                failed.append({"pair": f"{base}/{quote}", "reason": "invalid rate <= 0"})
                continue

            source_ts = latest.close_time
            now = datetime.now(UTC)
            feed_stat = freshness_status(source_ts, now, "1h")

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
        except Exception as e:
            # Check inverse or skip if not found
            if "IDRUSD" in symbol or "404" in str(e):
                skipped += 1
            else:
                failed.append({"pair": f"{base}/{quote}", "reason": str(e)})

    return {
        "requested": requested,
        "written": written,
        "skipped": skipped,
        "failed": failed,
        "provider": code,
    }


if __name__ == "__main__":
    session_factory = get_session_factory()
    with session_factory() as session:
        quotes_res = ingest_quotes(session)
        fx_res = ingest_fx_rates(session)
        print(json.dumps({"quotes": quotes_res, "fx": fx_res}, default=str))
