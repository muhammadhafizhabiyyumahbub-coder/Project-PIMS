"Builds structured analytical context for AI research from database results only."
from sqlalchemy.orm import Session

from app.database.models import Asset, ScannerResult
from app.engines.runner import load_candles
from app.qualification.service import evaluate_engine_readiness


def build_context(session: Session, asset: Asset, timeframe: str) -> dict:
    """All values come from persisted engine outputs; nothing is synthesized."""
    from app.engines.runner import resolve_provider_id
    provider_id = resolve_provider_id(session, asset)
    candles = load_candles(session, asset.id, timeframe, limit=200, provider_id=provider_id)
    last_close = float(candles[-1]["close"]) if candles else None
    close_24h_ago = float(candles[-25]["close"]) if len(candles) >= 25 else None
    daily_change = (
        last_close / close_24h_ago - 1 if last_close and close_24h_ago else None
    )

    scanner_result = (
        session.query(ScannerResult)
        .filter_by(asset_id=asset.id, timeframe=timeframe)
        .order_by(ScannerResult.created_at.desc())
        .first()
    )
    readiness = evaluate_engine_readiness(session, asset.id, timeframe)

    context = {
        "instrument": {
            "symbol": asset.symbol,
            "name": asset.name,
            "asset_type": asset.asset_type,
            "quote_currency": asset.quote_currency,
        },
        "timeframe": timeframe,
        "market_data": {
            "last_close": last_close,
            "daily_change_pct": round(daily_change * 100, 4) if daily_change is not None else None,
            "candle_count_loaded": len(candles),
            "observation_start": candles[0]["close_time"].isoformat() if candles else None,
            "observation_end": candles[-1]["close_time"].isoformat() if candles else None,
        },
        "scanner": {
            "score": float(scanner_result.score) if scanner_result and scanner_result.score else None,
            "rank": scanner_result.rank if scanner_result else None,
            "freshness": scanner_result.freshness_status if scanner_result else None,
            "metrics": scanner_result.metric_snapshot if scanner_result else None,
        },
        "engine_readiness": {
            engine: {
                "state": info["state"],
                "label": info["label"],
                "detail": info["detail"],
            }
            for engine, info in readiness.items()
        },
    }
    return context
