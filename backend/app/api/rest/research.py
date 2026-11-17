"Research endpoints: manual trigger, job status, reports."
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.ai.research import orchestrator
from app.api.envelope import error_response, success_response
from app.core.db import get_db
from app.database.models import Asset, ResearchJob, ResearchReport, ResearchRequest

router = APIRouter(prefix="/research", tags=["Research"])


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


@router.post("/requests")
def create_research_request(body: ResearchRequestBody, db: Session = Depends(get_db)):
    """Manual trigger: create request, gate on engine readiness, run bounded job."""
    asset = db.query(Asset).filter_by(symbol=body.symbol, is_active=True).one_or_none()
    if asset is None:
        return error_response("UNKNOWN_SYMBOL", f"unknown symbol {body.symbol}", 404)

    request, job, action = orchestrator.create_request(
        db, asset, body.timeframe, trigger_type="MANUAL"
    )
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
    request = db.get(ResearchRequest, request_id)
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


@router.get("/reports/{report_id}")
def get_research_report(report_id: str, db: Session = Depends(get_db)):
    report = db.get(ResearchReport, report_id)
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
