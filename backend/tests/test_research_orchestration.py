"Seam 1: research orchestration gating, dedup, fingerprint, retry bounds."
from datetime import datetime, timedelta, timezone

import pytest

from app.ai.research import orchestrator
from app.database.models import ResearchJob, ResearchReport, ResearchRequest
from app.qualification import service


def test_create_request_computes_fingerprint(db_session, btc_asset):
    request, job, action = orchestrator.create_request(db_session, btc_asset, "1h")
    assert action == "CREATED"
    assert len(request.context_fingerprint) == 64
    assert job.status == orchestrator.WAITING_FOR_ENGINES
    assert job.attempts == 0


def test_fingerprint_changes_when_context_changes(db_session, analyzed_universe):
    from app.ai.context_builder.builder import build_context

    btc = analyzed_universe["assets"]["BTCUSDT"]
    first = orchestrator.context_fingerprint(build_context(db_session, btc, "1h"))

    result = service._latest_scanner_result(db_session, btc.id, "1h")
    result.score = 99.0
    db_session.commit()

    second = orchestrator.context_fingerprint(build_context(db_session, btc, "1h"))
    assert first != second


def test_job_blocked_when_required_engines_not_ready(db_session, seeded_universe):
    btc = seeded_universe["assets"]["BTCUSDT"]
    request, job, _ = orchestrator.create_request(db_session, btc, "1h")
    finished = orchestrator.run_job(db_session, job)

    assert finished.status == orchestrator.BLOCKED
    assert finished.error_code == "ENGINES_NOT_READY"
    assert db_session.query(ResearchReport).count() == 0


def test_no_report_when_scanner_stale(db_session, analyzed_universe):
    btc = analyzed_universe["assets"]["BTCUSDT"]
    service._latest_scanner_result(db_session, btc.id, "1h").freshness_status = "STALE"
    db_session.commit()

    request, job, _ = orchestrator.create_request(db_session, btc, "1h")
    finished = orchestrator.run_job(db_session, job)
    assert finished.status == orchestrator.BLOCKED
    assert db_session.query(ResearchReport).count() == 0


def test_job_fails_clearly_without_provider(db_session, btc_asset, monkeypatch):
    monkeypatch.setenv("PIMS_LLM_BASE_URL", "")
    monkeypatch.setenv("PIMS_LLM_API_KEY", "")
    monkeypatch.setenv("PIMS_LLM_MODEL", "")
    from app.config.settings import get_settings

    get_settings.cache_clear()

    request, job, _ = orchestrator.create_request(db_session, btc_asset, "1h")
    finished = orchestrator.run_job(db_session, job)

    assert finished.status == orchestrator.FAILED
    assert finished.error_code == "PROVIDER_NOT_CONFIGURED"
    assert finished.attempts == 0  # no LLM call was attempted


def test_duplicate_request_deduplicated(db_session, btc_asset):
    first_request, first_job, first_action = orchestrator.create_request(
        db_session, btc_asset, "1h"
    )
    second_request, second_job, second_action = orchestrator.create_request(
        db_session, btc_asset, "1h"
    )

    assert first_action == "CREATED"
    assert second_action == "DEDUPLICATED"
    assert first_request.id == second_request.id
    assert first_job.id == second_job.id
    assert db_session.query(ResearchRequest).count() == 1


def test_cooldown_expiry_allows_new_request(db_session, btc_asset):
    request, job, _ = orchestrator.create_request(db_session, btc_asset, "1h")
    request.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db_session.commit()

    _, _, action = orchestrator.create_request(db_session, btc_asset, "1h")
    assert action == "CREATED"
    assert db_session.query(ResearchRequest).count() == 2


