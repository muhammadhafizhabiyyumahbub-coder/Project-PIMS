"""Analytics persistence REST endpoints."""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.envelope import error_response, success_response
from app.core.db import get_db
from app.database.repositories import analytics as analytics_repo
from app.database.repositories import portfolio as repo
from app.services.analytics import (
    _allocation_payload,
    _performance_payload,
    _risk_payload,
    _run_payload,
    persist_analytics,
)

router = APIRouter(prefix="/portfolios", tags=["Analytics Runs"])


def parse_uuid(value: str):
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


class AnalyticsRunCreate(BaseModel):
    analysis_type: str = Field(..., description="performance, risk, or allocation")
    window_days: int | None = Field(default=None, ge=30, le=3650)
    start: str | None = None
    end: str | None = None


@router.post("/{portfolio_id}/analytics/runs")
def create_analytics_run(
    portfolio_id: str,
    payload: AnalyticsRunCreate,
    db: Session = Depends(get_db),
):
    """Compute analytics on-demand and persist the run + results (manual trigger)."""
    pid = parse_uuid(portfolio_id)
    if pid is None or repo.get_portfolio(db, pid) is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)

    analysis_type = payload.analysis_type.lower()
    if analysis_type not in ("performance", "risk", "allocation"):
        return error_response(
            "VALIDATION_ERROR",
            "analysis_type must be performance, risk, or allocation",
            422,
        )

    start_dt = None
    end_dt = None
    if payload.start:
        try:
            start_dt = datetime.fromisoformat(payload.start.replace("Z", "+00:00"))
        except ValueError:
            return error_response("VALIDATION_ERROR", "invalid start date format", 422)
    if payload.end:
        try:
            end_dt = datetime.fromisoformat(payload.end.replace("Z", "+00:00"))
        except ValueError:
            return error_response("VALIDATION_ERROR", "invalid end date format", 422)

    try:
        run, rows = persist_analytics(
            db,
            pid,
            analysis_type,
            window_days=payload.window_days,
            start=start_dt,
            end=end_dt,
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        return error_response("VALIDATION_ERROR", str(exc), 422)
    except Exception as exc:
        db.rollback()
        return error_response("SERVER_ERROR", str(exc), 500)

    # Serialize results based on type
    if analysis_type == "performance":
        serialized_results = [_performance_payload(r) for r in rows]
    elif analysis_type == "risk":
        serialized_results = [_risk_payload(r) for r in rows]
    else:
        serialized_results = [_allocation_payload(r) for r in rows]

    return success_response(
        {
            "run": _run_payload(run),
            "results": serialized_results,
        },
        status_code=201,
    )


@router.get("/{portfolio_id}/analytics/runs")
def list_analytics_runs(
    portfolio_id: str,
    limit: int = 50,
    cursor: str | None = None,
    db: Session = Depends(get_db),
):
    """List persisted analytics runs for a portfolio, paginated newest first."""
    if limit < 1 or limit > 200:
        return error_response("VALIDATION_ERROR", "limit must be between 1 and 200", 422)
    pid = parse_uuid(portfolio_id)
    if pid is None or repo.get_portfolio(db, pid) is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)

    cursor_run = None
    if cursor:
        cursor_id = parse_uuid(cursor)
        if cursor_id is None:
            return error_response("VALIDATION_ERROR", "invalid cursor", 422)
        cursor_run = analytics_repo.get_run(db, cursor_id)
        if cursor_run is None or (cursor_run.input_metadata or {}).get("portfolio_id") != str(pid):
            return error_response("VALIDATION_ERROR", "invalid cursor", 422)

    rows, has_more = analytics_repo.list_runs_page(db, pid, limit=limit, cursor_run=cursor_run)
    return success_response(
        [_run_payload(r) for r in rows],
        meta={
            "count": len(rows),
            "pagination": {
                "limit": limit,
                "next_cursor": str(rows[-1].id) if has_more and rows else None,
                "has_more": has_more,
            },
        },
    )


@router.get("/{portfolio_id}/analytics/runs/{run_id}")
def get_analytics_run_detail(
    portfolio_id: str,
    run_id: str,
    db: Session = Depends(get_db),
):
    """Get detail of one analytics run + its persisted results."""
    pid = parse_uuid(portfolio_id)
    if pid is None or repo.get_portfolio(db, pid) is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
    rid = parse_uuid(run_id)
    if rid is None:
        return error_response("NOT_FOUND", f"run {run_id} not found", 404)

    run = analytics_repo.get_run(db, rid)
    if run is None or (run.input_metadata or {}).get("portfolio_id") != str(pid):
        return error_response("NOT_FOUND", f"run {run_id} not found", 404)

    perf, risk, alloc = analytics_repo.get_results_for_run(db, rid)
    if perf:
        results = [_performance_payload(r) for r in perf]
    elif risk:
        results = [_risk_payload(r) for r in risk]
    elif alloc:
        results = [_allocation_payload(r) for r in alloc]
    else:
        results = []

    return success_response(
        {
            "run": _run_payload(run),
            "results": results,
        }
    )
