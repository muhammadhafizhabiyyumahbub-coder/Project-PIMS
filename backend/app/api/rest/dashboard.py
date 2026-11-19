"""Dashboard endpoints per api-spec §14 (aggregation only, read-only).

Shape assumptions (api-spec §14.3 shows an example but not an exact schema):

- `/overview` reuses the Stage A valuation engine (no second methodology);
  `allocation` groups the same valuation positions by asset_type and computes
  percentages from `invested_value`, mirroring allocation-engine-spec dimensions.
- `portfolio.total_return` / `daily_pnl` are NOT returned: the stored
  performance result is a separate run, and recomputing them here would use a
  second methodology (api-spec §14.3 forbids that). They stay null.
- `/market-overview` reuses the market session/freshness derivation from
  `app.api.rest.markets` so both endpoints can never disagree.
- `/activity` lists transactions; `/scanner-highlights` reuses the exact
  `_opportunity` payload; `/research-highlights` lists completed reports.
- Money/quantity leave as decimal strings (api-spec §5.3). Missing = null with a
  reason, never 0.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.envelope import error_response, success_response
from app.api.rest.markets import _data_availability, _session
from app.core.db import get_db
from app.data.validation.freshness import freshness_status
from app.database.models import (
    AnalyticsRun,
    Asset,
    Market,
    Portfolio,
    ResearchReport,
    ResearchRequest,
    RiskResult,
    ScannerResult,
    Transaction,
)
from app.engines.portfolio.valuation import value_portfolio
from app.engines.runner import load_candles
from app.qualification.service import evaluate_engine_readiness, qualification_summary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

SCANNER_LIMIT_DEFAULT = 5
RESEARCH_LIMIT_DEFAULT = 5


def _decimal_str(value: Decimal | float | None) -> str | None:
    """api-spec §5.3: money/quantity as decimal strings, never JSON floats."""
    if value is None:
        return None
    return format(Decimal(str(value)).normalize(), "f")


def _opportunity(
    db: Session, result: ScannerResult, asset: Asset, market: Market | None, timeframe: str
) -> dict:
    candles = load_candles(db, asset.id, timeframe, limit=30)
    last_close = float(candles[-1]["close"]) if candles else None
    change = None
    if len(candles) >= 25:
        prev = float(candles[-25]["close"])
        change = round((last_close / prev - 1) * 100, 4) if prev else None

    readiness = evaluate_engine_readiness(db, asset.id, timeframe)
    summary = qualification_summary(readiness)
    regime = readiness.get("MARKET_REGIME", {})
    risk = readiness.get("RISK", {})

    return {
        "scanner_result_id": str(result.id),
        "instrument": {"symbol": asset.symbol, "name": asset.name, "asset_type": asset.asset_type},
        "market": market.code if market else None,
        "current_price": _decimal_str(last_close),
        "daily_change_pct": change,
        "quote_currency": asset.quote_currency,
        "scanner_score": _decimal_str(result.score),
        "scanner_rank": result.rank,
        "market_regime": regime.get("detail", {}).get("trend_regime"),
        "risk_status": risk.get("detail", {}).get("classification"),
        "approval_status": summary["status"],
        "passed_by": summary["passed_by"],
        "engine_readiness": {
            engine: {"state": info["state"], "label": info["label"]}
            for engine, info in readiness.items()
        },
        "updated_at": result.data_timestamp.isoformat() if result.data_timestamp else None,
        # Display freshness is evaluated at request time, not frozen at scan time.
        "data_status": freshness_status(
            result.data_timestamp, datetime.now(timezone.utc), result.timeframe
        ),
    }


def _latest_scanner_highlights(db: Session, limit: int) -> list[dict]:
    """Latest scanner result per asset (same rule as /instrument-opportunities)."""
    seen: set = set()
    rows: list[dict] = []
    for result in db.query(ScannerResult).order_by(ScannerResult.created_at.desc()).all():
        if result.asset_id in seen:
            continue
        seen.add(result.asset_id)
        asset = db.get(Asset, result.asset_id)
        if asset is None:
            continue
        market_row = db.get(Market, asset.market_id) if asset.market_id else None
        rows.append(_opportunity(db, result, asset, market_row, result.timeframe))
        if len(rows) >= limit:
            break
    return rows


def _research_payload(db: Session, report: ResearchReport) -> dict:
    request = db.get(ResearchRequest, report.request_id)
    asset = db.get(Asset, request.asset_id) if request and request.asset_id else None
    return {
        "report_id": str(report.id),
        "request_id": str(report.request_id),
        "title": report.title,
        "research_type": report.research_type,
        "request_summary": report.request_summary,
        "asset": {"id": str(asset.id), "symbol": asset.symbol, "name": asset.name} if asset else None,
        "provider": report.ai_provider,
        "model": report.model_identifier,
        "observation_start": report.observation_start.isoformat() if report.observation_start else None,
        "observation_end": report.observation_end.isoformat() if report.observation_end else None,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
    }


def _allocation(valuation, db: Session) -> list[dict]:
    """Group valuation positions by asset_type; percentages from invested_value."""
    invested = valuation.invested_value
    buckets: dict[str, Decimal] = {}
    for position in valuation.positions:
        asset = db.get(Asset, position.asset_id)
        key = asset.asset_type if asset else "UNKNOWN"
        if position.market_value is not None:
            buckets[key] = buckets.get(key, Decimal("0")) + position.market_value
    rows = []
    for key in sorted(buckets):
        value = buckets[key]
        pct = (value / invested * 100) if invested else None
        rows.append(
            {
                "allocation_type": "ASSET_CLASS",
                "allocation_key": key,
                "market_value": _decimal_str(value),
                "allocation_percentage": _decimal_str(pct),
                "reporting_currency": valuation.reporting_currency,
            }
        )
    return rows


def _risk_summary(db: Session, portfolio_id) -> dict | None:
    """Latest COMPLETED risk run; null (not {}) when portfolio has never been analyzed.

    analytics_runs has no portfolio_id column; the portfolio link lives in
    input_metadata.portfolio_id (Stage Q/R persistence). RiskResult columns are
    volatility / max_drawdown / value_at_risk / risk_classification (schema-spec
    §7.3 subset actually implemented).
    """
    run = (
        db.query(AnalyticsRun)
        .filter(
            AnalyticsRun.engine_type == "RISK",
            AnalyticsRun.execution_status == "COMPLETED",
            AnalyticsRun.input_metadata["portfolio_id"].astext == str(portfolio_id),
        )
        .order_by(AnalyticsRun.completed_at.desc())
        .first()
    )
    if run is None:
        return None
    result = db.query(RiskResult).filter_by(analytics_run_id=run.id).first()
    if result is None:
        return None
    return {
        "analytics_run_id": str(run.id),
        "observation_period": result.observation_period,
        "volatility": _decimal_str(result.volatility),
        "max_drawdown": _decimal_str(result.max_drawdown),
        "value_at_risk": _decimal_str(result.value_at_risk),
        "confidence_level": _decimal_str(result.confidence_level),
        "risk_classification": result.risk_classification,
        "calculation_time": run.completed_at.isoformat() if run.completed_at else None,
    }


@router.get("/overview")
def dashboard_overview(
    portfolio_id: str | None = Query(None, description="Optional portfolio; omit for aggregate"),
    time_range: str | None = Query(None, description="Reserved; not part of stored aggregation"),
    base_currency: str | None = Query(None, description="Reserved; valuations use reporting currency"),
    scanner_limit: int = Query(SCANNER_LIMIT_DEFAULT, ge=1, le=50),
    research_limit: int = Query(RESEARCH_LIMIT_DEFAULT, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Main dashboard aggregate (api-spec §14.1, §14.3)."""
    portfolio = None
    if portfolio_id:
        try:
            pid = uuid.UUID(portfolio_id)
        except (ValueError, AttributeError):
            return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
        portfolio = db.get(Portfolio, pid)
        if portfolio is None:
            return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)

    portfolio_summary = None
    allocation: list[dict] = []
    risk_summary = None
    if portfolio is not None:
        valuation = value_portfolio(db, portfolio.id)
        portfolio_summary = {
            "portfolio_id": str(portfolio.id),
            "name": portfolio.name,
            "status": portfolio.status,
            "total_value": _decimal_str(valuation.total_value),
            "invested_value": _decimal_str(valuation.invested_value),
            "cash_value": _decimal_str(valuation.cash_value),
            "realized_pnl": _decimal_str(valuation.realized_pnl),
            "unrealized_pnl": _decimal_str(valuation.unrealized_pnl),
            "currency": valuation.reporting_currency,
            "valuation_status": valuation.valuation_status,
            "valued_at": valuation.valued_at.isoformat(),
            # Not recomputed here: separate performance run owns these (api-spec §14.3).
            "total_return": None,
            "daily_pnl": None,
        }
        allocation = _allocation(valuation, db)
        risk_summary = _risk_summary(db, portfolio.id)

    return success_response(
        {
            "portfolio": portfolio_summary,
            "allocation": allocation,
            "risk_summary": risk_summary,
            "scanner_highlights": _latest_scanner_highlights(db, scanner_limit),
            "research_highlights": [
                _research_payload(db, report)
                for report in db.query(ResearchReport)
                .filter_by(execution_status="COMPLETED")
                .order_by(ResearchReport.generated_at.desc().nullslast())
                .limit(research_limit)
                .all()
            ],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )


@router.get("/market-overview")
def dashboard_market_overview(db: Session = Depends(get_db)):
    """Per-market session, stored-data freshness, and top 24h movers."""
    markets = list(db.scalars(select(Market).where(Market.is_active.is_(True)).order_by(Market.code)))
    rows = []
    for market in markets:
        assets = list(
            db.scalars(
                select(Asset)
                .where(Asset.market_id == market.id, Asset.is_active.is_(True))
                .order_by(Asset.symbol)
            )
        )
        movers = []
        for asset in assets:
            candles = load_candles(db, asset.id, "1h", limit=30)
            if len(candles) < 25:
                continue
            last = float(candles[-1]["close"])
            prev = float(candles[-25]["close"])
            if not prev:
                continue
            movers.append(
                {
                    "symbol": asset.symbol,
                    "change_pct": round((last / prev - 1) * 100, 4),
                    "last_price": _decimal_str(last),
                }
            )
        movers.sort(key=lambda row: row["change_pct"], reverse=True)
        rows.append(
            {
                "market": market.code,
                "market_type": market.market_type,
                "session": _session(market),
                "data_availability": _data_availability(db, market.id),
                "instruments_count": len(assets),
                "top_movers": movers[:5],
            }
        )
    return success_response(rows, meta={"count": len(rows)})


@router.get("/activity")
def dashboard_activity(
    portfolio_id: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Recent transactions, newest first (api-spec §14.1)."""
    query = db.query(Transaction).order_by(Transaction.transaction_date.desc())
    if portfolio_id:
        try:
            pid = uuid.UUID(portfolio_id)
        except (ValueError, AttributeError):
            return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
        if db.get(Portfolio, pid) is None:
            return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
        query = query.filter(Transaction.portfolio_id == pid)

    rows = []
    for txn in query.limit(limit).all():
        asset = db.get(Asset, txn.asset_id) if txn.asset_id else None
        rows.append(
            {
                "transaction_id": str(txn.id),
                "portfolio_id": str(txn.portfolio_id),
                "asset": {"id": str(asset.id), "symbol": asset.symbol} if asset else None,
                "transaction_type": txn.transaction_type,
                "quantity": _decimal_str(txn.quantity),
                "price": _decimal_str(txn.price),
                "gross_amount": _decimal_str(txn.gross_amount),
                "fee_amount": _decimal_str(txn.fee_amount),
                "currency": txn.currency,
                "transaction_date": txn.transaction_date.isoformat(),
            }
        )
    return success_response(rows, meta={"count": len(rows)})


@router.get("/scanner-highlights")
def dashboard_scanner_highlights(
    market: str | None = Query(None),
    qualification: str | None = Query(None),
    limit: int = Query(SCANNER_LIMIT_DEFAULT, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Top scanner results per asset, optionally filtered by market/qualification."""
    rows = _latest_scanner_highlights(db, limit * 10)
    if market:
        rows = [r for r in rows if (r["market"] or "").upper() == market.upper()]
    if qualification:
        rows = [r for r in rows if r["approval_status"].upper() == qualification.upper()]
    rows.sort(key=lambda r: Decimal(r["scanner_score"]) if r["scanner_score"] else Decimal("-1"), reverse=True)
    return success_response(rows[:limit], meta={"count": len(rows[:limit]), "limit": limit})


@router.get("/research-highlights")
def dashboard_research_highlights(
    limit: int = Query(RESEARCH_LIMIT_DEFAULT, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Latest completed research reports (api-spec §14.1)."""
    reports = (
        db.query(ResearchReport)
        .filter_by(execution_status="COMPLETED")
        .order_by(ResearchReport.generated_at.desc().nullslast())
        .limit(limit)
        .all()
    )
    return success_response([_research_payload(db, r) for r in reports], meta={"count": len(reports)})


@router.get("/instrument-opportunities")
def instrument_opportunities(
    market: str | None = None,
    qualification: str | None = None,
    sort: str = "scanner_score",
    db: Session = Depends(get_db),
):
    """Latest scanner result per asset, joined with qualification readiness."""
    rows = _latest_scanner_highlights(db, 10_000)

    if market:
        rows = [r for r in rows if (r["market"] or "").upper() == market.upper()]
    if qualification:
        rows = [r for r in rows if r["approval_status"].upper() == qualification.upper()]

    sort_keys = {
        "scanner_score": lambda r: Decimal(r["scanner_score"]) if r["scanner_score"] else Decimal("-1"),
        "daily_change": lambda r: r["daily_change_pct"] if r["daily_change_pct"] is not None else -1e9,
        "symbol": lambda r: r["instrument"]["symbol"],
        "updated_at": lambda r: r["updated_at"] or "",
        "market": lambda r: r["market"] or "",
    }
    rows.sort(key=sort_keys.get(sort, sort_keys["scanner_score"]), reverse=sort != "symbol")

    return success_response(rows, meta={"count": len(rows), "sort": sort})