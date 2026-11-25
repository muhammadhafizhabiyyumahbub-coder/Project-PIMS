"""Attribution Engine — M4, Phase 1 (asset-level attribution, deterministic).

Implements the approved Phase-1 methodology from
`docs/management/m4-gap-proposals/03-attribution.md`:

- Asset-level attribution: contribution of each holding = weight_i * return_i
- Weight = holding's invested value / total invested value (at period start)
- Return = period return from CLOSED candles
- Active contribution vs benchmark (if benchmark_asset_id provided):
  active_contribution_i = weight_i * return_i - w_b * r_b
  where w_b = benchmark weight (1.0 for single-asset benchmark), r_b = benchmark return
- Conservation: sum(contribution) == R_portfolio (within float tolerance)

Phase 2 (Brinson-Fachler) is out of scope and gated behind owner approval.

No network: reads stored candles + holdings only.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from app.database.models import (
    AnalyticsRun,
    Asset,
    Holding,
    MarketCandle,
)
from app.engines.runner import load_candles

CALC_VERSION = "attribution.phase1.v1"

# Minimum candles needed to compute a return
MIN_CANDLES = 2


@dataclass
class AttributionConfig:
    """Configuration for attribution run."""
    portfolio_id: str
    benchmark_asset_id: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    timeframe: str = "1d"
    limit: int = 300


def _simple_return(start_price: float, end_price: float) -> Optional[float]:
    """Simple return: (end - start) / start. None if start is 0 or None."""
    if start_price is None or end_price is None or start_price == 0:
        return None
    return (end_price - start_price) / start_price


def _get_period_return(
    session: Session,
    asset_id: str,
    period_start: datetime,
    period_end: datetime,
    timeframe: str = "1d",
    limit: int = 300,
) -> Optional[float]:
    """Get the simple return for an asset over the specified period.

    Uses CLOSED candles only. Returns None if insufficient data.
    """
    # Load candles for the asset
    candles = load_candles(session, asset_id, timeframe, limit=limit)

    if not candles or len(candles) < MIN_CANDLES:
        return None

    # Filter to CLOSED candles within the period
    closed_candles = [
        c for c in candles
        if c.get("candle_status") == "CLOSED"
        and c["close_time"] >= period_start
        and c["close_time"] <= period_end
    ]

    if len(closed_candles) < MIN_CANDLES:
        return None

    # Sort by time
    closed_candles.sort(key=lambda c: c["close_time"])

    start_price = closed_candles[0]["close"]
    end_price = closed_candles[-1]["close"]

    return _simple_return(start_price, end_price)


def _get_invested_value(session: Session, portfolio_id: str, period_start: datetime) -> Optional[float]:
    """Get the total invested value of the portfolio at period start.

    Uses the latest available holding valuation before or at period_start.
    """
    # Get holdings
    holdings = session.query(Holding).filter_by(portfolio_id=portfolio_id).all()
    if not holdings:
        return None

    total_invested = 0.0
    for holding in holdings:
        if holding.quantity and holding.average_cost:
            # Invested value = quantity * average_cost
            total_invested += float(holding.quantity) * float(holding.average_cost)

    return total_invested if total_invested > 0 else None


def run_attribution_for_portfolio(
    session: Session,
    portfolio_id: str,
    benchmark_asset_id: Optional[str] = None,
    period_start: Optional[datetime] = None,
    period_end: Optional[datetime] = None,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict:
    """Compute asset-level attribution for a portfolio and persist results.

    Returns a structured result dict with contributions and status.
    Persists to `analytics_runs` (engine_type=ATTRIBUTION) + `attribution_results`.
    """

    # Default period_end to now if not provided
    if period_end is None:
        period_end = datetime.now(timezone.utc)

    # Default period_start to 30 days ago if not provided
    if period_start is None:
        from datetime import timedelta
        period_start = period_end - timedelta(days=30)

    # Get holdings
    holdings = session.query(Holding).filter_by(portfolio_id=portfolio_id).all()
    if not holdings:
        return _persist_empty_run(
            session, portfolio_id, "ATTRIBUTION",
            "INSUFFICIENT_DATA", "portfolio has no holdings",
            period_start, period_end, timeframe
        )

    # Get total invested value at period start
    total_invested = _get_invested_value(session, portfolio_id, period_start)
    if total_invested is None:
        return _persist_empty_run(
            session, portfolio_id, "ATTRIBUTION",
            "INSUFFICIENT_DATA", "cannot determine total invested value",
            period_start, period_end, timeframe
        )

    # Get benchmark return if benchmark provided
    benchmark_return = None
    if benchmark_asset_id:
        benchmark_return = _get_period_return(
            session, benchmark_asset_id, period_start, period_end, timeframe, limit
        )

    # Compute contributions for each holding
    breakdown = []
    total_contribution = 0.0

    for holding in holdings:
        if not holding.quantity or holding.quantity <= 0:
            continue

        asset = session.get(Asset, holding.asset_id)
        if not asset:
            continue

        # Weight = holding's invested value / total invested value
        invested_value = float(holding.quantity) * float(holding.average_cost or 0)
        weight = invested_value / total_invested if total_invested > 0 else 0.0

        # Return for this asset
        asset_return = _get_period_return(
            session, holding.asset_id, period_start, period_end, timeframe, limit
        )

        if asset_return is None:
            contribution = None
            active_contribution = None
        else:
            contribution = weight * asset_return
            total_contribution += contribution

            # Active contribution vs benchmark
            if benchmark_return is not None:
                # For single-asset benchmark, w_b = 1.0
                # Active = w_i * r_i - w_b * r_b = contribution - r_b
                active_contribution = contribution - benchmark_return
            else:
                active_contribution = None

        breakdown.append({
            "asset_id": str(holding.asset_id),
            "symbol": asset.symbol,
            "weight": weight,
            "invested_value": invested_value,
            "return": asset_return,
            "contribution": contribution,
            "active_contribution": active_contribution,
        })

    # Check if we have any valid contributions
    valid_contributions = [b for b in breakdown if b["contribution"] is not None]
    if not valid_contributions:
        return _persist_empty_run(
            session, portfolio_id, "ATTRIBUTION",
            "INSUFFICIENT_DATA", "no holdings with valid return data",
            period_start, period_end, timeframe
        )

    # Portfolio return = sum of contributions
    portfolio_return = sum(b["contribution"] for b in valid_contributions)

    # Active portfolio return vs benchmark
    active_return = None
    if benchmark_return is not None:
        active_return = portfolio_return - benchmark_return

    # Persist to DB
    now = datetime.now(timezone.utc)
    run = AnalyticsRun(
        engine_type="ATTRIBUTION",
        asset_id=None,
        timeframe=timeframe,
        observation_start=period_start,
        observation_end=period_end,
        calculation_version=CALC_VERSION,
        input_metadata={
            "portfolio_id": str(portfolio_id),
            "benchmark_asset_id": benchmark_asset_id,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "total_invested": total_invested,
            "holding_count": len(holdings),
        },
        execution_status="COMPLETED",
        started_at=now,
        completed_at=now,
    )
    session.add(run)
    session.flush()

    # Persist each asset's attribution result
    from app.database.models import AttributionResult

    for item in breakdown:
        session.add(AttributionResult(
            analytics_run_id=run.id,
            asset_id=item["asset_id"],
            symbol=item["symbol"],
            contribution=item["contribution"],
            active_contribution=item["active_contribution"],
            result_metadata={
                "weight": item["weight"],
                "invested_value": item["invested_value"],
                "return": item["return"],
            },
        ))

    session.flush()

    return {
        "run_id": str(run.id),
        "portfolio_id": str(portfolio_id),
        "total_return": portfolio_return,
        "active_return": active_return,
        "benchmark_return": benchmark_return,
        "calculation_status": "COMPLETED",
        "calculation_version": CALC_VERSION,
        "breakdown": [
            {
                "symbol": b["symbol"],
                "weight": b["weight"],
                "return": b["return"],
                "contribution": b["contribution"],
                "active_contribution": b["active_contribution"],
            }
            for b in breakdown
        ],
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "timeframe": timeframe,
    }


def _persist_empty_run(
    session: Session,
    portfolio_id: str,
    engine_type: str,
    status: str,
    reason: str,
    period_start: datetime,
    period_end: datetime,
    timeframe: str,
) -> dict:
    """Persist an empty/failed run and return result dict."""
    now = datetime.now(timezone.utc)
    run = AnalyticsRun(
        engine_type=engine_type,
        asset_id=None,
        timeframe=timeframe,
        observation_start=period_start,
        observation_end=period_end,
        calculation_version=CALC_VERSION,
        input_metadata={
            "portfolio_id": str(portfolio_id),
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "reason": reason,
        },
        execution_status=status,
        started_at=now,
        completed_at=now,
        error_message=reason if status != "COMPLETED" else None,
    )
    session.add(run)
    session.flush()

    return {
        "run_id": str(run.id),
        "portfolio_id": str(portfolio_id),
        "total_return": None,
        "active_return": None,
        "benchmark_return": None,
        "calculation_status": status,
        "calculation_version": CALC_VERSION,
        "breakdown": [],
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "timeframe": timeframe,
    }