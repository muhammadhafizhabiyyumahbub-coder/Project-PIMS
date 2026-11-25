"""Scenario Analysis Engine — M4, Phase 1 (sensitivity + historical stress).

Implements the approved Phase-1 methodology from
`docs/management/m4-gap-proposals/04-scenario.md`:

- SENSITIVITY: perturb one asset by `shock`. Portfolio direct impact =
  w_target * shock; each other holding j contributes a correlated impact
  = w_j * rho_{j,target} * shock (rho from the M1 correlation engine).
  Total portfolio impact = direct + sum(correlated).
- HISTORICAL: replay each holding's return over [period_start, period_end]
  onto current weights: R_stress = sum_j w_j * r_{j,T}.

Deterministic, no network. No holdings / no candles -> INSUFFICIENT_DATA.
HYPOTHETICAL shocks are Phase 2 and gated: requesting one returns
INVALID_CONFIG ("requires owner approval").

No formula beyond the proposal baseline is invented here.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import AnalyticsRun, Asset, Holding, ScenarioResult
from app.engines.correlation.engine import build_series, compute_pair
from app.engines.runner import load_candles

CALC_VERSION = "scenario.phase1.v1"

MIN_CANDLES = 2


def _period_return(
    session: Session,
    asset_id,
    period_start: datetime,
    period_end: datetime,
    timeframe: str,
    limit: int,
) -> Optional[float]:
    """Simple return over the period from CLOSED candles. None if insufficient."""
    candles = load_candles(session, asset_id, timeframe, limit=limit)
    closed = [
        c for c in (candles or [])
        if c.get("candle_status") == "CLOSED"
        and c["close_time"] >= period_start
        and c["close_time"] <= period_end
    ]
    if len(closed) < MIN_CANDLES:
        return None
    closed.sort(key=lambda c: c["close_time"])
    start, end = closed[0]["close"], closed[-1]["close"]
    if not start:
        return None
    return (end - start) / start


def _rho(session: Session, asset_a, asset_b, timeframe: str, limit: int) -> Optional[float]:
    """Pearson correlation between two assets via the M1 correlation engine."""
    a = build_series(session, asset_a, timeframe, limit=limit)
    b = build_series(session, asset_b, timeframe, limit=limit)
    return compute_pair(a, b, ret_method="SIMPLE", timeframe=timeframe)["correlation"]


def _persist_run(
    session: Session,
    portfolio_id: str,
    scenario_type: str,
    timeframe: str,
    status: str,
    metadata: dict,
    scenario_rows: Optional[list[dict]] = None,
) -> dict:
    now = datetime.now(timezone.utc)
    run = AnalyticsRun(
        engine_type="SCENARIO",
        asset_id=None,
        timeframe=timeframe,
        calculation_version=CALC_VERSION,
        input_metadata={"portfolio_id": portfolio_id, "scenario_type": scenario_type, **metadata},
        execution_status=status,
        started_at=now,
        completed_at=now,
        error_message=metadata.get("reason") if status != "COMPLETED" else None,
    )
    session.add(run)
    session.flush()

    for row in scenario_rows or []:
        session.add(ScenarioResult(
            analytics_run_id=run.id,
            asset_id=row.get("asset_id"),
            symbol=row.get("symbol"),
            scenario_type=scenario_type,
            shock=row.get("shock"),
            impact=row.get("impact"),
            correlated_impact=row.get("correlated_impact"),
            result_metadata=row.get("result_metadata"),
        ))
    session.flush()
    return run


def _weights_and_assets(session: Session, portfolio_id: uuid.UUID):
    """Current holdings with invested-value weights + loaded Asset rows."""
    holdings = session.scalars(select(Holding).filter_by(portfolio_id=portfolio_id)).all()
    if not holdings:
        return None
    total = sum(
        float(h.quantity or 0) * float(h.average_cost or 0) for h in holdings
    )
    if total <= 0:
        return None
    out = []
    for h in holdings:
        invested = float(h.quantity or 0) * float(h.average_cost or 0)
        asset = session.get(Asset, h.asset_id)
        out.append((h, asset, invested / total))
    return out


def run_scenario_for_portfolio(
    session: Session,
    portfolio_id: str,
    scenario_type: str,
    params: dict,
    timeframe: str = "1d",
    limit: int = 300,
) -> dict:
    """Run a Phase-1 scenario for a portfolio and persist it.

    Returns {run_id, portfolio_id, scenario_type, portfolio_impact,
    per_asset, status}. Caller commits/rolls back.
    """
    if scenario_type not in ("SENSITIVITY", "HISTORICAL"):
        run = _persist_run(
            session, portfolio_id, scenario_type, timeframe, "INVALID_CONFIG",
            {"reason": "hypothetical shock requires owner approval "
                       "(magnitude/probability)"},
        )
        return {
            "run_id": str(run.id), "portfolio_id": portfolio_id,
            "scenario_type": scenario_type, "portfolio_impact": None,
            "per_asset": [], "status": "INVALID_CONFIG",
            "reason": run.error_message,
        }

    pid = uuid.UUID(portfolio_id)
    weighted = _weights_and_assets(session, pid)
    if weighted is None:
        run = _persist_run(
            session, portfolio_id, scenario_type, timeframe, "INSUFFICIENT_DATA",
            {"reason": "portfolio has no holdings or zero invested value"},
        )
        return {
            "run_id": str(run.id), "portfolio_id": portfolio_id,
            "scenario_type": scenario_type, "portfolio_impact": None,
            "per_asset": [], "status": "INSUFFICIENT_DATA",
        }

    per_asset: list[dict] = []
    portfolio_impact = 0.0
    any_valid = False
    observation = {}

    if scenario_type == "SENSITIVITY":
        target_asset_id = params.get("asset_id")
        shock = params.get("shock")
        if not target_asset_id or shock is None:
            run = _persist_run(
                session, portfolio_id, scenario_type, timeframe, "INVALID_CONFIG",
                {"reason": "SENSITIVITY requires asset_id and shock"},
            )
            return {
                "run_id": str(run.id), "portfolio_id": portfolio_id,
                "scenario_type": scenario_type, "portfolio_impact": None,
                "per_asset": [], "status": "INVALID_CONFIG",
            }
        shock = float(shock)
        target = session.get(Asset, uuid.UUID(str(target_asset_id)))
        if target is None or not any(str(a.id) == str(target_asset_id) for _h, a, _w in weighted):
            run = _persist_run(
                session, portfolio_id, scenario_type, timeframe, "INVALID_CONFIG",
                {"reason": "asset_id is not a holding in portfolio"},
            )
            return {
                "run_id": str(run.id), "portfolio_id": portfolio_id,
                "scenario_type": scenario_type, "portfolio_impact": None,
                "per_asset": [], "status": "INVALID_CONFIG",
            }

        for _h, asset, w in weighted:
            if asset is None:
                continue
            if str(asset.id) == str(target_asset_id):
                impact = w * shock
                correlated = 0.0
                any_valid = True
            else:
                rho = _rho(session, asset, target, timeframe, limit) if target else None
                if rho is None:
                    per_asset.append({
                        "asset_id": asset.id, "symbol": asset.symbol,
                        "shock": None, "impact": None, "correlated_impact": None,
                        "result_metadata": {"weight": w, "reason": "no correlation with target"},
                    })
                    continue
                impact = 0.0
                correlated = w * rho * shock
                any_valid = True
            portfolio_impact += impact + correlated
            per_asset.append({
                "asset_id": asset.id, "symbol": asset.symbol,
                "shock": shock, "impact": impact, "correlated_impact": correlated,
                "result_metadata": {"weight": w},
            })

    else:  # HISTORICAL
        period_start = params.get("period_start")
        period_end = params.get("period_end")
        if not period_start or not period_end:
            run = _persist_run(
                session, portfolio_id, scenario_type, timeframe, "INVALID_CONFIG",
                {"reason": "HISTORICAL requires period_start and period_end"},
            )
            return {
                "run_id": str(run.id), "portfolio_id": portfolio_id,
                "scenario_type": scenario_type, "portfolio_impact": None,
                "per_asset": [], "status": "INVALID_CONFIG",
            }
        observation = {
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
        }
        for _h, asset, w in weighted:
            if asset is None:
                continue
            r = _period_return(session, asset.id, period_start, period_end, timeframe, limit)
            if r is None:
                per_asset.append({
                    "asset_id": asset.id, "symbol": asset.symbol,
                    "shock": None, "impact": None, "correlated_impact": None,
                    "result_metadata": {"weight": w, "reason": "insufficient candle data"},
                })
                continue
            any_valid = True
            impact = w * r
            portfolio_impact += impact
            per_asset.append({
                "asset_id": asset.id, "symbol": asset.symbol,
                "shock": r, "impact": impact, "correlated_impact": None,
                "result_metadata": {"weight": w},
            })

    if not any_valid:
        run = _persist_run(
            session, portfolio_id, scenario_type, timeframe, "INSUFFICIENT_DATA",
            {"reason": "no holdings with usable candle data", **observation},
        )
        return {
            "run_id": str(run.id), "portfolio_id": portfolio_id,
            "scenario_type": scenario_type, "portfolio_impact": None,
            "per_asset": per_asset, "status": "INSUFFICIENT_DATA",
        }

    run = _persist_run(
        session, portfolio_id, scenario_type, timeframe, "COMPLETED",
        {"limit": limit, **observation}, scenario_rows=per_asset,
    )

    return {
        "run_id": str(run.id),
        "portfolio_id": portfolio_id,
        "scenario_type": scenario_type,
        "portfolio_impact": portfolio_impact,
        "per_asset": [
            {
                "symbol": p["symbol"], "shock": p["shock"],
                "impact": p["impact"], "correlated_impact": p["correlated_impact"],
            }
            for p in per_asset
        ],
        "status": "COMPLETED",
    }
