"""Asset repositories (schema-spec §4.1 core domain).

Read-only helpers for the Asset API; identity is always the internal Asset row.
Provider symbol mappings live in provider_instruments and never surface here.
"""
import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database.models import Asset, Market


def get_assets(session: Session, asset_ids: list[uuid.UUID]) -> list[Asset]:
    """Batch asset lookup."""
    return list(session.scalars(select(Asset).where(Asset.id.in_(asset_ids))).all())


def get_asset_with_market(
    session: Session, asset_id: uuid.UUID
) -> tuple[Asset, str | None] | None:
    row = session.execute(
        select(Asset, Market.code)
        .outerjoin(Market, Asset.market_id == Market.id)
        .where(Asset.id == asset_id)
    ).first()
    return (row[0], row[1]) if row is not None else None


def search_assets(
    session: Session,
    *,
    query: str | None = None,
    market: str | None = None,
    exchange: str | None = None,
    asset_type: str | None = None,
    limit: int = 50,
    cursor_asset: Asset | None = None,
) -> tuple[list[tuple[Asset, str | None]], bool]:
    """Deterministic (symbol, id) ordering; returns (asset, market_code) rows.

    Only active assets are listed. `market` and `exchange` both filter on the
    markets.code column joined via assets.market_id.
    """
    stmt = (
        select(Asset, Market.code)
        .outerjoin(Market, Asset.market_id == Market.id)
        .where(Asset.is_active.is_(True))
    )
    if query:
        like = f"%{query}%"
        stmt = stmt.where(or_(Asset.symbol.ilike(like), Asset.name.ilike(like)))
    if market is not None:
        stmt = stmt.where(Market.code == market)
    if exchange is not None:
        stmt = stmt.where(Market.code == exchange)
    if asset_type is not None:
        stmt = stmt.where(Asset.asset_type == asset_type)
    if cursor_asset is not None:
        stmt = stmt.where(
            (Asset.symbol, Asset.id) > (cursor_asset.symbol, cursor_asset.id)
        )
    stmt = stmt.order_by(Asset.symbol, Asset.id).limit(limit + 1)
    rows = list(session.execute(stmt).all())
    has_more = len(rows) > limit
    return rows[:limit], has_more
