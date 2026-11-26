"""Analytics API endpoints matching api-spec.md §15 (top-level /api/v1/analytics)."""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.envelope import error_response, success_response
from app.core.db import get_db
from app.database.repositories import portfolio as portfolio_repo
from app.engines.portfolio.performance import performance_for_portfolio
from app.engines.risk.portfolio_risk import risk_for_portfolio
from app.engines.allocation.allocation import allocation_for_portfolio
from app.engines.technical.engine import compute as compute_technical
from app.engines.market_regime.engine import classify as classify_regime
from app.engines.runner import load_candles
from app.engines.correlation.engine import run_correlation_for_portfolio
from app.engines.attribution.engine import run_attribution_for_portfolio
from app.engines.backtesting.engine import (
    run_backtest_for_assets,
    InsufficientData,
)
from app.engines.factor.engine import run_factor_for_universe, FactorConfig
from app.engines.fundamental.engine import run_fundamental_for_universe
from app.engines.sentiment.engine import run_sentiment_for_universe
from app.engines.scenario.engine import run_scenario_for_portfolio

router = APIRouter(prefix="/analytics", tags=["Analytics"])

def parse_uuid(value: str):
    try:
        return uuid.UUID(value)
    except (ValueError, AttributeError):
        return None

def _serialize_decimal(value: Optional[Decimal]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    return format(Decimal(str(value)).normalize(), "f")

def _serialize_return(value: Optional[float | Decimal]) -> Optional[str]:
    if value is None:
        return None
    return format(Decimal(str(value)).normalize(), "f")

def _serialize_coverage(coverage: dict) -> dict:
    """Serialize Decimal values in coverage dict."""
    result = {}
    for k, v in coverage.items():
        if k in ("coverage_percentage", "position_coverage_percentage", "value_known_percentage"):
            result[k] = _serialize_decimal(v) if v is not None else None
        elif k == "unpriced_positions":
            result[k] = [
                {
                    "asset_id": str(p.asset_id),
                    "symbol": p.symbol,
                    "quantity": _serialize_decimal(p.quantity),
                    "cost_basis": _serialize_decimal(p.cost_basis),
                }
                for p in v
            ]
        else:
            result[k] = v
    return result

def _serialize_concentration(concentration: dict) -> dict:
    """Serialize Decimal values in concentration dict."""
    result = {}
    for k, v in concentration.items():
        if k in ("largest_holding_weight", "top_3_weight", "top_5_weight", "top_10_weight"):
            result[k] = _serialize_return(v) if v is not None else None
        else:
            result[k] = v
    return result

def _get_portfolio_or_404(db: Session, portfolio_id: str):
    pid = parse_uuid(portfolio_id)
    if pid is None:
        return error_response("VALIDATION_ERROR", "invalid portfolio_id format", 422)
    portfolio = portfolio_repo.get_portfolio(db, pid)
    if portfolio is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)
    return pid, portfolio

def _get_asset_or_404(db: Session, asset_id: str):
    aid = parse_uuid(asset_id)
    if aid is None:
        return error_response("VALIDATION_ERROR", "invalid asset_id format", 422)
    from app.database.models import Asset
    asset = db.get(Asset, aid)
    if asset is None or not asset.is_active:
        return error_response("NOT_FOUND", f"asset {asset_id} not found", 404)
    return aid, asset

