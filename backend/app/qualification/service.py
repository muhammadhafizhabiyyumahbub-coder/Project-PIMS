"Qualification service: engine readiness states and PASSED/FAILED labels."
import json
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.database.models import (
    AnalyticsRun,
    MarketRegimeResult,
    RiskResult,
    ScannerResult,
    TechnicalResult,
)
from app.qualification.policy import DEFAULT_POLICY
READY = "READY"
PENDING = "PENDING"
RUNNING = "RUNNING"
BLOCKED = "BLOCKED"
FAILED = "FAILED"
STALE = "STALE"
PARTIAL = "PARTIAL"

PASSED = "PASSED"
NOT_AVAILABLE = "NOT AVAILABLE"


def jsonable_readiness(readiness: dict) -> dict:
    """JSON-safe copy for JSONB storage and API responses."""
    return json.loads(json.dumps(readiness, default=str))


def _latest_analytics_run(session: Session, asset_id, engine_type: str):
    return (
        session.query(AnalyticsRun)
        .filter_by(asset_id=asset_id, engine_type=engine_type)
        .order_by(AnalyticsRun.started_at.desc())
        .first()
    )


def _latest_regime(session: Session, asset_id: str, timeframe: str) -> MarketRegimeResult | None:
    return (
        session.query(MarketRegimeResult)
        .filter_by(asset_id=asset_id, timeframe=timeframe)
        .order_by(MarketRegimeResult.observation_time.desc())
        .first()
    )


def _latest_risk(session: Session, asset_id: str, timeframe: str) -> RiskResult | None:
    return (
        session.query(RiskResult)
        .join(AnalyticsRun, RiskResult.analytics_run_id == AnalyticsRun.id)
        .filter(RiskResult.asset_id == asset_id, AnalyticsRun.timeframe == timeframe)
        .order_by(AnalyticsRun.started_at.desc())
        .first()
    )


def _latest_technical(session: Session, asset_id: str, timeframe: str) -> TechnicalResult | None:
    return (
        session.query(TechnicalResult)
        .filter_by(asset_id=asset_id, timeframe=timeframe, indicator_name="RSI_14")
        .order_by(TechnicalResult.observation_time.desc())
        .first()
    )


def _latest_scanner_result(session: Session, asset_id: str, timeframe: str) -> ScannerResult | None:
    return (
        session.query(ScannerResult)
        .join(AnalyticsRun, ScannerResult.scanner_run_id == AnalyticsRun.id)
        .filter(ScannerResult.asset_id == asset_id, AnalyticsRun.timeframe == timeframe)
        .order_by(ScannerResult.created_at.desc())
        .first()
    )


def _state_from_run(run: AnalyticsRun | None, result_time: datetime | None, now: datetime, max_stale: int) -> str:
    if run is None:
        return PENDING
    if run.execution_status == "RUNNING":
        return RUNNING
    if run.execution_status in ("FAILED", "BLOCKED"):
        return FAILED if run.execution_status == "FAILED" else BLOCKED
    if result_time is None:
        return BLOCKED
    if (now - result_time) > timedelta(seconds=max_stale):
        return STALE
    return READY


