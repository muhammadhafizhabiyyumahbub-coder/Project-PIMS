"Engine runner: loads candles, runs engines, persists analytics_runs + results."
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.database.models import (
    AnalyticsRun,
    Asset,
    MarketCandle,
    MarketRegimeResult,
    RiskResult,
    TechnicalResult,
)
from app.engines import market_regime, risk, technical

CALCULATION_VERSION = "1.0.0"


def load_candles(session: Session, asset_id, timeframe: str, limit: int = 300) -> list[dict]:
    rows = (
        session.query(MarketCandle)
        .filter_by(asset_id=asset_id, timeframe=timeframe)
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
    candles = load_candles(session, asset.id, timeframe)
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