@router.get("/performance")
def get_analytics_performance(
    portfolio_id: str = Query(..., description="Portfolio UUID"),
    start: Optional[str] = Query(None, description="ISO-8601 start timestamp"),
    end: Optional[str] = Query(None, description="ISO-8601 end timestamp"),
    benchmark_id: Optional[str] = Query(None, description="Benchmark asset UUID"),
    db: Session = Depends(get_db),
):
    """Get portfolio performance (TWR, simple return, CAGR). Delegates to performance engine."""
    pid = parse_uuid(portfolio_id)
    if pid is None:
        return error_response("VALIDATION_ERROR", "invalid portfolio_id format", 422)
    portfolio = portfolio_repo.get_portfolio(db, pid)
    if portfolio is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)

    start_dt = None
    end_dt = None
    if start:
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
        except ValueError:
            return error_response("VALIDATION_ERROR", "invalid start date format", 422)
    if end:
        try:
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))
        except ValueError:
            return error_response("VALIDATION_ERROR", "invalid end date format", 422)

    try:
        result = performance_for_portfolio(db, pid, start=start_dt, end=end_dt)
    except Exception as exc:
        return error_response("SERVER_ERROR", str(exc), 500)

    return success_response({
        "portfolio_id": str(pid),
        "period_start": result.period_start.isoformat() if result.period_start else None,
        "period_end": result.period_end.isoformat() if result.period_end else None,
        "twr": _serialize_return(result.twr) if result.twr is not None else None,
        "simple_return": _serialize_return(result.simple_return) if result.simple_return is not None else None,
        "cagr": _serialize_return(result.cagr) if result.cagr is not None else None,
        "realized_pnl": _serialize_decimal(result.realized_pnl) if result.realized_pnl is not None else None,
        "unrealized_pnl": _serialize_decimal(result.unrealized_pnl) if result.unrealized_pnl is not None else None,
        "return_status": result.return_status,
        "twr_reason": result.twr_reason,
        "simple_return_reason": result.simple_return_reason,
        "cagr_reason": result.cagr_reason,
        "sub_period_count": result.sub_period_count,
        "period_days": result.period_days,
        "reporting_currency": result.reporting_currency,
    })

@router.get("/risk")
def get_analytics_risk(
    portfolio_id: str = Query(..., description="Portfolio UUID"),
    window_days: int = Query(90, ge=30, le=3650, description="Lookback window in days"),
    db: Session = Depends(get_db),
):
    """Get portfolio risk metrics (volatility, drawdown, VaR). Delegates to risk engine."""
    pid = parse_uuid(portfolio_id)
    if pid is None:
        return error_response("VALIDATION_ERROR", "invalid portfolio_id format", 422)
    portfolio = portfolio_repo.get_portfolio(db, pid)
    if portfolio is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)

    try:
        result = risk_for_portfolio(db, pid, window_days)
    except Exception as exc:
        return error_response("SERVER_ERROR", str(exc), 500)

    metrics = {k: _serialize_return(v) for k, v in result.metrics.items()}
    return success_response({
        "portfolio_id": str(pid),
        "observation_start": result.observation_start.isoformat() if result.observation_start else None,
        "observation_end": result.observation_end.isoformat() if result.observation_end else None,
        "window_days": window_days,
        "method": result.method,
        "weight_base": result.weight_base,
        "risk_free_rate": _serialize_return(result.risk_free_rate),
        "annualization": result.annualization,
        "annualization_factor": result.annualization_factor,
        "observation_count": result.return_count,
        "holdings_count": result.holdings_count,
        "price_source": result.price_source,
        "data_status": result.data_status,
        "data_status_reason": result.data_status_reason,
        "metrics": metrics,
        "metric_reasons": result.metric_reasons,
    })

@router.get("/allocation")
def get_analytics_allocation(
    portfolio_id: str = Query(..., description="Portfolio UUID"),
    db: Session = Depends(get_db),
):
    """Get portfolio allocation breakdown (asset class, market, currency, asset, cash)."""
    pid = parse_uuid(portfolio_id)
    if pid is None:
        return error_response("VALIDATION_ERROR", "invalid portfolio_id format", 422)
    portfolio = portfolio_repo.get_portfolio(db, pid)
    if portfolio is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)

    try:
        result = allocation_for_portfolio(db, pid)
    except Exception as exc:
        return error_response("SERVER_ERROR", str(exc), 500)

    # Build slices
    slices = {}
    for cat_key in ["asset_class", "market", "currency", "individual_asset", "sector"]:
        items = result.categories.get(cat_key, [])
        if not isinstance(items, list) or len(items) == 0:
            slices[cat_key] = []
            continue
        
        # Check for dict or object
        if isinstance(items[0], dict):
            # allocation engine returns dicts for these
            slices[cat_key] = [
                {
                    "name": s.get("name", str(s)),
                    "market_value": _serialize_decimal(s.get("market_value")),
                    "allocation_percentage": _serialize_return(s.get("weight")),
                }
                for s in items
            ]
        else:
            # Objects with .name, .market_value, .weight
            slices[cat_key] = [
                {
                    "name": getattr(s, "name", str(s)),
                    "market_value": _serialize_decimal(getattr(s, "market_value", None)),
                    "allocation_percentage": _serialize_return(getattr(s, "weight", None)),
                }
                for s in items
            ]
    cash = result.categories["cash"]
    slices["cash"] = {
        "currency": cash["currency"],
        "market_value": _serialize_decimal(cash["value"]),
        "allocation_percentage": _serialize_return(cash["weight"]),
    }

    return success_response({
        "portfolio_id": str(pid),
        "valuation_timestamp": result.valuation_timestamp.isoformat(),
        "reporting_currency": result.reporting_currency,
        "total_value": _serialize_decimal(result.total_value),
        "cash_value": _serialize_decimal(result.cash_value),
        "invested_value": _serialize_decimal(result.invested_value),
        "weight_base": result.weight_base,
        "coverage": _serialize_coverage(result.coverage),
        "concentration": _serialize_concentration(result.concentration),
        "data_status": result.data_status,
        "data_status_reason": result.data_status_reason,
        "slices": slices,
    })

