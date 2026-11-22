"Candle persistence (upsert on unique candle identity)."
from datetime import datetime, timezone

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.database.models import MarketCandle


def upsert_candles(
    session: Session,
    asset_id,
    provider_id,
    timeframe: str,
    normalized: list[dict],
    currency: str,
    feed_type: str | None,
    source_timestamp: datetime | None = None,
) -> int:
    """Insert or update candles; returns number of rows written."""
    received_at = datetime.now(timezone.utc)
    written = 0
    for candle in normalized:
        stmt = insert(MarketCandle).values(
            asset_id=asset_id,
            provider_id=provider_id,
            feed_type=feed_type,
            timeframe=timeframe,
            currency=currency,
            source_timestamp=source_timestamp,
            received_at=received_at,
            **candle,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_candle_identity",
            set_={
                "high_price": stmt.excluded.high_price,
                "low_price": stmt.excluded.low_price,
                "close_price": stmt.excluded.close_price,
                "volume": stmt.excluded.volume,
                "quote_volume": stmt.excluded.quote_volume,
                "close_time": stmt.excluded.close_time,
                "candle_status": stmt.excluded.candle_status,
                # Keep provenance correct on re-ingest: an IDX candle mislabelled USD
                # must be fixable by refreshing, not only by deleting rows.
                "currency": stmt.excluded.currency,
                "feed_type": stmt.excluded.feed_type,
                "received_at": received_at,
            },
        )
        session.execute(stmt)
        written += 1
    session.commit()
    return written
