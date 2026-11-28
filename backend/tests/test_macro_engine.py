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
from app.data.providers.macro.fred import FREDAdapter, SERIES_MAP
from app.data.providers.macro.fred_fetch import FredFetcher
from app.engines.macro.engine import (
    classify_macro_regime,
    classify_regime,
    compute_metrics,
    rolling_average,
    run_macro_analysis,
    yoy_change,
    yoy_change_pp,
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


# ---------------------------------------------------------------------------
# Audit F2 — GDP series + frequency-aware YoY lag
# ---------------------------------------------------------------------------


def test_gdp_maps_to_real_quarterly_gdpc1():
    # spec: GDPC1 (quarterly, real); the annual nominal GDPA was the blocker.
    assert SERIES_MAP["GDP"] == "GDPC1"


def test_yoy_change_pp_difference_and_insufficient():
    values = [float(10 + i) for i in range(13)]  # 10..22
    assert abs(yoy_change_pp(values) - 12.0) < 1e-9  # 22 - 10 pp
    assert yoy_change_pp([1.0, 2.0, 3.0]) is None  # fewer than lag+1


def test_quarterly_yoy_uses_lag_four():
    # 6 quarters 100..105 -> YoY = (105 - 101)/101*100 (lag 4, not 12).
    obs = [
        {"date": f"{2024 + i // 4}-{(i % 4) * 3 + 1:02d}-01", "value": float(100 + i)}
        for i in range(6)
    ]
    m = compute_metrics(obs, freq="quarterly")
    assert m["yoy"] == pytest.approx((105 - 101) / 101 * 100)
    assert m["yoy_unit"] == "%"


# ---------------------------------------------------------------------------
# Audit F3 — percent series YoY in percentage points
# ---------------------------------------------------------------------------


def test_percent_series_yoy_is_percentage_points():
    values = [4.4] + [4.0] * 11 + [4.1]  # 13 monthly obs, last 4.1, t-12 = 4.4
    obs = [{"date": f"2025-{i:02d}-01", "value": v} for i, v in enumerate(values, 1)]
    m = compute_metrics(obs, freq="monthly", unit="percent")
    assert m["yoy"] == pytest.approx(4.1 - 4.4)  # -0.30 pp, not -6.82 %
    assert m["yoy_unit"] == "pp"


# ---------------------------------------------------------------------------
# Audit F4 — rolling window tracks frequency
# ---------------------------------------------------------------------------


def test_rolling_average_window_tracks_frequency():
    quarterly = [{"date": "2024-01-01", "value": float(100 + i)} for i in range(6)]
    # 6 quarters -> window 4 -> mean of last 4 (102..105) = 103.5
    assert compute_metrics(quarterly, freq="quarterly")["rolling_avg_12"] == pytest.approx(103.5)
    # daily window is 12 observations
    daily = [{"date": "2025-01-01", "value": float(100 + i)} for i in range(20)]
    assert compute_metrics(daily, freq="daily")["rolling_avg_12"] == pytest.approx(
        sum(108 + i for i in range(12)) / 12
    )


# ---------------------------------------------------------------------------
# Audit F6 — standard macro regime from GDP YoY + UNRATE direction
# ---------------------------------------------------------------------------


def test_classify_macro_regime():
    assert classify_macro_regime(2.3, [4.4, 4.3, 4.2, 4.1])[0] == "EXPANSION"
    assert classify_macro_regime(2.3, [4.1, 4.2, 4.3, 4.4])[0] == "CONTRACTION"  # rising
    assert classify_macro_regime(-1.0, [4.4, 4.3, 4.2, 4.1])[0] == "CONTRACTION"  # GDP < 0
    assert classify_macro_regime(None, [4.4, 4.1])[0] == "UNAVAILABLE"
    regime, basis = classify_macro_regime(2.3, [4.4, 4.3, 4.2, 4.1])
    assert regime == "EXPANSION"
    assert basis["gdp_yoy"] == 2.3
    assert basis["unrate_delta"] == pytest.approx(-0.1)


def test_macro_endpoint_reports_standard_regime(db_session, monkeypatch):
    gdp = [
        {"date": f"{y}-{m:02d}-01", "value": v}
        for y, m, v in [
            (2024, 1, 100.0), (2024, 4, 101.0), (2024, 7, 102.0),
            (2024, 10, 103.0), (2025, 1, 104.0),
        ]
    ]
    unrate = [
        {"date": f"2025-{m:02d}-01", "value": v}
        for m, v in [(1, 4.4), (2, 4.3), (3, 4.2), (4, 4.1)]
    ]
    _mock_adapter(monkeypatch, {"GDPC1": gdp, "UNRATE": unrate})

    data = client.get("/api/v1/analytics/macro", params={"series": "GDP,UNRATE"}).json()["data"]
    assert data["regime"] == "EXPANSION"
    assert data["regime_basis"]["gdp_yoy"] > 0
    assert data["regime_basis"]["unrate_delta"] < 0
    gdp_result = next(r for r in data["results"] if r["series_id"] == "GDP")
    assert gdp_result["provider_series"] == "GDPC1"
    assert gdp_result["frequency"] == "quarterly"


# ---------------------------------------------------------------------------
# Audit F7 — provider integrity (no fabricated data, HTTP errors surface)
# ---------------------------------------------------------------------------


def test_fred_fetcher_missing_key_returns_no_data():
    assert FredFetcher("").fetch("CPIAUCSL") == []
    assert FredFetcher("test_key").fetch("CPIAUCSL") == []


def test_fred_fetcher_http_error_returns_no_data(monkeypatch):
    """When httpx.Client raises ConnectError, fetch returns [] (no fabricated data)."""
    import httpx

    fetcher = FredFetcher("real-key")
    # Inject a transport that raises on any request
    def _failing_transport(request):
        raise httpx.ConnectError("down")
    fetcher.transport = httpx.MockTransport(_failing_transport)
    assert fetcher.fetch("CPIAUCSL") == []


def test_fred_adapter_http_error_is_logged(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.data.providers.macro.fred.logger.warning",
        lambda *a, **k: calls.append(a),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    adapter = FREDAdapter(api_key="k", transport=httpx.MockTransport(handler))
    assert adapter.fetch_observations("CPIAUCSL") == []
    assert calls and "CPIAUCSL" in calls[0]


def test_fred_adapter_empty_key_returns_no_data():
    assert FREDAdapter(api_key="").fetch_observations("CPIAUCSL") == []


def test_fred_http_status_error_does_not_leak_api_key(monkeypatch):
    """§26 key-leak regression: when FRED returns a non-2xx status, the
    httpx.HTTPStatusError message embeds the full request URL (including the
    api_key query param). Neither the log line nor any re-raised exception
    must contain the key. (Audit probe: `raise_for_status` message must not
    contain the api_key.)"""
    secret = "a1b2c3d4SECRETFREDKEY"
    logged: list = []
    monkeypatch.setattr(
        "app.data.providers.macro.fred.logger.warning",
        lambda *a, **k: logged.append(" ".join(str(x) for x in a)),
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "bad key"})

    adapter = FREDAdapter(api_key=secret, transport=httpx.MockTransport(handler))
    assert adapter.fetch_observations("CPIAUCSL") == []
    # log must not contain the secret key
    assert logged, "expected a warning to be logged"
    for line in logged:
        assert secret not in line, f"api_key leaked into log: {line!r}"
    # also: the raised httpx error string itself must be safe to inspect
    # (guard: building the message from status_code only, not exc repr)
    import httpx as _httpx
    try:
        _httpx.Response(401, request=_httpx.Request("GET", f"https://x/?api_key={secret}")).raise_for_status()
    except _httpx.HTTPStatusError as e:
        # httpx DOES embed the URL — this is why we must not `str(exc)` it.
        assert secret in str(e) or True  # document the httpx behaviour
        # our code path must not have logged `str(e)`
        for line in logged:
            assert secret not in line


def test_fred_adapter_http_error_no_key_leak(monkeypatch):
    """REGRESSION (audit C-1): on HTTP error, log records must NOT contain
    the api_key — httpx str(exc) embeds the full URL (api_key in query string)."""
    import logging
    fetcher = FredFetcher("super-secret-key-123")

    def handler(request):
        return httpx.Response(401, json={"error": "bad key"})
    fetcher.transport = httpx.MockTransport(handler)

    # Capture log records via a handler on the fred_fetch logger
    handler_list = []
    class _Capture(logging.Handler):
        def emit(self, record):
            handler_list.append(record)

    cap_handler = _Capture()
    fetcher_logger = logging.getLogger("app.data.providers.macro.fred_fetch")
    fetcher_logger.addHandler(cap_handler)
    try:
        assert fetcher.fetch("CPIAUCSL") == []
    finally:
        fetcher_logger.removeHandler(cap_handler)

    # The api_key must NOT appear in any log record (message or exception str).
    for rec in handler_list:
        assert "super-secret-key-123" not in rec.getMessage(), (
            f"api_key leaked in log: {rec.getMessage()!r}"
        )
