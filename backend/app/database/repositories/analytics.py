"""Analytics persistence repository (schema-spec §7.1–7.4).

Read/write helpers only; transaction boundaries belong to the service.
"""
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import (
    AllocationResult,
    AnalyticsRun,
    PerformanceResult,
    RiskResult,
)


def add_run(
    session: Session,
    *,
    engine_type: str,
    portfolio_id: uuid.UUID,
    observation_start: datetime | None = None,
    observation_end: datetime | None = None,
    input_metadata: dict | None = None,
    calculation_version: str = "1.0.0",
) -> AnalyticsRun:
    now = datetime.now(tz=UTC)
    run = AnalyticsRun(
        engine_type=engine_type,
        asset_id=None,
        timeframe=None,
        observation_start=observation_start,
        observation_end=observation_end,
        calculation_version=calculation_version,
        input_metadata=input_metadata or {},
        execution_status="COMPLETED",
        started_at=now,
        completed_at=now,
        error_message=None,
    )
    session.add(run)
    session.flush()
    return run


def add_performance_result(
    session: Session,
    *,
    analytics_run_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    period_start: datetime,
    period_end: datetime,
    total_return: Decimal | None,
    daily_return: Decimal | None,
    realized_pnl: Decimal | None,
    unrealized_pnl: Decimal | None,
    cagr: Decimal | None,
    reporting_currency: str,
    methodology: str,
    result_metadata: dict | None = None,
) -> PerformanceResult:
    row = PerformanceResult(
        analytics_run_id=analytics_run_id,
        portfolio_id=portfolio_id,
        period_start=period_start,
        period_end=period_end,
        total_return=total_return,
        daily_return=daily_return,
        realized_pnl=realized_pnl,
        unrealized_pnl=unrealized_pnl,
        cagr=cagr,
        reporting_currency=reporting_currency,
        methodology=methodology,
        result_metadata=result_metadata or {},
    )
    session.add(row)
    session.flush()
    return row


def add_risk_result(
    session: Session,
    *,
    analytics_run_id: uuid.UUID,
    observation_period: str | None,
    volatility: Decimal | None,
    max_drawdown: Decimal | None,
    value_at_risk: Decimal | None,
    confidence_level: Decimal | None,
    risk_classification: str | None,
    result_metadata: dict | None = None,
) -> RiskResult:
    row = RiskResult(
        analytics_run_id=analytics_run_id,
        observation_period=observation_period,
        volatility=volatility,
        max_drawdown=max_drawdown,
        value_at_risk=value_at_risk,
        confidence_level=confidence_level,
        risk_classification=risk_classification,
        result_metadata=result_metadata or {},
    )
    session.add(row)
    session.flush()
    return row


def add_allocation_result(
    session: Session,
    *,
    analytics_run_id: uuid.UUID,
    portfolio_id: uuid.UUID,
    allocation_type: str,
    allocation_key: str,
    market_value: Decimal | None,
    allocation_percentage: Decimal | None,
    reporting_currency: str,
    result_metadata: dict | None = None,
) -> AllocationResult:
    row = AllocationResult(
        analytics_run_id=analytics_run_id,
        portfolio_id=portfolio_id,
        allocation_type=allocation_type,
        allocation_key=allocation_key,
        market_value=market_value,
        allocation_percentage=allocation_percentage,
        reporting_currency=reporting_currency,
        result_metadata=result_metadata or {},
    )
    session.add(row)
    session.flush()
    return row


def get_run(session: Session, run_id: uuid.UUID) -> AnalyticsRun | None:
    return session.get(AnalyticsRun, run_id)


def _portfolio_filter(portfolio_id: uuid.UUID):
    return AnalyticsRun.input_metadata["portfolio_id"].astext == str(portfolio_id)


def list_runs_page(
    session: Session,
    portfolio_id: uuid.UUID,
    limit: int = 50,
    cursor_run: AnalyticsRun | None = None,
) -> tuple[list[AnalyticsRun], bool]:
    """Runs for one portfolio, newest first; cursor is a run id."""
    query = (
        select(AnalyticsRun)
        .where(_portfolio_filter(portfolio_id))
        .order_by(AnalyticsRun.started_at.desc(), AnalyticsRun.id.desc())
        .limit(limit + 1)
    )
    if cursor_run is not None:
        query = query.where(
            (AnalyticsRun.started_at, AnalyticsRun.id)
            < (cursor_run.started_at, cursor_run.id)
        )
    rows = list(session.scalars(query))
    has_more = len(rows) > limit
    return rows[:limit], has_more


def get_results_for_run(
    session: Session, run_id: uuid.UUID
) -> tuple[list[PerformanceResult], list[RiskResult], list[AllocationResult]]:
    perf = list(
        session.scalars(select(PerformanceResult).where(PerformanceResult.analytics_run_id == run_id))
    )
    risk = list(
        session.scalars(select(RiskResult).where(RiskResult.analytics_run_id == run_id))
    )
    alloc = list(
        session.scalars(select(AllocationResult).where(AllocationResult.analytics_run_id == run_id))
    )
    return perf, risk, alloc
