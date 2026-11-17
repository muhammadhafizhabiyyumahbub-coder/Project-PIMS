"Seam 2: qualification service readiness states, labels, and policies."
from datetime import datetime, timedelta, timezone

from app.qualification import policy, service


def test_empty_asset_all_pending(db_session, seeded_universe):
    btc = seeded_universe["assets"]["BTCUSDT"]
    readiness = service.evaluate_engine_readiness(db_session, btc.id, "1h")

    assert readiness["TECHNICAL"]["state"] == "PENDING"
    assert readiness["MARKET_REGIME"]["state"] == "PENDING"
    assert readiness["RISK"]["state"] == "PENDING"
    assert readiness["SCANNER"]["state"] == "PENDING"
    assert readiness["CORRELATION"]["state"] == "NOT AVAILABLE"
    assert readiness["CORRELATION"]["label"] == "NOT AVAILABLE"

    summary = service.qualification_summary(readiness)
    assert summary["status"] == "NOT_QUALIFIED"
    assert summary["passed_by"] == []


def test_analyzed_universe_qualified(db_session, analyzed_universe):
    btc = analyzed_universe["assets"]["BTCUSDT"]
    readiness = service.evaluate_engine_readiness(db_session, btc.id, "1h")

    for engine in ("TECHNICAL", "MARKET_REGIME", "RISK", "SCANNER"):
        assert readiness[engine]["state"] == "READY"
        assert readiness[engine]["label"] == "PASSED"

    for engine in ("CORRELATION", "FUNDAMENTAL", "SENTIMENT"):
        assert readiness[engine]["label"] == "NOT AVAILABLE"

    summary = service.qualification_summary(readiness)
    assert summary["status"] == "PARTIAL"  # required PASSED, optional NOT AVAILABLE
    assert set(summary["passed_by"]) == {"TECHNICAL", "MARKET_REGIME", "RISK", "SCANNER"}


def test_stale_scanner_marked_stale(db_session, analyzed_universe):
    btc = analyzed_universe["assets"]["BTCUSDT"]
    scanner_result = service._latest_scanner_result(db_session, btc.id)
    scanner_result.freshness_status = "STALE"
    db_session.commit()

    readiness = service.evaluate_engine_readiness(db_session, btc.id, "1h")
    assert readiness["SCANNER"]["state"] == "STALE"
    assert readiness["SCANNER"]["label"] == "STALE"
    assert readiness["SCANNER"]["label"] != "PASSED"

    summary = service.qualification_summary(readiness)
    assert summary["status"] == "STALE"
    assert "SCANNER" not in summary["passed_by"]


def test_high_volatility_fails_risk_qualification(db_session, analyzed_universe):
    btc = analyzed_universe["assets"]["BTCUSDT"]

    strict_policy = {**policy.DEFAULT_POLICY, "risk_max_annualized_volatility": 0.01}
    readiness = service.evaluate_engine_readiness(
        db_session, btc.id, "1h", policy=strict_policy
    )

    assert readiness["RISK"]["state"] == "READY"
    assert readiness["RISK"]["label"] == "FAILED"
    summary = service.qualification_summary(readiness)
    assert summary["status"] == "NOT_QUALIFIED"
    assert "RISK" not in summary["passed_by"]
