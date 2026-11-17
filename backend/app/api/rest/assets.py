"""Asset REST endpoints per api-spec §11 (read-only instrument metadata).

Asset identity is internal (assets.symbol, schema-spec §4.1); provider-specific
symbol mappings stay in provider_instruments and are never used or exposed here.

`exchange` is the code of the market linked via assets.market_id (markets.code);
it is null only for assets without a market_id (Project Owner decision §7.7).
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.envelope import error_response, success_response
from app.core.db import get_db
from app.database.models import Asset
from app.database.repositories import asset as repo

router = APIRouter(prefix="/assets", tags=["Assets"])


def parse_uuid(value: str):
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


def _asset_payload(asset: Asset, market_code: str | None) -> dict:
    return {
        "id": str(asset.id),
        "symbol": asset.symbol,
        "name": asset.name,
        "market": market_code,
        "exchange": market_code,  # venue = markets.code until a venue entity exists (§7.7)
        "quote_currency": asset.quote_currency,
        "asset_type": asset.asset_type,
        "base_currency": asset.base_currency,
    }


def _run_search(
    db: Session,
    query: str | None,
    market: str | None,
    exchange: str | None,
    asset_type: str | None,
    limit: int,
    cursor: str | None,
):
    if limit < 1 or limit > 200:
        return error_response("VALIDATION_ERROR", "limit must be between 1 and 200", 422)
    cursor_asset = None
    if cursor:
        cursor_id = parse_uuid(cursor)
        if cursor_id is None:
            return error_response("VALIDATION_ERROR", "invalid cursor", 422)
        cursor_asset = repo.get_asset(db, cursor_id)
        if cursor_asset is None:
            return error_response("VALIDATION_ERROR", "invalid cursor", 422)
    rows, has_more = repo.search_assets(
        db,
        query=query,
        market=market,
        exchange=exchange,
        asset_type=asset_type,
        limit=limit,
        cursor_asset=cursor_asset,
    )
    return success_response(
        [_asset_payload(asset, market_code) for asset, market_code in rows],
        meta={
            "count": len(rows),
            "pagination": {
                "limit": limit,
                "next_cursor": str(rows[-1][0].id) if has_more and rows else None,
                "has_more": has_more,
            },
        },
    )


# /assets/search MUST be declared before /assets/{asset_id} so "search" is
# never matched as an id (api-spec §11.1; proven by test).
@router.get("/search")
def search_assets(
    query: str | None = None,
    market: str | None = None,
    exchange: str | None = None,
    asset_type: str | None = None,
    limit: int = Query(default=50),
    cursor: str | None = None,
    db: Session = Depends(get_db),
):
    return _run_search(db, query, market, exchange, asset_type, limit, cursor)


@router.get("")
def list_assets(
    query: str | None = None,
    market: str | None = None,
    exchange: str | None = None,
    asset_type: str | None = None,
    limit: int = Query(default=50),
    cursor: str | None = None,
    db: Session = Depends(get_db),
):
    """Search asset universe (api-spec §11.1): same filters as /assets/search."""
    return _run_search(db, query, market, exchange, asset_type, limit, cursor)


@router.get("/{asset_id}")
def get_asset_detail(asset_id: str, db: Session = Depends(get_db)):
    asset_uuid = parse_uuid(asset_id)
    if asset_uuid is None:
        return error_response("NOT_FOUND", f"asset {asset_id} not found", 404)
    row = repo.get_asset_with_market(db, asset_uuid)
    if row is None:
        return error_response("NOT_FOUND", f"asset {asset_id} not found", 404)
    asset, market_code = row
    return success_response(_asset_payload(asset, market_code))
