"""M4 Macro Engine — Phase 1 tests (FRED via injectable mock transport).

Covers: pure metric math (YoY, rolling average, z-score, regime), UNAVAILABLE
handling (never 0), endpoint + persistence of analytics_runs(MACRO) +
macro_results, validation, determinism. Deterministic, no real network.
"""
from datetime import datetime, timezone

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database.models import AnalyticsRun, MacroResult
from app.data.providers.macro.fred import FREDAdapter
from app.engines.macro.engine import (
    classify_regime,
    compute_metrics,
    rolling_average,
    run_macro_analysis,
    yoy_change,
    zscore,
)

client = TestClient(app)


# ---------------------------------------------------------------------------
# Pure-math tests
# ---------------------------------------------------------------------------


def test_yoy_change_basic():
    values = [float(100 + i) for i in range(13)]  # 100..112
    assert abs(yoy_change(values) - 12.0) < 1e-9  # (112-100)/100*100


def test_yoy_change_insufficient_or_zero_prev():
    assert yoy_change([1.0, 2.0, 3.0]) is None  # fewer than lag+1
    assert yoy_change([0.0] + [1.0] * 12) is None  # zero base period


def test_rolling_average_basic_and_insufficient():
    values = [float(100 + i) for i in range(13)]  # 100..112
    # last 12: 101..112 -> mean 106.5
    assert abs(rolling_average(values) - 106.5) < 1e-9
    assert rolling_average([1.0, 2.0]) is None


def test_zscore_matches_independent_value():
    # [1,2,3,4,5]: mean 3, population std sqrt(2), last 5 -> z = 2/sqrt(2)
    z = zscore([1.0, 2.0, 3.0, 4.0, 5.0])
    assert abs(z - 1.4142135623730951) < 1e-9
    assert zscore([2.0, 2.0, 2.0]) is None  # zero variance -> undefined
    assert zscore([1.0]) is None  # too few


def test_classify_regime():
    assert classify_regime(110.0, 100.0) == "EXPANSION"
    assert classify_regime(90.0, 100.0) == "CONTRACTION"
    assert classify_regime(100.0, 100.0) == "EXPANSION"  # >= counts as expansion
    assert classify_regime(None, 100.0) == "UNAVAILABLE"


def test_compute_metrics_unavailable_is_none_not_zero():
    m = compute_metrics([])
    assert m["status"] == "UNAVAILABLE"
    assert m["reason"] == "no FRED data"
    assert m["period"] is None
    for k in ("level", "yoy", "rolling_avg_12", "zscore", "value"):
        assert m.get(k) is None
    assert m["regime"] == "UNAVAILABLE"


def test_compute_metrics_rising_series_is_expansion():
    obs = [
        {"date": f"2024-{(i % 12) + 1:02d}-01", "value": float(100 + i)}
        for i in range(24)
    ]
    m = compute_metrics(obs)
    assert m["status"] == "COMPLETED"
    assert m["level"] == 123.0
    assert m["period"] == obs[-1]["date"]
    assert m["rolling_avg_12"] == pytest.approx(117.5)
    assert m["regime"] == "EXPANSION"
    assert m["yoy"] == pytest.approx((123 - 111) / 111 * 100)


# ---------------------------------------------------------------------------
# Endpoint + persistence (DB)
# ---------------------------------------------------------------------------


def _series(days_ago_end: int = 0):
    """24 monthly observations, rising values 100..123 (oldest-first)."""
    dates = [f"2024-{m:02d}-01" for m in range(1, 13)] + [
        f"2025-{m:02d}-01" for m in range(1, 13)
    ]
    return [{"date": d, "value": float(100 + i)} for i, d in enumerate(dates)]


def _mock_adapter(monkeypatch, series_values):
    """Patch the engine's FREDAdapter factory with an httpx.MockTransport-backed
    adapter (no network)."""

    def handler(request: httpx.Request) -> httpx.Response:
        sid = request.url.params.get("series_id")
        vals = series_values.get(sid)
        if vals is None:
            return httpx.Response(404, json={"error": "not found"})
        return httpx.Response(200, json={"observations": vals})

    def factory():
        return FREDAdapter(api_key="test-key", transport=httpx.MockTransport(handler))

    monkeypatch.setattr("app.engines.macro.engine.FREDAdapter", factory)


def test_macro_endpoint_persists(db_session, monkeypatch):
    _mock_adapter(monkeypatch, {"CPIAUCSL": _series(), "UNRATE": _series()})

    resp = client.get("/api/v1/analytics/macro", params={"series": "CPI,UNRATE", "period": "YoY"})
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "COMPLETED"
    assert data["analysis_type"] == "YOY"
    assert data["source"] == "FRED"
    assert [r["series_id"] for r in data["results"]] == ["CPI", "UNRATE"]
    for r in data["results"]:
        assert r["status"] == "COMPLETED"
        assert r["value"] is not None  # YoY value
        assert r["regime"] == "EXPANSION"

    run = db_session.get(AnalyticsRun, data["run_id"])
    assert run is not None and run.engine_type == "MACRO"

    rows = db_session.query(MacroResult).filter_by(analytics_run_id=run.id).all()
    # 2 series * 4 persisted metrics (YOY, ROLLING_AVG_12M, ZSCORE, REGIME)
    assert len(rows) == 8
    assert {r.analysis_type for r in rows} == {"YOY", "ROLLING_AVG_12M", "ZSCORE", "REGIME"}
    regime_rows = [r for r in rows if r.analysis_type == "REGIME"]
    assert all(r.value == 1.0 for r in regime_rows)


def test_macro_endpoint_unavailable_stores_null(db_session, monkeypatch):
    # FRED returns only missing (".") values -> fetch_observations -> [] -> UNAVAILABLE.
    _mock_adapter(
        monkeypatch,
        {"CPIAUCSL": [{"date": "2025-01-01", "value": "."}]},
    )

    resp = client.get("/api/v1/analytics/macro", params={"series": "CPI"})
    assert resp.status_code == 200, resp.text
    result = resp.json()["data"]["results"][0]
    assert result["status"] == "UNAVAILABLE"
    assert result["value"] is None
    assert result["reason"] == "no FRED data"

    rows = db_session.query(MacroResult).filter_by(
        analytics_run_id=resp.json()["data"]["run_id"]
    ).all()
    assert rows and all(r.value is None for r in rows)  # never coerced to 0


def test_macro_endpoint_unknown_series_422():
    resp = client.get("/api/v1/analytics/macro", params={"series": "CPI,NOPE"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_macro_endpoint_invalid_period_422(db_session, monkeypatch):
    _mock_adapter(monkeypatch, {"CPIAUCSL": _series()})
    resp = client.get("/api/v1/analytics/macro", params={"series": "CPI", "period": "NOPE"})
    assert resp.status_code == 422


def test_macro_determinism(db_session, monkeypatch):
    _mock_adapter(monkeypatch, {"CPIAUCSL": _series()})
    r1 = client.get("/api/v1/analytics/macro", params={"series": "CPI", "period": "ZSCORE"}).json()["data"]
    r2 = client.get("/api/v1/analytics/macro", params={"series": "CPI", "period": "ZSCORE"}).json()["data"]
    assert r1["run_id"] != r2["run_id"]  # distinct runs
    assert r1["results"][0]["value"] == r2["results"][0]["value"]
    assert r1["results"][0]["regime"] == r2["results"][0]["regime"]


def test_run_macro_analysis_rejects_unknown_series(db_session):
    with pytest.raises(ValueError):
        run_macro_analysis(db_session, ["NOPE"], period="YoY")
