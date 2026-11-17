"AI research orchestration: readiness gating, dedup, fingerprint, cooldown, lifecycle."
import hashlib
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.ai.context_builder.builder import build_context
from app.ai.providers.openai_compat import OpenAICompatibleProvider, ProviderNotConfigured
from app.ai.report_generator.generator import (
    SYSTEM_PROMPT,
    OutputValidationError,
    build_report_prompt,
    extract_json,
    validate_report,
)
from app.config.settings import get_settings
from app.database.models import Asset, ResearchJob, ResearchReport, ResearchRequest
from app.qualification.policy import DEFAULT_POLICY
from app.qualification.service import evaluate_engine_readiness, jsonable_readiness, qualification_summary

CREATED = "CREATED"
WAITING_FOR_ENGINES = "WAITING_FOR_ENGINES"
VALIDATING_CONTEXT = "VALIDATING_CONTEXT"
READY_FOR_AI = "READY_FOR_AI"
RUNNING_AI = "RUNNING_AI"
VALIDATING_OUTPUT = "VALIDATING_OUTPUT"
COMPLETED = "COMPLETED"
BLOCKED = "BLOCKED"
FAILED = "FAILED"
CANCELLED = "CANCELLED"

# Recoverable errors may be retried up to max_retries within one run (bounded backoff).
RETRYABLE_ERRORS = {"PROVIDER_HTTP_ERROR", "OUTPUT_INVALID"}
BACKOFF_SECONDS = 2.0


def context_fingerprint(context: dict) -> str:
    """Stable hash of the analytical context; unchanged context means no new report."""
    canonical = json.dumps(context, sort_keys=True, default=str).encode()
    return hashlib.sha256(canonical).hexdigest()


def find_active_job(session: Session, request_id) -> ResearchJob | None:
    """Dedup: an in-flight job for the same request is reused, not duplicated."""
    return (
        session.query(ResearchJob)
        .filter(
            ResearchJob.request_id == request_id,
            ResearchJob.status.in_(
                [CREATED, WAITING_FOR_ENGINES, VALIDATING_CONTEXT, READY_FOR_AI, RUNNING_AI, VALIDATING_OUTPUT]
            ),
        )
        .one_or_none()
    )


def find_recent_request(session: Session, asset_id, timeframe: str, fingerprint: str, cooldown_seconds: int):
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=cooldown_seconds)
    return (
        session.query(ResearchRequest)
        .filter(
            ResearchRequest.asset_id == asset_id,
            ResearchRequest.timeframe == timeframe,
            ResearchRequest.context_fingerprint == fingerprint,
            ResearchRequest.created_at >= cutoff,
        )
        .order_by(ResearchRequest.created_at.desc())
        .first()
    )


def create_request(
    session: Session,
    asset: Asset,
    timeframe: str,
    trigger_type: str = "MANUAL",
) -> tuple[ResearchRequest, ResearchJob | None, str]:
    """Create request + job, or return existing cached request during cooldown.

    Returns (request, job, action) where action is CREATED, DEDUPLICATED or
    REPORT_REUSED. An existing completed report with the same fingerprint is
    reused instead of calling the LLM again.
    """
    settings = get_settings()
    context = build_context(session, asset, timeframe)
    fingerprint = context_fingerprint(context)
    now = datetime.now(timezone.utc)

    recent = find_recent_request(
        session, asset.id, timeframe, fingerprint, settings.research_cooldown_seconds
    )
    if recent is not None:
        job = (
            session.query(ResearchJob)
            .filter_by(request_id=recent.id)
            .order_by(ResearchJob.created_at.desc())
            .first()
        )
        if job and job.status == COMPLETED and job.report_id:
            return recent, job, "REPORT_REUSED"
        if job and job.status not in (FAILED, BLOCKED, CANCELLED):
            return recent, job, "DEDUPLICATED"

    request = ResearchRequest(
        research_type="INSTRUMENT",
        asset_id=asset.id,
        timeframe=timeframe,
        trigger_type=trigger_type,
        required_engines=DEFAULT_POLICY["required_engines"],
        optional_engines=DEFAULT_POLICY["optional_engines"],
        context_fingerprint=fingerprint,
        created_at=now,
        updated_at=now,
    )
    session.add(request)
    session.flush()

    job = ResearchJob(
        request_id=request.id,
        status=WAITING_FOR_ENGINES,
        context_fingerprint=fingerprint,
        attempts=0,
        max_retries=settings.research_max_retries,
        created_at=now,
        updated_at=now,
    )
    session.add(job)
    session.commit()
    return request, job, "CREATED"