@router.get("/technical")
def get_analytics_technical(
    asset_id: str = Query(..., description="Asset UUID"),
    timeframe: str = Query("1h", description="Candle timeframe"),
    limit: int = Query(200, ge=60, le=500, description="Number of candles"),
    db: Session = Depends(get_db),
):
    """Get technical indicators for an asset. Delegates to technical engine."""
    aid = parse_uuid(asset_id)
    if aid is None:
        return error_response("VALIDATION_ERROR", "invalid asset_id format", 422)
    from app.database.models import Asset
    asset = db.get(Asset, aid)
    if asset is None or not asset.is_active:
        return error_response("NOT_FOUND", f"asset {asset_id} not found", 404)

    try:
        from app.engines.runner import resolve_provider_id
        provider_id = resolve_provider_id(db, asset)
        candles = load_candles(db, aid, timeframe, limit=limit, provider_id=provider_id)
        if not candles:
            return error_response("NOT_FOUND", f"no candles for asset {asset_id} timeframe {timeframe}", 404)
    except Exception as exc:
        return error_response("SERVER_ERROR", str(exc), 500)

    # Use the last candle's close_time as observation_time
    observation_time = candles[-1]["close_time"]
    result = compute_technical(candles, observation_time)

    if result.get("calculation_status") == "FAILED":
        return success_response({
            "asset_id": str(aid),
            "symbol": asset.symbol,
            "timeframe": timeframe,
            "calculation_status": "FAILED",
            "error": result.get("error"),
        })

    return success_response({
        "asset_id": str(aid),
        "symbol": asset.symbol,
        "timeframe": timeframe,
        "calculation_status": "COMPLETED",
        "observation_time": observation_time.isoformat(),
        "parameters": result.get("parameters"),
        "values": {
            "sma_20": _serialize_return(result["values"]["sma_20"]),
            "sma_50": _serialize_return(result["values"]["sma_50"]),
            "rsi_14": _serialize_return(result["values"]["rsi_14"]),
            "atr_14": _serialize_return(result["values"]["atr_14"]),
            "macd": {
                "macd": _serialize_return(result["values"]["macd"]["macd"]),
                "signal": _serialize_return(result["values"]["macd"]["signal"]),
                "histogram": _serialize_return(result["values"]["macd"]["histogram"]),
            },
            "last_close": _serialize_return(result["values"]["last_close"]),
        },
    })

@router.get("/market-regime")
def get_analytics_market_regime(
    asset_id: str = Query(..., description="Asset UUID"),
    timeframe: str = Query("1h", description="Candle timeframe"),
    limit: int = Query(200, ge=60, le=500, description="Number of candles"),
    db: Session = Depends(get_db),
):
    """Get market regime classification for an asset. Delegates to market regime engine."""
    aid = parse_uuid(asset_id)
    if aid is None:
        return error_response("VALIDATION_ERROR", "invalid asset_id format", 422)
    from app.database.models import Asset
    asset = db.get(Asset, aid)
    if asset is None or not asset.is_active:
        return error_response("NOT_FOUND", f"asset {asset_id} not found", 404)

    try:
        from app.engines.runner import resolve_provider_id
        provider_id = resolve_provider_id(db, asset)
        candles = load_candles(db, aid, timeframe, limit=limit, provider_id=provider_id)
        if not candles:
            return error_response("NOT_FOUND", f"no candles for asset {asset_id} timeframe {timeframe}", 404)
    except Exception as exc:
        return error_response("SERVER_ERROR", str(exc), 500)

    # Use the last candle's close_time
    observation_time = candles[-1]["close_time"]
    closes = [float(c["close"]) for c in candles]
    highs = [float(c["high"]) for c in candles]
    lows = [float(c["low"]) for c in candles]
    
    # Reuse technical indicators for regime classification
    from app.engines.technical.engine import sma, rsi, atr
    sma_20 = sma(closes, 20)
    sma_50 = sma(closes, 50)
    rsi_14 = rsi(closes)
    atr_14 = atr(highs, lows, closes)
    last_close = closes[-1]

    if any(v is None for v in [sma_20, sma_50, rsi_14, atr_14]):
        return success_response({
            "asset_id": str(aid),
            "symbol": asset.symbol,
            "timeframe": timeframe,
            "calculation_status": "FAILED",
            "error": "insufficient data for regime classification",
        })

    regime = classify_regime(sma_20, sma_50, last_close, rsi_14, atr_14)

    return success_response({
        "asset_id": str(aid),
        "symbol": asset.symbol,
        "timeframe": timeframe,
        "observation_time": observation_time.isoformat(),
        "trend_regime": regime["trend_regime"],
        "volatility_regime": regime["volatility_regime"],
        "momentum_regime": regime["momentum_regime"],
        "confidence_score": _serialize_return(regime["confidence_score"]),
        "atr_pct": _serialize_return(regime["atr_pct"]),
        "calculation_status": "COMPLETED",
    })

