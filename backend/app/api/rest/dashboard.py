"Dashboard endpoints: Instrument Opportunities from scanner results."
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.envelope import success_response
from app.core.db import get_db
from app.data.validation.freshness import freshness_status
from app.database.models import Asset, Market, ScannerResult
from app.engines.runner import load_candles
from app.qualification.service import evaluate_engine_readiness, qualification_summary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

TERMINAL_STATUS = "NOT_QUALIFIED"


def _opportunity(db: Session, result: ScannerResult, asset: Asset, market: Market, timeframe: str) -> dict:
    candles = load_candles(db, asset.id, timeframe, limit=30)
    last_close = float(candles[-1]["close"]) if candles else None
    change = None
    if len(candles) >= 25:
        prev = float(candles[-25]["close"])
        change = round((last_close / prev - 1) * 100, 4) if prev else None

    readiness = evaluate_engine_readiness(db, asset.id, timeframe)
    summary = qualification_summary(readiness)
    regime = readiness.get("MARKET_REGIME", {})
    risk = readiness.get("RISK", {})

    return {
        "scanner_result_id": str(result.id),
        "instrument": {"symbol": asset.symbol, "name": asset.name, "asset_type": asset.asset_type},
        "market": market.code if market else None,
        "current_price": last_close,
        "daily_change_pct": change,
        "quote_currency": asset.quote_currency,
        "scanner_score": float(result.score) if result.score is not None else None,
        "scanner_rank": result.rank,
        "market_regime": regime.get("detail", {}).get("trend_regime"),
        "risk_status": risk.get("detail", {}).get("classification"),
        "approval_status": summary["status"],
        "passed_by": summary["passed_by"],
        "engine_readiness": {
            engine: {"state": info["state"], "label": info["label"]}
            for engine, info in readiness.items()
        },
        "updated_at": result.data_timestamp.isoformat() if result.data_timestamp else None,
        # Display freshness is evaluated at request time, not frozen at scan time.
        "data_status": freshness_status(result.data_timestamp, datetime.now(timezone.utc), result.timeframe),
    }


@router.get("/instrument-opportunities")
def instrument_opportunities(
    market: str | None = None,
    qualification: str | None = None,
    sort: str = "scanner_score",
    db: Session = Depends(get_db),
):
    """Latest scanner result per asset, joined with qualification readiness."""
    latest = (
        db.query(ScannerResult)
        .order_by(ScannerResult.created_at.desc())
        .all()
    )
    seen: set = set()
    rows: list[dict] = []
    for result in latest:
        if result.asset_id in seen:
            continue
        seen.add(result.asset_id)
        asset = db.get(Asset, result.asset_id)
        market_row = db.get(Market, asset.market_id) if asset and asset.market_id else None
        rows.append(_opportunity(db, result, asset, market_row, result.timeframe))

    if market:
        rows = [r for r in rows if (r["market"] or "").upper() == market.upper()]
    if qualification:
        rows = [r for r in rows if r["approval_status"].upper() == qualification.upper()]

    sort_keys = {
        "scanner_score": lambda r: r["scanner_score"] or -1,
        "daily_change": lambda r: r["daily_change_pct"] or -1e9,
        "symbol": lambda r: r["instrument"]["symbol"],
        "updated_at": lambda r: r["updated_at"] or "",
        "market": lambda r: r["market"] or "",
    }
    rows.sort(key=sort_keys.get(sort, sort_keys["scanner_score"]), reverse=sort != "symbol")

    return success_response(rows, meta={"count": len(rows), "sort": sort})
