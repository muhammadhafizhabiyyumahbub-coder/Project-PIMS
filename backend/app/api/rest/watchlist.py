"""Watchlist REST endpoints per api-spec §17.

Handlers validate input and orchestrate the repository only; membership never
touches portfolio holdings (api-spec §17.2).
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.envelope import error_response, success_response
from app.core.db import get_db
from app.database.repositories import watchlist as repo
from app.schemas.watchlist import WatchlistCreate, WatchlistItemAdd, WatchlistUpdate

router = APIRouter(prefix="/watchlists", tags=["Watchlists"])


def parse_uuid(value: str):
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


def _watchlist_payload(watchlist) -> dict:
    return {
        "id": str(watchlist.id),
        "name": watchlist.name,
        "description": watchlist.description,
        "created_at": watchlist.created_at.isoformat(),
        "updated_at": watchlist.updated_at.isoformat(),
        "item_count": len(watchlist.items),
    }


def _item_payload(item) -> dict:
    return {
        "asset_id": str(item.asset_id),
        "symbol": item.asset.symbol if item.asset else None,
        "name": item.asset.name if item.asset else None,
        "added_at": item.added_at.isoformat(),
    }


@router.get("")
def list_watchlists(db: Session = Depends(get_db)):
    watchlists = repo.list_watchlists(db)
    return success_response(
        [_watchlist_payload(w) for w in watchlists], meta={"count": len(watchlists)}
    )


@router.post("", status_code=201)
def create_watchlist(body: WatchlistCreate, db: Session = Depends(get_db)):
    watchlist = repo.create_watchlist(db, name=body.name, description=body.description)
    db.commit()
    return success_response(_watchlist_payload(watchlist), status_code=201)


@router.get("/{watchlist_id}")
def get_watchlist_detail(watchlist_id: str, db: Session = Depends(get_db)):
    wid = parse_uuid(watchlist_id)
    watchlist = (
        repo.get_watchlist_with_items(db, wid) if wid is not None else None
    )
    if watchlist is None:
        return error_response("NOT_FOUND", f"watchlist {watchlist_id} not found", 404)
    payload = _watchlist_payload(watchlist)
    payload["items"] = [_item_payload(i) for i in watchlist.items]
    return success_response(payload)


@router.patch("/{watchlist_id}")
def update_watchlist(
    watchlist_id: str, body: WatchlistUpdate, db: Session = Depends(get_db)
):
    wid = parse_uuid(watchlist_id)
    watchlist = repo.get_watchlist(db, wid) if wid is not None else None
    if watchlist is None:
        return error_response("NOT_FOUND", f"watchlist {watchlist_id} not found", 404)
    repo.update_watchlist(db, watchlist, name=body.name, description=body.description)
    db.commit()
    return success_response(_watchlist_payload(watchlist))


@router.delete("/{watchlist_id}")
def delete_watchlist(watchlist_id: str, db: Session = Depends(get_db)):
    wid = parse_uuid(watchlist_id)
    watchlist = repo.get_watchlist(db, wid) if wid is not None else None
    if watchlist is None:
        return error_response("NOT_FOUND", f"watchlist {watchlist_id} not found", 404)
    repo.delete_watchlist(db, watchlist)
    db.commit()
    return success_response({"deleted": True, "id": str(wid)})


@router.post("/{watchlist_id}/items", status_code=201)
def add_watchlist_item(
    watchlist_id: str, body: WatchlistItemAdd, db: Session = Depends(get_db)
):
    wid = parse_uuid(watchlist_id)
    watchlist = repo.get_watchlist(db, wid) if wid is not None else None
    if watchlist is None:
        return error_response("NOT_FOUND", f"watchlist {watchlist_id} not found", 404)
    asset_id = parse_uuid(body.asset_id)
    if asset_id is None or repo.get_asset(db, asset_id) is None:
        return error_response("NOT_FOUND", f"asset {body.asset_id} not found", 404)
    if repo.get_item(db, wid, asset_id) is not None:
        return error_response(
            "CONFLICT", "asset already in watchlist", 409
        )
    item = repo.add_item(db, wid, asset_id)
    db.commit()
    return success_response(_item_payload(item), status_code=201)


@router.delete("/{watchlist_id}/items/{asset_id}")
def remove_watchlist_item(
    watchlist_id: str, asset_id: str, db: Session = Depends(get_db)
):
    wid = parse_uuid(watchlist_id)
    if wid is None or repo.get_watchlist(db, wid) is None:
        return error_response("NOT_FOUND", f"watchlist {watchlist_id} not found", 404)
    aid = parse_uuid(asset_id)
    if aid is None or not repo.remove_item(db, wid, aid):
        return error_response(
            "NOT_FOUND", f"asset {asset_id} not in watchlist", 404
        )
    db.commit()
    return success_response({"removed": True, "asset_id": str(aid)})