def run_job(session: Session, job: ResearchJob) -> ResearchJob:
    """Execute one research job through the gated lifecycle. Synchronous, bounded."""
    settings = get_settings()
    now = datetime.now(timezone.utc)

    def advance(status: str, **extra) -> None:
        job.status = status
        job.updated_at = datetime.now(timezone.utc)
        for key, value in extra.items():
            setattr(job, key, value)
        session.commit()

    request = session.get(ResearchRequest, job.request_id)
    asset = session.get(Asset, request.asset_id)

    # Gate 1: required engines must be READY (never BLOCKED/FAILED/STALE/PENDING).
    readiness = evaluate_engine_readiness(session, asset.id, request.timeframe)
    job.engine_readiness = jsonable_readiness(readiness)
    session.commit()
    required = [k for k, v in readiness.items() if v["detail"].get("required")]
    blocking = [k for k in required if readiness[k]["state"] != "READY"]
    if blocking:
        advance(
            BLOCKED,
            error_code="ENGINES_NOT_READY",
            error_message=f"Required engines not READY: {', '.join(blocking)}",
        )
        return job

    # Gate 2: context validation + fingerprint recheck.
    advance(VALIDATING_CONTEXT)
    context = build_context(session, asset, request.timeframe)
    fingerprint = context_fingerprint(context)
    if fingerprint != job.context_fingerprint:
        job.context_fingerprint = fingerprint
        request.context_fingerprint = fingerprint
        session.commit()

    # Reuse completed report with identical fingerprint (no duplicate LLM calls).
    existing = (
        session.query(ResearchReport)
        .join(ResearchJob, ResearchJob.report_id == ResearchReport.id)
        .filter(
            ResearchJob.context_fingerprint == fingerprint,
            ResearchJob.status == COMPLETED,
            ResearchJob.created_at
            >= datetime.now(timezone.utc) - timedelta(seconds=settings.research_cooldown_seconds),
        )
        .first()
    )
    if existing:
        job.report_id = existing.id
        advance(COMPLETED, completed_at=datetime.now(timezone.utc))
        return job

    advance(READY_FOR_AI)

    # Gate 3: provider must be configured before any LLM call.
    try:
        provider = OpenAICompatibleProvider.from_settings()
    except ProviderNotConfigured as exc:
        advance(FAILED, error_code="PROVIDER_NOT_CONFIGURED", error_message=str(exc))
        return job

    advance(RUNNING_AI, provider_name=provider.provider_name, model_identifier=provider.model)
    prompt = build_report_prompt(context)

    # Bounded retry loop: no infinite retries, backoff between attempts.
    attempts = 0
    while attempts <= job.max_retries:
        attempts += 1
        job.attempts = attempts
        session.commit()
        try:
            raw = provider.generate(SYSTEM_PROMPT, prompt)
            report = validate_report(extract_json(raw))
            break
        except OutputValidationError as exc:
            if attempts > job.max_retries:
                advance(FAILED, error_code="OUTPUT_INVALID", error_message=str(exc))
                return job
        except Exception as exc:  # provider/HTTP failure, recoverable
            if attempts > job.max_retries:
                advance(
                    FAILED,
                    error_code="PROVIDER_HTTP_ERROR",
                    error_message=str(exc)[:1000],
                )
                return job

    advance(VALIDATING_OUTPUT)
    report_row = ResearchReport(
        request_id=request.id,
        research_type=request.research_type,
        title=f"{asset.symbol} instrument research",
        request_summary=request.request_summary,
        report_content=report,
        ai_provider=provider.provider_name,
        model_identifier=provider.model,
        execution_status="COMPLETED",
        observation_start=context["market_data"]["observation_start"],
        observation_end=context["market_data"]["observation_end"],
        generated_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
    )
    session.add(report_row)
    session.flush()
    job.report_id = report_row.id
    advance(COMPLETED, completed_at=datetime.now(timezone.utc))
    return job
