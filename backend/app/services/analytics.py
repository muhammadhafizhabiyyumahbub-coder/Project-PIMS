"""Analytics persistence service: compute + store.

Creates one AnalyticsRun and writes results to the corresponding tables.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.database.models import (
    AllocationResult,
    AnalyticsRun,
    PerformanceResult,
    RiskResult,
)
from app.database.repositories import analytics as repo
from app.database.repositories import portfolio as portfolio_repo
from app.engines.allocation.allocation import allocation_for_portfolio, serialize_weight
from app.engines.portfolio.performance import (
    PerformanceResult as EnginePerformanceResult,
    performance_for_portfolio,
    serialize_money as _serialize_money,
    serialize_return,
)
from app.engines.risk.portfolio_risk import (
    RiskResult as EngineRiskResult,
    risk_for_portfolio,
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    # fallback: try str
    try:
        return str(value)
    except Exception:
        return None


def persist_analytics(
    session: Session,
    portfolio_id: uuid.UUID,
    analysis_type: str,
    *,
    window_days: int | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> tuple[AnalyticsRun, list[PerformanceResult] | list[RiskResult] | list[AllocationResult]]:
    """Compute the requested analytics and persist run + results.

    Returns the run row and a list of result rows (one for performance/risk,
    multiple for allocation).
    """
    portfolio = portfolio_repo.get_portfolio(session, portfolio_id)
    if portfolio is None:
        raise ValueError(f"portfolio {portfolio_id} not found")

    # Run computation
    if analysis_type == "performance":
        result: EnginePerformanceResult = performance_for_portfolio(
            session, portfolio_id, start=start, end=end
        )
        if result.return_status == "UNAVAILABLE" and (
            result.period_start is None or result.period_end is None
        ):
            # period_start/period_end are NOT NULL: without a real period there is
            # nothing honest to store, so refuse instead of inventing boundaries.
            raise ValueError(
                "Performance result is UNAVAILABLE and has no period boundaries; "
                "cannot persist without a valid period."
            )

        run = repo.add_run(
            session,
            engine_type="PERFORMANCE",
            portfolio_id=portfolio_id,
            observation_start=result.period_start,
            observation_end=result.period_end,
            input_metadata=_json_safe({
                "portfolio_id": str(portfolio_id),
                "analysis_type": "performance",
                "request_start": start.isoformat() if start else None,
                "request_end": end.isoformat() if end else None,
                "return_status": result.return_status,
                "sub_period_count": result.sub_period_count,
            }),
        )

        metadata = _json_safe({
            "return_status": result.return_status,
            "twr_reason": result.twr_reason,
            "simple_return": serialize_return(result.simple_return),
            "simple_return_reason": result.simple_return_reason,
            "sub_period_count": result.sub_period_count,
            "period_days": result.period_days,
            "cagr_reason": result.cagr_reason,
        })

        res = repo.add_performance_result(
            session,
            analytics_run_id=run.id,
            portfolio_id=portfolio_id,
            period_start=result.period_start,
            period_end=result.period_end,
            total_return=result.twr,
            daily_return=None,
            realized_pnl=Decimal(result.realized_pnl) if result.realized_pnl is not None else None,
            unrealized_pnl=Decimal(result.unrealized_pnl) if result.unrealized_pnl is not None else None,
            cagr=result.cagr,
            reporting_currency=result.reporting_currency,
            methodology="time_weighted_return",
            result_metadata=metadata,
        )
        return run, [res]

    elif analysis_type == "risk":
        if window_days is None:
            window_days = 90
        if window_days < 30 or window_days > 3650:
            raise ValueError("window must be between 30 and 3650")

        result: EngineRiskResult = risk_for_portfolio(session, portfolio_id, window_days)

        run = repo.add_run(
            session,
            engine_type="RISK",
            portfolio_id=portfolio_id,
            observation_start=result.observation_start,
            observation_end=result.observation_end,
            input_metadata=_json_safe({
                "portfolio_id": str(portfolio_id),
                "analysis_type": "risk",
                "window_days": window_days,
                "data_status": result.data_status,
                "data_status_reason": result.data_status_reason,
                "holdings_count": result.holdings_count,
            }),
        )

        # Owner decision 7.12#3: methodology metadata required for later
        # reinterpretation. sharpe/sortino/cvar have no column in the existing
        # risk_results table (risk_results columns are frozen), so they live here.
        metadata = _json_safe({
            "portfolio_id": str(portfolio_id),
            "method": result.method,
            "weight_base": result.weight_base,
            "risk_free_rate": serialize_return(result.risk_free_rate),
            "annualization": result.annualization,
            "annualization_factor": result.annualization_factor,
            "observation_count": result.return_count,
            "holdings_count": result.holdings_count,
            "price_source": result.price_source,
            "data_status": result.data_status,
            "data_status_reason": result.data_status_reason,
            "observation_start": (
                result.observation_start.isoformat() if result.observation_start else None
            ),
            "observation_end": (
                result.observation_end.isoformat() if result.observation_end else None
            ),
            "metrics": {k: serialize_return(v) for k, v in result.metrics.items()},
            "metric_reasons": result.metric_reasons,
        })

        obs_period = f"{window_days}d"
        res = repo.add_risk_result(
            session,
            analytics_run_id=run.id,
            observation_period=obs_period,
            volatility=result.metrics.get("volatility"),
            max_drawdown=result.metrics.get("max_drawdown"),
            value_at_risk=result.metrics.get("var_95"),
            confidence_level=(
                Decimal("0.95") if result.metrics.get("var_95") is not None else None
            ),
            risk_classification=None,
            result_metadata=metadata,
        )
        return run, [res]

    elif analysis_type == "allocation":
        result = allocation_for_portfolio(session, portfolio_id)

        run = repo.add_run(
            session,
            engine_type="ALLOCATION",
            portfolio_id=portfolio_id,
            observation_start=result.valuation_timestamp,
            observation_end=result.valuation_timestamp,
            input_metadata=_json_safe({
                "portfolio_id": str(portfolio_id),
                "analysis_type": "allocation",
                "data_status": result.data_status,
                "data_status_reason": result.data_status_reason,
                "weight_base": result.weight_base,
                "coverage": result.coverage,
                "concentration": _json_safe(result.concentration),
                "total_value": serialize_return(result.total_value),
                "cash_value": serialize_return(result.cash_value),
                "invested_value": serialize_return(result.invested_value),
                "sector_status": result.categories["sector"]["status"],
                "sector_reason": result.categories["sector"]["reason"],
            }),
        )

        # Shared metadata for every row
        base_metadata = _json_safe({
            "weight_base": result.weight_base,
            "coverage": result.coverage,
            "data_status": result.data_status,
            "data_status_reason": result.data_status_reason,
            "valuation_status": result.valuation_timestamp.isoformat(),
            "total_value": serialize_return(result.total_value),
            "cash_value": serialize_return(result.cash_value),
            "invested_value": serialize_return(result.invested_value),
        })

        rows = []
        # Asset class slices
        for s in result.categories["asset_class"]:
            rows.append(repo.add_allocation_result(
                session,
                analytics_run_id=run.id,
                portfolio_id=portfolio_id,
                allocation_type="ASSET_CLASS",
                allocation_key=s.name[:150],
                market_value=s.market_value,
                allocation_percentage=s.weight,
                reporting_currency=result.reporting_currency,
                result_metadata=base_metadata,
            ))
        # Market slices
        for s in result.categories["market"]:
            rows.append(repo.add_allocation_result(
                session,
                analytics_run_id=run.id,
                portfolio_id=portfolio_id,
                allocation_type="MARKET",
                allocation_key=s.name[:150],
                market_value=s.market_value,
                allocation_percentage=s.weight,
                reporting_currency=result.reporting_currency,
                result_metadata=base_metadata,
            ))
        # Currency slices
        for s in result.categories["currency"]:
            rows.append(repo.add_allocation_result(
                session,
                analytics_run_id=run.id,
                portfolio_id=portfolio_id,
                allocation_type="CURRENCY",
                allocation_key=s.name[:150],
                market_value=s.market_value,
                allocation_percentage=s.weight,
                reporting_currency=result.reporting_currency,
                result_metadata=base_metadata,
            ))
        # Individual asset slices
        for p in result.categories["individual_asset"]:
            rows.append(repo.add_allocation_result(
                session,
                analytics_run_id=run.id,
                portfolio_id=portfolio_id,
                allocation_type="ASSET",
                allocation_key=p.symbol[:150],
                market_value=p.market_value,
                allocation_percentage=p.weight,
                reporting_currency=result.reporting_currency,
                result_metadata=base_metadata,
            ))
        # Cash slice
        cash_info = result.categories["cash"]
        rows.append(repo.add_allocation_result(
            session,
            analytics_run_id=run.id,
            portfolio_id=portfolio_id,
            allocation_type="CASH",
            allocation_key=cash_info["currency"][:150],
            market_value=cash_info["value"],
            allocation_percentage=cash_info["weight"],
            reporting_currency=result.reporting_currency,
            result_metadata=base_metadata,
        ))

        # Sector is unavailable — record in run input_metadata only

        return run, rows

    else:
        raise ValueError(f"unknown analysis_type: {analysis_type}")


# Read helpers for API serialization

def _run_payload(run: AnalyticsRun) -> dict:
    meta = run.input_metadata or {}
    return {
        "id": str(run.id),
        "engine_type": run.engine_type,
        "portfolio_id": meta.get("portfolio_id"),
        "observation_start": run.observation_start.isoformat() if run.observation_start else None,
        "observation_end": run.observation_end.isoformat() if run.observation_end else None,
        "calculation_version": run.calculation_version,
        "execution_status": run.execution_status,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "input_metadata": meta,
        "error_message": run.error_message,
    }


def _performance_payload(row: PerformanceResult) -> dict:
    return {
        "id": str(row.id),
        "analytics_run_id": str(row.analytics_run_id),
        "portfolio_id": str(row.portfolio_id),
        "period_start": row.period_start.isoformat(),
        "period_end": row.period_end.isoformat(),
        "total_return": serialize_return(row.total_return) if row.total_return is not None else None,
        "daily_return": serialize_return(row.daily_return) if row.daily_return is not None else None,
        "realized_pnl": _serialize_money(row.realized_pnl) if row.realized_pnl is not None else None,
        "unrealized_pnl": _serialize_money(row.unrealized_pnl) if row.unrealized_pnl is not None else None,
        "cagr": serialize_return(row.cagr) if row.cagr is not None else None,
        "reporting_currency": row.reporting_currency,
        "methodology": row.methodology,
        "result_metadata": row.result_metadata or {},
    }


def _risk_payload(row: RiskResult) -> dict:
    md = row.result_metadata or {}
    return {
        "id": str(row.id),
        "analytics_run_id": str(row.analytics_run_id),
        "portfolio_id": md.get("portfolio_id"),
        "observation_period": row.observation_period,
        "volatility": serialize_return(row.volatility) if row.volatility is not None else None,
        "max_drawdown": serialize_return(row.max_drawdown) if row.max_drawdown is not None else None,
        "value_at_risk": serialize_return(row.value_at_risk) if row.value_at_risk is not None else None,
        "confidence_level": serialize_return(row.confidence_level) if row.confidence_level is not None else None,
        "risk_classification": row.risk_classification,
        "result_metadata": md,
    }


def _allocation_payload(row: AllocationResult) -> dict:
    return {
        "id": str(row.id),
        "analytics_run_id": str(row.analytics_run_id),
        "portfolio_id": str(row.portfolio_id),
        "allocation_type": row.allocation_type,
        "allocation_key": row.allocation_key,
        "market_value": _serialize_money(row.market_value) if row.market_value is not None else None,
        "allocation_percentage": serialize_weight(row.allocation_percentage) if row.allocation_percentage is not None else None,
        "reporting_currency": row.reporting_currency,
        "result_metadata": row.result_metadata or {},
    }