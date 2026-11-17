"Market data endpoints."
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.envelope import success_response
from app.core.db import get_db
from app.data.validation.freshness import freshness_status
from app.database.models import Asset
from app.engines.runner import load_candles

router = APIRouter(prefix="/market-data", tags=["Market Data"])


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
