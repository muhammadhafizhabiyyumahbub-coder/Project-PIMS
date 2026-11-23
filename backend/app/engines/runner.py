"Engine runner: loads candles, runs engines, persists analytics_runs + results."
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.config.settings import get_settings
from app.database.models import (
    AnalyticsRun,
    Asset,
    DataProvider,
    Market,
    MarketCandle,
    MarketRegimeResult,
    ProviderInstrument,
    RiskResult,
    TechnicalResult,
)
from app.engines import market_regime, risk, technical

logger = logging.getLogger(__name__)

CALCULATION_VERSION = "1.0.0"


def resolve_provider_id(session: Session, asset: Asset) -> Optional[uuid.UUID]:
    """Resolve the canonical provider_id for an asset based on its market and settings."""
    settings = get_settings()
    crypto_provider_code = settings.crypto_provider.upper()
    
    if not asset.market_id:
        return None
    
    market = session.get(Market, asset.market_id)
    if not market:
        return None
    
    # Determine target provider code based on market type
    if market.market_type == "CRYPTO" or market.code == "CRYPTO":
        target_provider_code = crypto_provider_code
    else:
        target_provider_code = "YAHOO"
    
    # Find the active provider instrument for this asset and provider
    provider = (
        session.query(DataProvider)
        .filter_by(code=target_provider_code)
        .first()
    )
    if not provider:
        return None
    
    pi = (
        session.query(ProviderInstrument)
        .filter_by(asset_id=asset.id, provider_id=provider.id, is_active=True)
        .first()
    )
    return pi.provider_id if pi else None


def load_candles(
    session: Session, 
    asset_id, 
    timeframe: str, 
    limit: int = 300,
    provider_id: Optional[uuid.UUID] = None
) -> list[dict]:
    """Load candles for an asset, optionally filtered by provider.
    
    If provider_id is not provided, it will be resolved from the asset's market.
    """
    # If no explicit provider_id, resolve from asset
    if provider_id is None:
        asset = session.get(Asset, asset_id)
        if asset:
            provider_id = resolve_provider_id(session, asset)
        if provider_id is None:
            # Never mix providers silently: fall back to the provider that wrote the
            # most recent candle for this asset/timeframe, and log which one was used.
            latest = (
                session.query(MarketCandle)
                .filter_by(asset_id=asset_id, timeframe=timeframe)
                .order_by(MarketCandle.open_time.desc())
                .first()
            )
            if latest is not None:
                provider_id = latest.provider_id
                logger.info(
                    "load_candles: no configured provider mapping for asset %s (%s); "
                    "using the provider of the latest candle (%s)",
                    asset_id,
                    timeframe,
                    provider_id,
                )
    
    query = (
        session.query(MarketCandle)
        .filter_by(asset_id=asset_id, timeframe=timeframe)
    )
    
    if provider_id:
        query = query.filter_by(provider_id=provider_id)
    
    rows = (
        query
        .order_by(MarketCandle.open_time.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()  # oldest-first
    return [
        {
            "open_time": r.open_time,
            "close_time": r.close_time,
            "open": float(r.open_price),
            "high": float(r.high_price),
            "low": float(r.low_price),
            "close": float(r.close_price),
            "volume": float(r.volume) if r.volume is not None else None,
            "quote_volume": float(r.quote_volume) if r.quote_volume is not None else None,
            "currency": r.currency,
        }
        for r in rows
    ]


def _new_run(
    session: Session,
    engine_type: str,
    asset: Asset,
    timeframe: str,
    candles: list[dict],
) -> AnalyticsRun:
    run = AnalyticsRun(
        engine_type=engine_type,
        asset_id=asset.id,
        timeframe=timeframe,
        observation_start=candles[0]["close_time"] if candles else None,
        observation_end=candles[-1]["close_time"] if candles else None,
        calculation_version=CALCULATION_VERSION,
        input_metadata={"candle_count": len(candles), "timeframe": timeframe},
        execution_status="RUNNING",
        started_at=datetime.now(timezone.utc),
    )
    session.add(run)
    session.flush()
    return run


def run_instrument_engines(session: Session, asset: Asset, timeframe: str) -> dict:
    """Run technical + market_regime + risk engines for one asset. Persist results."""
    provider_id = resolve_provider_id(session, asset)
    candles = load_candles(session, asset.id, timeframe, provider_id=provider_id)
    now = datetime.now(timezone.utc)
    observation_time = candles[-1]["close_time"] if candles else now
    output: dict = {"technical": None, "market_regime": None, "risk": None}

    tech = technical.compute(candles, observation_time)
    run_tech = _new_run(session, "TECHNICAL", asset, timeframe, candles)
    if tech["calculation_status"] == "COMPLETED":
        run_tech.execution_status = "COMPLETED"
        run_tech.completed_at = now
        for name, params, values in [
            ("SMA_20", {"period": 20}, {"value": tech["values"]["sma_20"]}),
            ("SMA_50", {"period": 50}, {"value": tech["values"]["sma_50"]}),
            ("RSI_14", {"period": 14}, {"value": tech["values"]["rsi_14"]}),
            ("ATR_14", {"period": 14}, {"value": tech["values"]["atr_14"]}),
            (
                "MACD",
                {"fast": 12, "slow": 26, "signal": 9},
                tech["values"]["macd"],
            ),
        ]:
            session.add(
                TechnicalResult(
                    analytics_run_id=run_tech.id,
                    asset_id=asset.id,
                    timeframe=timeframe,
                    indicator_name=name,
                    indicator_parameters=params,
                    observation_time=tech["observation_time"],
                    indicator_values=values,
                    calculation_status="COMPLETED",
                )
            )
        output["technical"] = tech
    else:
        run_tech.execution_status = "FAILED"
        run_tech.error_message = tech.get("error")
        run_tech.completed_at = now

    regime_run = _new_run(session, "MARKET_REGIME", asset, timeframe, candles)
    if tech["calculation_status"] == "COMPLETED":
        v = tech["values"]
        classification = market_regime.classify(
            v["sma_20"], v["sma_50"], v["last_close"], v["rsi_14"], v["atr_14"]
        )
        regime_run.execution_status = "COMPLETED"
        regime_run.completed_at = now
        session.add(
            MarketRegimeResult(
                analytics_run_id=regime_run.id,
                asset_id=asset.id,
                timeframe=timeframe,
                trend_regime=classification["trend_regime"],
                volatility_regime=classification["volatility_regime"],
                momentum_regime=classification["momentum_regime"],
                confidence_score=classification["confidence_score"],
                observation_time=observation_time,
                result_metadata=classification,
            )
        )
        output["market_regime"] = classification
    else:
        regime_run.execution_status = "BLOCKED"
        regime_run.error_message = "technical engine failed"
        regime_run.completed_at = now

    risk_run = _new_run(session, "RISK", asset, timeframe, candles)
    risk_out = risk.compute(candles)
    if risk_out["calculation_status"] == "COMPLETED":
        risk_run.execution_status = "COMPLETED"
        risk_run.completed_at = now
        session.add(
            RiskResult(
                analytics_run_id=risk_run.id,
                asset_id=asset.id,
                observation_period=timeframe,
                volatility=risk_out["volatility"],
                max_drawdown=risk_out["max_drawdown"],
                risk_classification=risk_out["risk_classification"],
                result_metadata=risk_out,
            )
        )
        output["risk"] = risk_out
    else:
        risk_run.execution_status = "FAILED"
        risk_run.error_message = risk_out.get("error")
        risk_run.completed_at = now

    session.commit()
    return output
