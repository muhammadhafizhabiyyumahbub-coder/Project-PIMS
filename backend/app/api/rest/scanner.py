"Scanner endpoints per api-spec A 16 (read-only: categories, results, runs; plus existing POST /run)."
import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.envelope import error_response, success_response
from app.core.db import get_db
from app.api.schemas.scanner import ScannerConfigCreate, ScannerConfigUpdate
from app.engines.scanner.service import run_scanner
from app.database.repositories import scanner as repo
from app.database.models import (
    Asset,
    Market,
    MarketCandle,
    DataProvider,
    ProviderInstrument,
    ScannerConfiguration,
    ScannerResult,
    ScannerRun,
)

router = APIRouter(prefix="/scanner", tags=["Scanner"])

def parse_uuid(value: str):
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None

# api-spec A 16.2 scanner categories
SCANNER_CATEGORIES = [
    "TECHNICAL",
    "MOMENTUM",
    "VOLUME",
    "VOLATILITY",
    "FUNDAMENTAL",
    "MARKET_TREND",
    "ANOMALY",
    "CORRELATION",
]

@router.post("/run")
def scanner_run(timeframe: str = "1h", db: Session = Depends(get_db)):
    run = run_scanner(db, timeframe)
    return success_response(
        {
            "scanner_run_id": str(run.id),
            "execution_status": run.execution_status,
            "universe_size": run.universe_size,
            "eligible_count": run.eligible_count,
            "result_count": run.result_count,
            "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        }
    )

@router.get("/categories")
def scanner_categories():
    """Supported scanner categories per api-spec A 16.2."""
    return success_response(SCANNER_CATEGORIES, meta={"count": len(SCANNER_CATEGORIES)})

# Scanner Config endpoints
@router.post("/configurations")
def create_config(
    payload: ScannerConfigCreate,
    db: Session = Depends(get_db),
):
    if payload.category not in SCANNER_CATEGORIES:
        return error_response("VALIDATION_ERROR", f"invalid category: {payload.category}", 422)
    if not isinstance(payload.universe_config, dict) or not isinstance(payload.filter_config, dict):
         return error_response("VALIDATION_ERROR", "configs must be JSON objects", 422)
    
    config = repo.create_scanner_config(
        db, payload.name, payload.category, payload.universe_config, payload.filter_config, payload.description, payload.ranking_config, payload.timeframe
    )
    db.commit()
    return success_response({"id": str(config.id)})

@router.get("/configurations")
def list_configs(db: Session = Depends(get_db)):
    configs = repo.list_scanner_configs(db)
    return success_response([
        {
            "id": str(c.id),
            "name": c.name,
            "category": c.category,
            "is_active": c.is_active,
        } for c in configs
    ])

@router.patch("/configurations/{config_id}")
def update_config(config_id: str, payload: ScannerConfigUpdate, db: Session = Depends(get_db)):
    cid = parse_uuid(config_id)
    if cid is None:
        return error_response("NOT_FOUND", "not found", 404)
        
    config = repo.get_scanner_config(db, cid)
    if not config:
        return error_response("NOT_FOUND", "not found", 404)
        
    repo.update_scanner_config(db, config, **payload.model_dump(exclude_unset=True))
    db.commit()
    return success_response({"id": str(config.id)})

@router.delete("/configurations/{config_id}")
def delete_config(config_id: str, db: Session = Depends(get_db)):
    cid = parse_uuid(config_id)
    if cid is None:
        return error_response("NOT_FOUND", "not found", 404)
        
    config = repo.get_scanner_config(db, cid)
    if not config:
        return error_response("NOT_FOUND", "not found", 404)
        
    repo.delete_scanner_config(db, config)
    db.commit()
    return success_response(None)

@router.get("/results")
def scanner_results(
    scanner_run_id: str | None = Query(None, description="Filter by run UUID"),
    market: str | None = Query(None, description="Filter by market code"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Retrieve scanner results per api-spec A 16.1."""
    query = db.query(ScannerResult).order_by(ScannerResult.created_at.desc())
    if scanner_run_id:
        rid = parse_uuid(scanner_run_id)
        if rid is None:
            return error_response("NOT_FOUND", f"scanner run {scanner_run_id} not found", 404)
        query = query.filter(ScannerResult.scanner_run_id == rid)
    results = query.limit(limit).all()

    rows = []
    # One batched lookup per timeframe keeps this honest without an N+1 query.
    currency_by_timeframe: dict[str, dict] = {}
    timeframes = {r.timeframe for r in results}
    for tf in timeframes:
        currency_by_timeframe[tf] = dict(
            db.query(MarketCandle.asset_id, MarketCandle.currency)
            .filter(MarketCandle.timeframe == tf)
            .distinct(MarketCandle.asset_id)
            .order_by(MarketCandle.asset_id, MarketCandle.open_time.desc())
            .all()
        )
    for r in results:
        asset = db.get(Asset, r.asset_id)
        m = db.get(Market, asset.market_id) if asset and asset.market_id else None
        if market and (not m or m.code.upper() != market.upper()):
            continue
        data_currency = currency_by_timeframe.get(r.timeframe, {}).get(r.asset_id)
        rows.append({
            "scanner_result_id": str(r.id),
            "scanner_run_id": str(r.scanner_run_id),
            "instrument": {"symbol": asset.symbol, "name": asset.name, "asset_type": asset.asset_type} if asset else None,
            "market": m.code if m else None,
            "rank": r.rank,
            "score": format(Decimal(str(r.score)).normalize(), "f") if r.score is not None else None,
            "matched_rules": r.matched_rules,
            "metric_snapshot": r.metric_snapshot,
            # Currency of the price that was actually scanned (provider data) and the
            # asset's nominal quote currency; they differ by design for crypto (USD vs USDT).
            "data_currency": data_currency,
            "quote_currency": asset.quote_currency if asset else None,
            "result_status": r.result_status,
            "data_status": r.freshness_status,
            "data_timestamp": r.data_timestamp.isoformat() if r.data_timestamp else None,
            "created_at": r.created_at.isoformat(),
        })
    return success_response(rows, meta={"count": len(rows)})

@router.get("/runs/{run_id}")
def get_scanner_run(run_id: str, db: Session = Depends(get_db)):
    """Retrieve scanner run detail and summary metrics."""
    rid = parse_uuid(run_id)
    if rid is None:
        return error_response("NOT_FOUND", f"scanner run {run_id} not found", 404)
    run = db.get(ScannerRun, rid)
    if run is None:
        return error_response("NOT_FOUND", f"scanner run {run_id} not found", 404)
    results_count = db.query(ScannerResult).filter_by(scanner_run_id=run.id).count()
    return success_response({
        "scanner_run_id": str(run.id),
        "execution_mode": run.execution_mode,
        "execution_status": run.execution_status,
        "universe_size": run.universe_size,
        "eligible_count": run.eligible_count,
        "result_count": run.result_count or results_count,
        "started_at": run.started_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "error_message": run.error_message,
        "execution_metadata": run.execution_metadata,
    })

@router.get("/results/{result_id}/qualification")
def result_qualification(result_id: str, db: Session = Depends(get_db)):
    from app.api.rest.dashboard import _opportunity
    from app.database.models import Market
    from app.qualification.service import (
        evaluate_engine_readiness,
        jsonable_readiness,
        qualification_summary,
    )

    rid = parse_uuid(result_id)
    if rid is None:
        return error_response("NOT_FOUND", f"scanner result {result_id} not found", 404)
    result = db.get(ScannerResult, rid)
    if result is None:
        return error_response("NOT_FOUND", f"scanner result {result_id} not found", 404)
    asset = db.get(Asset, result.asset_id)
    market = db.get(Market, asset.market_id) if asset.market_id else None
    readiness = evaluate_engine_readiness(db, asset.id, result.timeframe)
    summary = qualification_summary(readiness)
    from datetime import datetime, timezone

    from app.data.validation.freshness import freshness_status

    return success_response(
        {
            "scanner_result_id": str(result.id),
            "instrument": asset.symbol,
            "approval_status": summary["status"],
            "passed_by": summary["passed_by"],
            "engine_readiness": jsonable_readiness(readiness),
            "data_status": freshness_status(
                result.data_timestamp, datetime.now(timezone.utc), result.timeframe
            ),
            "updated_at": result.data_timestamp.isoformat(),
        }
    )
