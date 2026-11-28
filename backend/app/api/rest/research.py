"Research endpoints: manual trigger, job status, reports, history, delete."
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.research import orchestrator
from app.api.envelope import error_response, success_response
from app.config.settings import get_settings
from app.core.db import get_db
from app.database.models import Asset, ResearchJob, ResearchReport, ResearchRequest

DEDUP_ACTION = "DEDUPLICATED"

router = APIRouter(prefix="/research", tags=["Research"])

def parse_uuid(value: str):
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None


class ResearchRequestBody(BaseModel):
    symbol: str = Field(min_length=1)
    timeframe: str = "1h"
    request_summary: str | None = None

    model_config = {"extra": "forbid"}


def _job_payload(job: ResearchJob) -> dict:
    return {
        "job_id": str(job.id),
        "request_id": str(job.request_id),
        "status": job.status,
        "attempts": job.attempts,
        "max_retries": job.max_retries,
        "engine_readiness": job.engine_readiness,
        "provider": job.provider_name,
        "model": job.model_identifier,
        "report_id": str(job.report_id) if job.report_id else None,
        "error_code": job.error_code,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "updated_at": job.updated_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@router.post("")
@router.post("/requests")
def create_research_request(body: ResearchRequestBody, db: Session = Depends(get_db)):
    """Manual trigger: create request, gate on engine readiness, run bounded job.

    Rate limit: cooldown (default 900s) per asset+timeframe+fingerprint.
    If a recent request exists within cooldown, return it (action=DEDUPLICATED)
    instead of calling the LLM again.
    """
    asset = db.query(Asset).filter_by(symbol=body.symbol, is_active=True).one_or_none()
    if asset is None:
        return error_response("UNKNOWN_SYMBOL", f"unknown symbol {body.symbol}", 404)

    request, job, action = orchestrator.create_request(
        db, asset, body.timeframe, trigger_type="MANUAL"
    )
    # Cooldown gate: if DEDUPLICATED, job is reused (no new LLM call)
    if action == DEDUP_ACTION:
        from app.api.websocket.channels import notify_research_status
        settings = get_settings()
        payload = _job_payload(job)
        notify_research_status(payload)
        return success_response({
            "action": action,
            "job": payload,
            "note": f"request reused from recent run (cooldown {settings.research_cooldown_seconds}s)",
        })
    if body.request_summary:
        request.request_summary = body.request_summary
        db.commit()
    # Synchronous execution: there is no separate worker, so an existing
    # non-terminal job (e.g. left by a crashed request) is simply resumed.
    if job.status != orchestrator.COMPLETED:
        job = orchestrator.run_job(db, job)
    from app.api.websocket.channels import notify_research_status

    payload = _job_payload(job)
    notify_research_status(payload)
    return success_response({"action": action, "job": payload})


@router.get("/requests/{request_id}")
def get_research_request(request_id: str, db: Session = Depends(get_db)):
    rid = parse_uuid(request_id)
    if rid is None:
        return error_response("NOT_FOUND", f"request {request_id} not found", 404)
    request = db.get(ResearchRequest, rid)
    if request is None:
        return error_response("NOT_FOUND", f"request {request_id} not found", 404)
    jobs = (
        db.query(ResearchJob)
        .filter_by(request_id=request.id)
        .order_by(ResearchJob.created_at.desc())
        .all()
    )
    return success_response(
        {
            "request_id": str(request.id),
            "trigger_type": request.trigger_type,
            "required_engines": request.required_engines,
            "optional_engines": request.optional_engines,
            "context_fingerprint": request.context_fingerprint,
            "jobs": [_job_payload(j) for j in jobs],
        }
    )


@router.get("/{report_id}")
@router.get("/reports/{report_id}")
def get_research_report(report_id: str, db: Session = Depends(get_db)):
    rid = parse_uuid(report_id)
    if rid is None:
        return error_response("NOT_FOUND", f"report {report_id} not found", 404)
    report = db.get(ResearchReport, rid)
    if report is None:
        return error_response("NOT_FOUND", f"report {report_id} not found", 404)
    return success_response(
        {
            "report_id": str(report.id),
            "request_id": str(report.request_id),
            "title": report.title,
            "research_type": report.research_type,
            "provider": report.ai_provider,
            "model": report.model_identifier,
            "execution_status": report.execution_status,
            "observation_start": report.observation_start.isoformat() if report.observation_start else None,
            "observation_end": report.observation_end.isoformat() if report.observation_end else None,
            "generated_at": report.generated_at.isoformat() if report.generated_at else None,
            "report_content": report.report_content,
        }
    )


def _report_summary(db: Session, report: ResearchReport) -> dict:
    request = db.get(ResearchRequest, report.request_id)
    asset = db.get(Asset, request.asset_id) if request and request.asset_id else None
    return {
        "report_id": str(report.id),
        "request_id": str(report.request_id),
        "title": report.title,
        "research_type": report.research_type,
        "request_summary": report.request_summary,
        "asset": {"id": str(asset.id), "symbol": asset.symbol} if asset else None,
        "provider": report.ai_provider,
        "model": report.model_identifier,
        "execution_status": report.execution_status,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
        "created_at": report.created_at.isoformat(),
    }


@router.get("")
def list_research(
    limit: int = Query(20, ge=1, le=100),
    cursor: str | None = Query(
        None, description="ISO-8601 created_at of the last item of the previous page"
    ),
    db: Session = Depends(get_db),
):
    """Research report history, newest first (api-spec §18.1).

    Cursor pagination on created_at: pass the `meta.next_cursor` of the previous
    page. Empty history is a 200 with an empty list, never an error.
    """
    query = db.query(ResearchReport).order_by(ResearchReport.created_at.desc(), ResearchReport.id.desc())
    if cursor:
        try:
            after = datetime.fromisoformat(cursor.replace("Z", "+00:00"))
        except ValueError:
            return error_response("VALIDATION_ERROR", "cursor must be ISO-8601", 422)
        query = query.filter(ResearchReport.created_at < after)
    reports = query.limit(limit + 1).all()
    has_more = len(reports) > limit
    reports = reports[:limit]
    next_cursor = reports[-1].created_at.isoformat() if has_more and reports else None
    return success_response(
        [_report_summary(db, r) for r in reports],
        meta={"count": len(reports), "limit": limit, "has_more": has_more, "next_cursor": next_cursor},
    )


@router.delete("/{report_id}")
def delete_research_report(report_id: str, db: Session = Depends(get_db)):
    """Delete one research report (api-spec §18.1).

    Only the report row is removed. The originating request and job stay: the
    spec defines deletion of a report, not of its request history. Job references
    are detached first so the FK does not block the delete.
    """
    try:
        rid = uuid.UUID(report_id)
    except (ValueError, AttributeError):
        return error_response("NOT_FOUND", f"report {report_id} not found", 404)
    report = db.get(ResearchReport, rid)
    if report is None:
        return error_response("NOT_FOUND", f"report {report_id} not found", 404)

    jobs = db.query(ResearchJob).filter_by(report_id=rid).all()
    for job in jobs:
        job.report_id = None
    db.delete(report)
    db.commit()
    return success_response({"report_id": str(rid), "deleted": True})
