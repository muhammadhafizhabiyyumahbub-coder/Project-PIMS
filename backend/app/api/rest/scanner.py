"Scanner endpoints."
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.envelope import success_response
from app.core.db import get_db
from app.database.models import Asset, ScannerResult
from app.engines.scanner.service import run_scanner

router = APIRouter(prefix="/scanner", tags=["Scanner"])


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


@router.get("/results/{result_id}/qualification")
def result_qualification(result_id: str, db: Session = Depends(get_db)):
    from app.api.rest.dashboard import _opportunity
    from app.database.models import Market
    from app.qualification.service import (
        evaluate_engine_readiness,
        jsonable_readiness,
        qualification_summary,
    )

    result = db.get(ScannerResult, result_id)
    if result is None:
        from app.api.envelope import error_response

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