@router.get("/correlation")
def get_analytics_correlation(
    portfolio_id: str = Query(..., description="Portfolio UUID"),
    timeframe: str = Query("1d", description="Candle timeframe for return series"),
    return_method: str = Query("SIMPLE", description="Return method: SIMPLE or LOG"),
    rolling_window: int = Query(0, description="Rolling window size (0 = off)"),
    limit: int = Query(300, description="Max candles per asset"),
    db: Session = Depends(get_db),
):
    """Correlation matrix for portfolio holdings (correlation-engine-spec).

    Deterministic: reads stored candles, computes pairwise Pearson (spec §4.2),
    persists to correlation_results + analytics_runs. No network/provider calls.
    """
    pid = parse_uuid(portfolio_id)
    if pid is None:
        return error_response("VALIDATION_ERROR", "invalid portfolio_id format", 422)
    portfolio = portfolio_repo.get_portfolio(db, pid)
    if portfolio is None:
        return error_response("NOT_FOUND", f"portfolio {portfolio_id} not found", 404)

    holdings = portfolio_repo.list_holdings(db, pid)
    if not holdings:
        return success_response({
            "portfolio_id": str(pid),
            "correlation_matrix": [],
            "calculation_status": "INSUFFICIENT_DATA",
            "reason": "portfolio has no holdings",
            "pairs_computed": 0,
            "series_used": 0,
        })

    try:
        result = run_correlation_for_portfolio(
            db, pid, holdings,
            timeframe=timeframe,
            ret_method=return_method,
            rolling_window=rolling_window,
            limit=limit,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return success_response(result)


@router.post("/backtest")
def run_analytics_backtest(
    payload: "BacktestRequest",
    db: Session = Depends(get_db),
):
    """Deterministic Phase-1 backtest (BUY_HOLD / STATIC_WEIGHT) over stored
    candles. Persists to analytics_runs (BACKTESTING) + backtest_metrics.

    No network / no signal — Phase 2 rule-based strategies are gated behind
    owner approval (see docs/management/m4-gap-proposals/01-backtesting.md).
    """
    from app.database.models import Asset

    assets = []
    for symbol in payload.symbols:
        a = db.query(Asset).filter_by(symbol=symbol, is_active=True).first()
        if a is None:
            return error_response(
                "VALIDATION_ERROR", f"active asset {symbol!r} not found", 422
            )
        assets.append(a)
    if not assets:
        return error_response("VALIDATION_ERROR", "no symbols supplied", 422)

    weights = payload.weights or {s: 1.0 / len(payload.symbols) for s in payload.symbols}

    try:
        result = run_backtest_for_assets(
            db,
            assets,
            weights=weights,
            strategy=payload.strategy,
            timeframe=payload.timeframe,
            limit=payload.limit,
            rebalance_every=payload.rebalance_every,
            fee_bps=payload.fee_bps,
            slippage_bps=payload.slippage_bps,
        )
        db.commit()
    except InsufficientData as exc:
        return error_response("INSUFFICIENT_DATA", str(exc), 422)
    except ValueError as exc:
        return error_response("INVALID_CONFIG", str(exc), 422)
    except Exception as exc:
        db.rollback()
        return error_response("SERVER_ERROR", str(exc), 500)

    return success_response(result)


class AttributionRequest(BaseModel):
    portfolio_id: str = Field(..., description="Portfolio UUID")
    benchmark_asset_id: Optional[str] = Field(None, description="Benchmark asset UUID")
    period_start: Optional[datetime] = Field(None, description="Start of period (ISO-8601)")
    period_end: Optional[datetime] = Field(None, description="End of period (ISO-8601)")
    timeframe: str = Field("1d", description="Candle timeframe")


@router.post("/attribution")
def run_analytics_attribution(
    payload: AttributionRequest,
    db: Session = Depends(get_db),
):
    """Asset-level attribution for a portfolio (Phase 1).

    Persists to analytics_runs (ATTRIBUTION) + attribution_results.
    Deterministic; no network.
    """
    pid = parse_uuid(payload.portfolio_id)
    if pid is None:
        return error_response("VALIDATION_ERROR", "invalid portfolio_id format", 422)
    portfolio = portfolio_repo.get_portfolio(db, pid)
    if portfolio is None:
        return error_response("NOT_FOUND", f"portfolio {payload.portfolio_id} not found", 404)

    try:
        result = run_attribution_for_portfolio(
            db,
            payload.portfolio_id,
            benchmark_asset_id=payload.benchmark_asset_id,
            period_start=payload.period_start,
            period_end=payload.period_end,
            timeframe=payload.timeframe,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        return error_response("SERVER_ERROR", str(exc), 500)

    # Serialize breakdown and return
    breakdown = []
    for item in result["breakdown"]:
        breakdown.append({
            "symbol": item["symbol"],
            "contribution": _serialize_return(item["contribution"]),
            "active_contribution": _serialize_return(item["active_contribution"]),
        })

    return success_response({
        "run_id": result["run_id"],
        "portfolio_id": result["portfolio_id"],
        "total_return": _serialize_return(result["total_return"]),
        "active_return": _serialize_return(result["active_return"]),
        "status": result["calculation_status"],
        "breakdown": breakdown,
    })


class BacktestRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, description="Asset symbols to backtest")
    strategy: str = Field("STATIC_WEIGHT", pattern="^(BUY_HOLD|STATIC_WEIGHT)$")
    weights: Optional[dict[str, float]] = Field(
        None, description="Target weight per symbol (normalized); default equal"
    )
    timeframe: str = Field("1d", description="Candle timeframe")
    limit: int = Field(300, ge=60, le=2000, description="Max candles per asset")
    rebalance_every: int = Field(21, ge=1, description="Rebalance schedule (periods)")
    fee_bps: float = Field(10.0, ge=0, description="Transaction fee in bps")
    slippage_bps: float = Field(5.0, ge=0, description="Slippage in bps")


@router.post("/fundamental")
def run_analytics_fundamental(
    payload: "FundamentalRequest",
    db: Session = Depends(get_db),
):
    """Asset-level fundamental analysis (Phase 1)."""
    from app.database.models import Asset
    assets = []
    for symbol in payload.symbols:
        a = db.query(Asset).filter_by(symbol=symbol, is_active=True).first()
        if a is None:
            return error_response("VALIDATION_ERROR", f"asset {symbol!r} not found", 422)
        assets.append(a)

    try:
        result = run_fundamental_for_universe(db, assets, timeframe=payload.timeframe)
        db.commit()
    except ValueError as exc:
        db.rollback()
        return error_response("INVALID_CONFIG", str(exc), 422)
    except Exception as exc:
        db.rollback()
        return error_response("SERVER_ERROR", str(exc), 500)

    return success_response({
        "run_id": result["run_id"],
        "status": result["status"],
        "per_asset": result.get("per_asset", []),
    })


class SentimentRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, description="Asset symbols")
    timeframe: str = Field("1d", description="Timeframe")