def evaluate_engine_readiness(
    session: Session, asset_id: str, timeframe: str, policy: dict | None = None
) -> dict[str, dict]:
    """Return readiness state + qualification label per engine for one instrument."""
    policy = policy or DEFAULT_POLICY
    now = datetime.now(timezone.utc)
    max_stale = policy["max_stale_seconds"]
    readiness: dict[str, dict] = {}

    # Technical
    tech = _latest_technical(session, asset_id, timeframe)
    tech_run = session.query(AnalyticsRun).filter_by(asset_id=asset_id, engine_type="TECHNICAL", timeframe=timeframe).order_by(AnalyticsRun.started_at.desc()).first()
    state = _state_from_run(tech_run, tech.observation_time if tech else None, now, max_stale)
    readiness["TECHNICAL"] = {
        "state": state,
        "label": PASSED if state == READY else state,
        "observation_time": tech.observation_time if tech else None,
        "detail": {"engine": "technical_analysis", "required": True},
    }

    # Market regime (depends on technical; failed technical blocks regime)
    regime = _latest_regime(session, asset_id, timeframe)
    regime_run = session.query(AnalyticsRun).filter_by(asset_id=asset_id, engine_type="MARKET_REGIME", timeframe=timeframe).order_by(AnalyticsRun.started_at.desc()).first()
    state = _state_from_run(regime_run, regime.observation_time if regime else None, now, max_stale)
    if state == READY and regime is not None:
        allowed = policy["regime_allowed_trends"]
        if allowed is not None and regime.trend_regime not in allowed:
            readiness["MARKET_REGIME"] = {
                "state": READY,
                "label": FAILED,
                "observation_time": regime.observation_time,
                "detail": {"trend_regime": regime.trend_regime, "required": True},
            }
        else:
            readiness["MARKET_REGIME"] = {
                "state": READY,
                "label": PASSED,
                "observation_time": regime.observation_time,
                "detail": {"trend_regime": regime.trend_regime, "required": True},
            }
    else:
        readiness["MARKET_REGIME"] = {
            "state": state,
            "label": state,
            "observation_time": regime.observation_time if regime else None,
            "detail": {"required": True},
        }

    # Risk
    risk_result = _latest_risk(session, asset_id, timeframe)
    risk_run = session.query(AnalyticsRun).filter_by(asset_id=asset_id, engine_type="RISK", timeframe=timeframe).order_by(AnalyticsRun.started_at.desc()).first()
    # Staleness follows the underlying data window, not when the run happened:
    # recomputing from old candles must not qualify as fresh.
    risk_data_time = risk_run.observation_end if risk_run else None
    state = _state_from_run(risk_run, risk_data_time, now, max_stale)
    if state == READY and risk_result is not None:
        if risk_result.volatility is None:
             readiness["RISK"] = {
                "state": READY,
                "label": FAILED,
                "observation_time": risk_run.completed_at,
                "detail": {
                    "volatility": None,
                    "reason": "risk metric unavailable",
                    "required": True,
                },
            }
        else:
            vol = float(risk_result.volatility)
            if vol <= policy["risk_max_annualized_volatility"]:
                readiness["RISK"] = {
                    "state": READY,
                    "label": PASSED,
                    "observation_time": risk_run.completed_at,
                    "detail": {
                        "volatility": vol,
                        "classification": risk_result.risk_classification,
                        "required": True,
                    },
                }
            else:
                readiness["RISK"] = {
                    "state": READY,
                    "label": FAILED,
                    "observation_time": risk_run.completed_at,
                    "detail": {
                        "volatility": vol,
                        "threshold": policy["risk_max_annualized_volatility"],
                        "required": True,
                    },
                }
    else:
        readiness["RISK"] = {
            "state": state,
            "label": state,
            "observation_time": risk_run.completed_at if risk_run else None,
            "detail": {"required": True},
        }

    # Scanner eligibility
    scanner_result = _latest_scanner_result(session, asset_id, timeframe)
    scanner_run = session.query(AnalyticsRun).filter_by(asset_id=asset_id, engine_type="SCANNER", timeframe=timeframe).order_by(AnalyticsRun.started_at.desc()).first()
    if scanner_result is None:
        readiness["SCANNER"] = {
            "state": PENDING,
            "label": PENDING,
            "observation_time": None,
            "detail": {"required": True},
        }
    else:
        stale = (
            scanner_result.freshness_status == "STALE"
            or (now - scanner_result.data_timestamp) > timedelta(seconds=max_stale)
        )
        min_score = policy["scanner_min_score"]
        passed = (
            not stale
            and scanner_result.result_status == "COMPLETED"
            and scanner_result.score is not None
            and (min_score is None or float(scanner_result.score) >= min_score)
        )
        readiness["SCANNER"] = {
            "state": STALE if stale else READY,
            "label": PASSED if passed else (STALE if stale else FAILED),
            "observation_time": scanner_result.data_timestamp,
            "detail": {
                "score": float(scanner_result.score) if scanner_result.score is not None else None,
                "rank": scanner_result.rank,
                "required": True,
            },
        }

    # Optional engines: no implementation in this slice; must be disclosed.
    for engine in policy["optional_engines"]:
        readiness[engine] = {
            "state": NOT_AVAILABLE,
            "label": NOT_AVAILABLE,
            "observation_time": None,
            "detail": {"required": False},
        }

    return readiness


def qualification_summary(readiness: dict[str, dict]) -> dict:
    """Overall qualification status + list of engines actually passed."""
    required = [k for k, v in readiness.items() if v["detail"].get("required")]
    optional = [k for k, v in readiness.items() if not v["detail"].get("required")]
    required_states = [readiness[k]["state"] for k in required]
    passed_by = [k for k, v in readiness.items() if v["label"] == PASSED]

    if any(s in (FAILED, BLOCKED) for s in required_states):
        status = "NOT_QUALIFIED"
    elif any(readiness[k]["label"] == FAILED for k in required):
        status = "NOT_QUALIFIED"
    elif any(s == STALE for s in required_states):
        status = "STALE"
    elif all(s == READY for s in required_states):
        status = "PARTIAL" if any(readiness[k]["state"] == NOT_AVAILABLE for k in optional) else "QUALIFIED"
    else:
        status = "NOT_QUALIFIED"

    return {"status": status, "passed_by": passed_by}
