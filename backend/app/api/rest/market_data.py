"Market data endpoints."
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.envelope import error_response, success_response
from app.core.db import get_db
from app.data.validation.freshness import TIMEFRAME_SECONDS, freshness_status
from app.database.models import Asset, DataProvider, MarketCandle
from app.engines.runner import load_candles

router = APIRouter(prefix="/market-data", tags=["Market Data"])


def _decimal_str(value: Decimal | float | None) -> str | None:
    """api-spec §5.3: OHLCV leaves the API as decimal strings, never JSON floats."""
    if value is None:
        return None
    return format(Decimal(str(value)).normalize(), "f")


@router.post("/refresh")
def refresh(symbol: str | None = None, timeframe: str = "1h", db: Session = Depends(get_db)):
    """Fetch latest klines from Bybit and persist normalized candles."""
    from app.data.ingestion.ingest import refresh_asset_candles
    from app.data.storage.universe import ensure_universe

    universe = ensure_universe(db)
    assets = universe["assets"]
    if symbol:
        if symbol not in assets:
            from fastapi import HTTPException

            raise HTTPException(status_code=404, detail="unknown symbol")
        assets = {symbol: assets[symbol]}
    refreshed = {
        sym: refresh_asset_candles(db, asset, timeframe) for sym, asset in assets.items()
    }
    return success_response({"refreshed_candles": refreshed}, meta={"timeframe": timeframe})


@router.get("/candles")
def get_candles(symbol: str, timeframe: str = "1h", limit: int = 200, db: Session = Depends(get_db)):
    asset = db.query(Asset).filter_by(symbol=symbol, is_active=True).one_or_none()
    if asset is None:
        raise HTTPException(status_code=404, detail="unknown symbol")
    candles = load_candles(db, asset.id, timeframe, limit=limit)
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    last_time = candles[-1]["close_time"] if candles else None
    return success_response(
        {
            "symbol": asset.symbol,
            "timeframe": timeframe,
            "freshness_status": freshness_status(last_time, now, timeframe),
            "data_timestamp": last_time.isoformat() if last_time else None,
            "candles": [
                {
                    "open_time": c["open_time"].isoformat(),
                    "close_time": c["close_time"].isoformat() if c["close_time"] else None,
                    "open": c["open"],
                    "high": c["high"],
                    "low": c["low"],
                    "close": c["close"],
                    "volume": c["volume"],
                }
                for c in candles
            ],
        },
        meta={"symbol": asset.symbol, "count": len(candles)},
    )


@router.get("/instruments/{asset_id}/candles")
def get_instrument_candles(
    asset_id: str,
    timeframe: str = "1h",
    start_time: str | None = None,
    end_time: str | None = None,
    limit: int = 300,
    db: Session = Depends(get_db),
):
    """Instrument candles by internal asset id (api-spec §13.1, §13.2).

    Reads only stored rows (no provider fetch). OHLCV are decimal strings per
    api-spec §5.3/§13.4. Empty result is a 200 with an empty list and an honest
    freshness of UNAVAILABLE — never fabricated candles.
    """
    if timeframe not in TIMEFRAME_SECONDS:
        return error_response(
            "VALIDATION_ERROR",
            f"unsupported timeframe {timeframe}; supported: {', '.join(sorted(TIMEFRAME_SECONDS))}",
            422,
        )
    if limit < 1 or limit > 1000:
        return error_response("VALIDATION_ERROR", "limit must be between 1 and 1000", 422)

    bounds = {}
    for name, raw in (("start_time", start_time), ("end_time", end_time)):
        if raw is None:
            continue
        try:
            bounds[name] = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return error_response(
                "VALIDATION_ERROR", f"invalid {name} (ISO-8601 required)", 422
            )

    try:
        aid = uuid.UUID(asset_id)
    except (ValueError, AttributeError):
        return error_response("NOT_FOUND", f"asset {asset_id} not found", 404)
    asset = db.get(Asset, aid)
    if asset is None:
        return error_response("NOT_FOUND", f"asset {asset_id} not found", 404)

    query = db.query(MarketCandle).filter_by(asset_id=aid, timeframe=timeframe)
    if "start_time" in bounds:
        query = query.filter(MarketCandle.open_time >= bounds["start_time"])
    if "end_time" in bounds:
        query = query.filter(MarketCandle.open_time <= bounds["end_time"])
    rows = query.order_by(MarketCandle.open_time.desc()).limit(limit).all()
    rows.reverse()  # oldest first (api-spec §13.6)

    last_close_time = (rows[-1].close_time or rows[-1].open_time) if rows else None
    provider_code = None
    if rows:
        provider_code = db.scalar(
            select(DataProvider.code).where(DataProvider.id == rows[-1].provider_id)
        )
    return success_response(
        {
            "asset_id": str(asset.id),
            "symbol": asset.symbol,
            "timeframe": timeframe,
            "provider": provider_code,
            "currency": rows[-1].currency if rows else asset.quote_currency,
            "candles": [
                {
                    "time": int(c.open_time.timestamp()),
                    "open_time": c.open_time.isoformat(),
                    "close_time": c.close_time.isoformat() if c.close_time else None,
                    "open": _decimal_str(c.open_price),
                    "high": _decimal_str(c.high_price),
                    "low": _decimal_str(c.low_price),
                    "close": _decimal_str(c.close_price),
                    "volume": _decimal_str(c.volume),
                }
                for c in rows
            ],
            "freshness": (
                freshness_status(last_close_time, datetime.now(timezone.utc), timeframe)
                if rows
                else "UNAVAILABLE"
            ),
            "freshness_reason": (
                None if rows else "No stored candles for this asset and timeframe."
            ),
        },
        meta={"count": len(rows), "asset_id": str(asset.id), "timeframe": timeframe},
    )
