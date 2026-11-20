"Market data repositories (quotes and FX rates)."
import uuid
from datetime import datetime, UTC
from decimal import Decimal

from sqlalchemy import select, Boolean
from sqlalchemy.orm import Session

from app.database.models import MarketQuote, FXRate


def list_quotes(
    session: Session,
    *,
    asset_id: uuid.UUID | None = None,
    provider_id: uuid.UUID | None = None,
    limit: int = 50,
    cursor_quote: MarketQuote | None = None,
) -> tuple[list[MarketQuote], bool]:
    stmt = select(MarketQuote)
    if asset_id is not None:
        stmt = stmt.where(MarketQuote.asset_id == asset_id)
    if provider_id is not None:
        stmt = stmt.where(MarketQuote.provider_id == provider_id)
    if cursor_quote is not None:
        stmt = stmt.where(
            (MarketQuote.received_at, MarketQuote.id)
            < (cursor_quote.received_at, cursor_quote.id)
        )
    stmt = stmt.order_by(MarketQuote.received_at.desc(), MarketQuote.id.desc()).limit(limit + 1)
    rows = list(session.scalars(stmt))
    has_more = len(rows) > limit
    return rows[:limit], has_more


def get_latest_quote_for_asset(session: Session, asset_id: uuid.UUID) -> MarketQuote | None:
    return session.scalars(
        select(MarketQuote)
        .where(MarketQuote.asset_id == asset_id)
        .order_by(MarketQuote.received_at.desc(), MarketQuote.id.desc())
    ).first()


def get_fx_rate(
    session: Session, base_currency: str, quote_currency: str
) -> FXRate | None:
    return session.scalars(
        select(FXRate)
        .where(
            FXRate.base_currency == base_currency,
            FXRate.quote_currency == quote_currency,
        )
        .order_by(FXRate.source_timestamp.desc(), FXRate.id.desc())
    ).first()


def upsert_quote(
    session: Session,
    *,
    asset_id: uuid.UUID,
    provider_id: uuid.UUID,
    price: Decimal,
    currency: str,
    source_timestamp: datetime,
    received_at: datetime,
    is_realtime: bool,
    feed_status: str,
) -> MarketQuote:
    # Check idempotency by asset_id, provider_id, and source_timestamp
    existing = session.scalars(
        select(MarketQuote).where(
            MarketQuote.asset_id == asset_id,
            MarketQuote.provider_id == provider_id,
            MarketQuote.source_timestamp == source_timestamp,
        )
    ).first()
    if existing:
        return existing

    quote = MarketQuote(
        asset_id=asset_id,
        provider_id=provider_id,
        last_price=price,
        currency=currency,
        source_timestamp=source_timestamp,
        received_at=received_at,
        is_realtime=is_realtime,
        feed_status=feed_status,
        freshness_status=feed_status,
    )
    session.add(quote)
    session.flush()
    session.refresh(quote)
    return quote


def upsert_fx_rate(
    session: Session,
    *,
    base_currency: str,
    quote_currency: str,
    rate: Decimal,
    provider_id: uuid.UUID,
    source_timestamp: datetime,
    freshness_status: str,
) -> FXRate:
    existing = session.scalars(
        select(FXRate).where(
            FXRate.base_currency == base_currency,
            FXRate.quote_currency == quote_currency,
            FXRate.source_timestamp == source_timestamp,
        )
    ).first()
    if existing:
        return existing

    fx = FXRate(
        base_currency=base_currency,
        quote_currency=quote_currency,
        rate=rate,
        provider_id=provider_id,
        source_timestamp=source_timestamp,
        freshness_status=freshness_status,
    )
    session.add(fx)
    session.flush()
    session.refresh(fx)
    return fx

