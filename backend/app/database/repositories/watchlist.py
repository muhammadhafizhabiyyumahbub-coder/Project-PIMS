"""Watchlist repositories (api-spec §17).

Persistence only; validation and HTTP concerns live in the API layer.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database.models import Asset, Watchlist, WatchlistItem
from app.database.models.core import utc_now


def list_watchlists(session: Session) -> list[Watchlist]:
    return list(
        session.scalars(
            select(Watchlist)
            .options(joinedload(Watchlist.items))
            .order_by(Watchlist.created_at, Watchlist.id)
        ).unique()
    )


def create_watchlist(
    session: Session, name: str, description: str | None = None
) -> Watchlist:
    watchlist = Watchlist(name=name, description=description)
    session.add(watchlist)
    session.flush()
    return watchlist


def get_watchlist(session: Session, watchlist_id: uuid.UUID) -> Watchlist | None:
    return session.get(Watchlist, watchlist_id)


def get_watchlist_with_items(
    session: Session, watchlist_id: uuid.UUID
) -> Watchlist | None:
    return session.scalars(
        select(Watchlist)
        .options(joinedload(Watchlist.items).joinedload(WatchlistItem.asset))
        .where(Watchlist.id == watchlist_id)
    ).unique().first()


def update_watchlist(
    session: Session, watchlist: Watchlist, **values
) -> Watchlist:
    for field, value in values.items():
        if value is not None:
            setattr(watchlist, field, value)
    watchlist.updated_at = utc_now()
    session.flush()
    return watchlist


def delete_watchlist(session: Session, watchlist: Watchlist) -> None:
    session.delete(watchlist)
    session.flush()


def get_asset(session: Session, asset_id: uuid.UUID) -> Asset | None:
    return session.get(Asset, asset_id)


def get_item(
    session: Session, watchlist_id: uuid.UUID, asset_id: uuid.UUID
) -> WatchlistItem | None:
    return session.scalars(
        select(WatchlistItem).where(
            WatchlistItem.watchlist_id == watchlist_id,
            WatchlistItem.asset_id == asset_id,
        )
    ).first()


def add_item(
    session: Session, watchlist_id: uuid.UUID, asset_id: uuid.UUID
) -> WatchlistItem:
    item = WatchlistItem(watchlist_id=watchlist_id, asset_id=asset_id)
    session.add(item)
    session.flush()
    return item


def remove_item(
    session: Session, watchlist_id: uuid.UUID, asset_id: uuid.UUID
) -> bool:
    item = get_item(session, watchlist_id, asset_id)
    if item is None:
        return False
    session.delete(item)
    session.flush()
    return True
