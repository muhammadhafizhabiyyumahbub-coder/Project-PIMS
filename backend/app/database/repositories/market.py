"Market data repositories (quotes and FX rates)."
import uuid
from datetime import datetime, UTC
from decimal import Decimal

from sqlalchemy import select
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
