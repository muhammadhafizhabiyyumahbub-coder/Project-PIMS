"Analytics engine run records and deterministic engine outputs."
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class AnalyticsRun(Base):
    __tablename__ = "analytics_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    engine_type: Mapped[str] = mapped_column(String(50), nullable=False)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assets.id"), nullable=True
    )
    timeframe: Mapped[str | None] = mapped_column(String(20), nullable=True)
    observation_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    observation_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    calculation_version: Mapped[str] = mapped_column(String(50), nullable=False)
    input_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    execution_status: Mapped[str] = mapped_column(String(30), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)


class TechnicalResult(Base):
    __tablename__ = "technical_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analytics_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analytics_runs.id"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assets.id"), nullable=False)
    timeframe: Mapped[str] = mapped_column(String(20), nullable=False)
    indicator_name: Mapped[str] = mapped_column(String(50), nullable=False)
    indicator_parameters: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    observation_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    indicator_values: Mapped[dict] = mapped_column(JSONB, nullable=False)
    calculation_status: Mapped[str] = mapped_column(String(30), nullable=False)


class MarketRegimeResult(Base):
    __tablename__ = "market_regime_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analytics_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analytics_runs.id"), nullable=False
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assets.id"), nullable=True
    )
    timeframe: Mapped[str] = mapped_column(String(20), nullable=False)
    trend_regime: Mapped[str] = mapped_column(String(30), nullable=False)
    volatility_regime: Mapped[str] = mapped_column(String(30), nullable=False)
    momentum_regime: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    observation_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    result_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class RiskResult(Base):
    __tablename__ = "risk_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analytics_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analytics_runs.id"), nullable=False
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assets.id"), nullable=True
    )
    observation_period: Mapped[str | None] = mapped_column(String(30), nullable=True)
    volatility: Mapped[float | None] = mapped_column(Numeric(20, 10), nullable=True)
    max_drawdown: Mapped[float | None] = mapped_column(Numeric(20, 10), nullable=True)
    value_at_risk: Mapped[float | None] = mapped_column(Numeric(30, 12), nullable=True)
    confidence_level: Mapped[float | None] = mapped_column(Numeric(10, 8), nullable=True)
    risk_classification: Mapped[str | None] = mapped_column(String(30), nullable=True)
    result_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class PerformanceResult(Base):
    __tablename__ = "performance_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analytics_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analytics_runs.id"), nullable=False
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id"), nullable=False
    )
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    total_return: Mapped[float | None] = mapped_column(
        Numeric(20, 10), nullable=True
    )
    daily_return: Mapped[float | None] = mapped_column(Numeric(20, 10), nullable=True)
    realized_pnl: Mapped[float | None] = mapped_column(
        Numeric(30, 12), nullable=True
    )
    unrealized_pnl: Mapped[float | None] = mapped_column(
        Numeric(30, 12), nullable=True
    )
    cagr: Mapped[float | None] = mapped_column(Numeric(20, 10), nullable=True)
    reporting_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    methodology: Mapped[str | None] = mapped_column(String(50), nullable=True)
    result_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AllocationResult(Base):
    __tablename__ = "allocation_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analytics_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analytics_runs.id"), nullable=False
    )
    portfolio_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("portfolios.id"), nullable=False
    )
    allocation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    allocation_key: Mapped[str] = mapped_column(String(150), nullable=False)
    market_value: Mapped[float | None] = mapped_column(Numeric(30, 12), nullable=True)
    allocation_percentage: Mapped[float | None] = mapped_column(
        Numeric(20, 10), nullable=True
    )
    reporting_currency: Mapped[str] = mapped_column(String(10), nullable=False)
    result_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class CorrelationResult(Base):
    """Pairwise correlation output (schema-spec §7.5)."""

    __tablename__ = "correlation_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analytics_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analytics_runs.id"), nullable=False
    )
    asset_a_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id"), nullable=False
    )
    asset_b_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id"), nullable=False
    )
    correlation_value: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    observation_count: Mapped[int | None] = mapped_column(nullable=True)
    observation_period: Mapped[str | None] = mapped_column(String(30), nullable=True)
    calculation_method: Mapped[str | None] = mapped_column(String(50), nullable=True)
    result_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class BacktestMetrics(Base):
    """Deterministic backtest run metrics (M4 Backtesting Engine, Phase 1).

    Long format: one row per metric so the metric set can grow without
    schema changes. Persisted under an AnalyticsRun (engine_type=BACKTESTING).
    """

    __tablename__ = "backtest_metrics"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analytics_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analytics_runs.id"), nullable=False
    )
    metric: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float | None] = mapped_column(Numeric(30, 12), nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class FactorResult(Base):
    """Per-asset market-based factor scores (M4 Factor Engine, Phase 1).

    One row per (run, asset): the raw factor values, their normalized (z)
    forms, and the composite score. Persisted under an AnalyticsRun
    (engine_type=FACTOR). Fundamental-based factors are out of scope here
    (owner deferred) — this table holds market-based factors only.
    """

    __tablename__ = "factor_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analytics_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analytics_runs.id"), nullable=False
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id"), nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(60), nullable=False)
    raw_factors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    z_factors: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    composite_score: Mapped[float | None] = mapped_column(Numeric(20, 10), nullable=True)
    excluded: Mapped[bool] = mapped_column(default=False, nullable=False)
    result_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AttributionResult(Base):
    """Asset-level attribution results (M4 Attribution Engine, Phase 1).

    One row per (run, asset): contribution to portfolio return and active
    contribution vs benchmark. Persisted under an AnalyticsRun
    (engine_type=ATTRIBUTION). Phase 1 is asset-level only; Brinson-Fachler
    (Phase 2) is gated behind owner approval.
    """

    __tablename__ = "attribution_results"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    analytics_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("analytics_runs.id"), nullable=False, index=True
    )
    asset_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("assets.id"), nullable=True
    )
    symbol: Mapped[str] = mapped_column(String(60), nullable=False)
    contribution: Mapped[float | None] = mapped_column(Numeric(30, 12), nullable=True)
    active_contribution: Mapped[float | None] = mapped_column(Numeric(30, 12), nullable=True)
    result_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
