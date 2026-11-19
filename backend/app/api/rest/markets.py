"""Market endpoints per api-spec §12 (read-only, derived from stored rows).

Shape assumptions (api-spec §12.2 lists the fields but not their exact JSON):

- `session` is derived from `markets.market_type` only. CRYPTO spot trades
  continuously; any other market reports UNKNOWN with a reason because no
  session schedule is stored. Reporting OPEN/CLOSED would be a guess.
- `data_availability` reuses the shared freshness policy
  (data/validation/freshness.py) over the newest stored candle of the market;
  when there is no candle it says UNAVAILABLE. This is never a provider
  connection claim, only what the stored data supports.
- `exchanges` lists the data provider codes mapped to instruments in the
  market via provider_instruments (internal identity stays assets.id).
- A market is resolvable by `markets.id` (UUID) or `markets.code`.
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.envelope import error_response, success_response
from app.core.db import get_db
from app.data.validation.freshness import freshness_status
from app.database.models import Asset, DataProvider, Market, MarketCandle, ProviderInstrument

router = APIRouter(prefix="/markets", tags=["Markets"])

# Fact about the asset class, not feed data: crypto spot venues trade 24/7.
CONTINUOUS_MARKET_TYPES = {"CRYPTO"}


def _session(market: Market) -> dict:
    if market.market_type in CONTINUOUS_MARKET_TYPES:
        return {"status": "CONTINUOUS", "reason": "Crypto spot markets trade continuously."}
    return {
        "status": "UNKNOWN",
        "reason": "No market session schedule is stored; session status cannot be derived.",
    }


def _latest_market_candle(db: Session, market_id):
    return db.execute(
        select(MarketCandle.close_time, MarketCandle.open_time, MarketCandle.timeframe)
        .join(Asset, MarketCandle.asset_id == Asset.id)
        .where(Asset.market_id == market_id)
        .order_by(MarketCandle.open_time.desc())
        .limit(1)
    ).first()


def _data_availability(db: Session, market_id) -> dict:
    row = _latest_market_candle(db, market_id)
    if row is None:
        return {
            "status": "UNAVAILABLE",
            "latest_candle_at": None,
            "timeframe": None,
            "reason": "No stored candles for any instrument in this market.",
        }
    close_time, open_time, timeframe = row
    stamp = close_time or open_time
    return {
        "status": freshness_status(stamp, datetime.now(timezone.utc), timeframe),
        "latest_candle_at": stamp.isoformat(),
        "timeframe": timeframe,
        "reason": None,
    }


def _market_payload(market: Market, instruments_count: int) -> dict:
    return {
        "id": str(market.id),
        "code": market.code,
        "name": market.name,
        "market_type": market.market_type,
        "country_code": market.country_code,
        "timezone": market.timezone,
        "is_active": market.is_active,
        "instruments_count": instruments_count,
    }


@router.get("")
def list_markets(db: Session = Depends(get_db)):
    """Supported markets with the count of active instruments in each."""
    rows = db.execute(
        select(Market, func.count(Asset.id))
        .outerjoin(Asset, (Asset.market_id == Market.id) & (Asset.is_active.is_(True)))
        .group_by(Market.id)
        .order_by(Market.code)
    ).all()
    return success_response(
        [_market_payload(market, count) for market, count in rows],
        meta={"count": len(rows)},
    )


@router.get("/status")
def markets_status(db: Session = Depends(get_db)):
    """Per-market session + stored-data freshness. Declared before /{market_id}."""
    markets = list(db.scalars(select(Market).order_by(Market.code)))
    rows = [
        {
            "market": market.code,
            "market_type": market.market_type,
            "session": _session(market),
            "data_availability": _data_availability(db, market.id),
        }
        for market in markets
    ]
    return success_response(rows, meta={"count": len(rows)})


@router.get("/{market_id}")
def get_market(market_id: str, db: Session = Depends(get_db)):
    """Market detail by UUID or code: instruments, exchanges, session, data age."""
    market = None
    try:
        market = db.get(Market, uuid.UUID(market_id))
    except (ValueError, AttributeError):
        market = None
    if market is None:
        market = db.scalars(select(Market).where(Market.code.ilike(market_id))).first()
    if market is None:
        return error_response("NOT_FOUND", f"market {market_id} not found", 404)

    assets = list(
        db.scalars(
            select(Asset)
            .where(Asset.market_id == market.id, Asset.is_active.is_(True))
            .order_by(Asset.symbol)
        )
    )
    exchanges = sorted(
        set(
            db.scalars(
                select(DataProvider.code)
                .join(ProviderInstrument, ProviderInstrument.provider_id == DataProvider.id)
                .join(Asset, Asset.id == ProviderInstrument.asset_id)
                .where(Asset.market_id == market.id)
                .distinct()
            )
        )
    )
    payload = {
        **_market_payload(market, len(assets)),
        "exchanges": exchanges,
        "session": _session(market),
        "data_availability": _data_availability(db, market.id),
        "instruments": [
            {
                "id": str(asset.id),
                "symbol": asset.symbol,
                "name": asset.name,
                "asset_type": asset.asset_type,
                "quote_currency": asset.quote_currency,
            }
            for asset in assets[:50]
        ],
    }
    return success_response(payload)