@router.post("/sentiment")
def run_analytics_sentiment(
    payload: SentimentRequest,
    db: Session = Depends(get_db),
):
    """Asset-level sentiment analysis (Phase 1).

    Persists to analytics_runs (SENTIMENT) + sentiment_results.
    Deterministic; uses LLM via app/ai for headline scoring.
    """
    from app.database.models import Asset
    assets = []
    for symbol in payload.symbols:
        a = db.query(Asset).filter_by(symbol=symbol, is_active=True).first()
        if a is None:
            return error_response("VALIDATION_ERROR", f"asset {symbol!r} not found", 422)
        assets.append(a)

    try:
        result = run_sentiment_for_universe(db, assets, timeframe=payload.timeframe)
        db.commit()
    except ValueError as exc:
        db.rollback()
        return error_response("INVALID_CONFIG", str(exc), 422)
    except Exception as exc:
        db.rollback()
        return error_response("SERVER_ERROR", str(exc), 500)

    return success_response({
        "run_id": result["run_id"],
        "status": result["status"],
    })


class FundamentalRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, description="Asset symbols")
    timeframe: str = Field("1d", description="Candle timeframe")


class ScenarioRequest(BaseModel):
    portfolio_id: str
    scenario_type: str = Field(..., pattern="^(SENSITIVITY|HISTORICAL|HYPOTHETICAL)$")
    asset_id: Optional[str] = None
    shock: Optional[float] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    timeframe: str = "1d"
    limit: int = Field(300, ge=2, le=2000)


class FactorRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=1, description="Asset symbols (factor universe)")
    factors: list[str] = Field(
        default_factory=lambda: ["MOMENTUM", "VOLATILITY", "REVERSAL", "SIZE"],
        description="Market-based factors to compute",
    )
    normalization: str = Field("ZSCORE", pattern="^(ZSCORE|RANK)$")
    weighting: str = Field("EQUAL", description="Composite weighting (Phase 1: EQUAL)")
    timeframe: str = Field("1d", description="Candle timeframe")
    limit: int = Field(300, ge=60, le=2000, description="Max candles per asset")


@router.post("/scenario")
def run_analytics_scenario(payload: "ScenarioRequest", db: Session = Depends(get_db)):
    """Deterministic Phase-1 sensitivity or historical scenario analysis."""
    pid = parse_uuid(payload.portfolio_id)
    if pid is None:
        return error_response("VALIDATION_ERROR", "invalid portfolio_id format", 422)
    if portfolio_repo.get_portfolio(db, pid) is None:
        return error_response("NOT_FOUND", f"portfolio {payload.portfolio_id} not found", 404)
    params = {
        "asset_id": payload.asset_id,
        "shock": payload.shock,
        "period_start": payload.period_start,
        "period_end": payload.period_end,
    }
    try:
        result = run_scenario_for_portfolio(
            db, payload.portfolio_id, payload.scenario_type, params,
            timeframe=payload.timeframe, limit=payload.limit,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        return error_response("SERVER_ERROR", str(exc), 500)
    return success_response({
        "run_id": result["run_id"],
        "portfolio_id": result["portfolio_id"],
        "scenario_type": result["scenario_type"],
        "portfolio_impact": _serialize_return(result["portfolio_impact"]),
        "per_asset": [
            {
                "symbol": item["symbol"],
                "shock": _serialize_return(item["shock"]),
                "impact": _serialize_return(item["impact"]),
                "correlated_impact": _serialize_return(item["correlated_impact"]),
            }
            for item in result["per_asset"]
        ],
        "status": result["status"],
    })


@router.post("/factor")
def run_analytics_factor(payload: "FactorRequest", db: Session = Depends(get_db)):
    """Deterministic Phase-1 market-based factor scores (momentum / volatility /
    reversal / size) over a symbol universe. Persists to analytics_runs (FACTOR)
    + factor_results. No network; fundamental factors are out of scope.
    """
    from app.database.models import Asset

    assets = []
    for symbol in payload.symbols:
        a = db.query(Asset).filter_by(symbol=symbol, is_active=True).first()
        if a is None:
            return error_response(
                "VALIDATION_ERROR", f"active asset {symbol!r} not found", 422
            )
        assets.append(a)
    if not assets:
        return error_response("VALIDATION_ERROR", "no symbols supplied", 422)

    cfg = FactorConfig(
        factors=payload.factors,
        normalization=payload.normalization,
        weighting=payload.weighting,
    )
    try:
        result = run_factor_for_universe(
            db, [a.id for a in assets], cfg=cfg,
            timeframe=payload.timeframe, limit=payload.limit,
            symbol_map={str(a.id): a.symbol for a in assets},
        )
        db.commit()
    except ValueError as exc:
        db.rollback()
        return error_response("INVALID_CONFIG", str(exc), 422)
    except Exception as exc:
        db.rollback()
        return error_response("SERVER_ERROR", str(exc), 500)

    return success_response(result)