def test_completed_report_is_reused_not_regenerated(db_session, analyzed_universe, monkeypatch):
    """A completed report for the same fingerprint must be returned, not re-run."""
    btc = analyzed_universe["assets"]["BTCUSDT"]
    request, job, _ = orchestrator.create_request(db_session, btc, "1h")

    # Simulate an earlier completed job with the same fingerprint.
    report = ResearchReport(
        request_id=request.id,
        research_type="INSTRUMENT",
        title="cached",
        report_content={"executive_summary": "cached"},
        ai_provider="openai-compatible",
        model_identifier="test-model",
        execution_status="COMPLETED",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(report)
    db_session.flush()

    cached_job = ResearchJob(
        request_id=request.id,
        status=orchestrator.COMPLETED,
        context_fingerprint=job.context_fingerprint,
        attempts=1,
        max_retries=0,
        report_id=report.id,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
    db_session.add(cached_job)
    job.status = orchestrator.CANCELLED
    db_session.commit()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("provider must not be called when a cached report exists")

    monkeypatch.setattr(
        orchestrator.OpenAICompatibleProvider, "from_settings", staticmethod(fail_if_called)
    )

    finished = orchestrator.run_job(db_session, job)
    assert finished.status == orchestrator.COMPLETED
    assert finished.report_id == report.id
    assert db_session.query(ResearchReport).count() == 1


def test_bounded_retries_then_failed(db_session, btc_asset, monkeypatch):
    from app.config.settings import get_settings

    monkeypatch.setenv("PIMS_LLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("PIMS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("PIMS_LLM_MODEL", "test-model")
    get_settings.cache_clear()

    calls = {"count": 0}

    def always_fails(self, system, user):
        calls["count"] += 1
        raise RuntimeError("provider down")

    from app.ai.providers.openai_compat import OpenAICompatibleProvider

    monkeypatch.setattr(OpenAICompatibleProvider, "generate", always_fails)
    monkeypatch.setattr(orchestrator, "BACKOFF_SECONDS", 0.0)

    request, job, _ = orchestrator.create_request(db_session, btc_asset, "1h")
    finished = orchestrator.run_job(db_session, job)

    assert finished.status == orchestrator.FAILED
    assert finished.error_code == "PROVIDER_HTTP_ERROR"
    assert calls["count"] == job.max_retries + 1  # bounded, never infinite
    assert db_session.query(ResearchReport).count() == 0


def test_invalid_output_fails_after_retries(db_session, btc_asset, monkeypatch):
    from app.config.settings import get_settings

    monkeypatch.setenv("PIMS_LLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("PIMS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("PIMS_LLM_MODEL", "test-model")
    get_settings.cache_clear()

    from app.ai.providers.openai_compat import OpenAICompatibleProvider

    monkeypatch.setattr(
        OpenAICompatibleProvider, "generate", lambda self, system, user: "not json at all"
    )

    request, job, _ = orchestrator.create_request(db_session, btc_asset, "1h")
    finished = orchestrator.run_job(db_session, job)

    assert finished.status == orchestrator.FAILED
    assert finished.error_code == "OUTPUT_INVALID"
    assert db_session.query(ResearchReport).count() == 0


def test_valid_output_persists_report(db_session, btc_asset, monkeypatch):
    import json

    from app.ai.providers.openai_compat import OpenAICompatibleProvider
    from app.ai.report_generator.generator import REQUIRED_SECTIONS
    from app.config.settings import get_settings

    monkeypatch.setenv("PIMS_LLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("PIMS_LLM_API_KEY", "test-key")
    monkeypatch.setenv("PIMS_LLM_MODEL", "test-model")
    get_settings.cache_clear()

    body = {section: f"value for {section}" for section in REQUIRED_SECTIONS}
    monkeypatch.setattr(
        OpenAICompatibleProvider, "generate", lambda self, system, user: json.dumps(body)
    )

    request, job, _ = orchestrator.create_request(db_session, btc_asset, "1h")
    finished = orchestrator.run_job(db_session, job)

    assert finished.status == orchestrator.COMPLETED
    assert finished.report_id is not None
    report = db_session.get(ResearchReport, finished.report_id)
    assert set(REQUIRED_SECTIONS).issubset(report.report_content.keys())
    assert report.execution_status == "COMPLETED"


def test_scheduled_trigger_disabled_by_default():
    from app.config.settings import get_settings

    settings = get_settings()
    assert settings.research_schedule_enabled is False
    assert settings.scanner_schedule_enabled is False
    assert settings.research_scanner_trigger_enabled is False
