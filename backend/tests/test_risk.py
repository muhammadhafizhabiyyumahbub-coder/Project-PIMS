"""Risk engine tests (Stage L), hand-computed expectations in comments.

Seam under test:
- Pure metrics: `compute_over_series` over hand-built daily close series.
- Endpoint: `GET /portfolios/{id}/risk?window=` over stored candles.
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest
from fastapi.testclient import TestClient

from app.database.models import MarketCandle
from app.engines.risk import portfolio_risk as risk


def dt(day: int) -> datetime:
    return datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day)


def series(symbol: str, closes: list[str]) -> risk.AssetSeries:
    return risk.AssetSeries(
        asset_id=symbol,
        symbol=symbol,
        asset_type="CRYPTO",
        closes=[(dt(i), D(c)) for i, c in enumerate(closes)],
        source="1d",
    )


# ---------------------------------------------------------------- pure metrics


def test_daily_volatility_and_annualization_hand_computed():
    """Closes 100,110,99,108.9 -> returns exactly 0.1, -0.1, 0.1.

    mean = 1/30. deviations +1/15, -2/15, +1/15.
    variance = (1/225 + 4/225 + 1/225) / 2 = (6/225)/2 = 1/75.
    stdev = sqrt(1/75) = 0.11547...
    annualized (365) = sqrt(1/75) * sqrt(365) = sqrt(365/75)
    """
    metrics, reasons, count, start, end = risk.compute_over_series(
        {"A": D(1)}, {"A": series("A", ["100", "110", "99", "108.9"])}, 365
    )
    assert count == 3
    assert start == dt(0) and end == dt(3)
    assert metrics["volatility"] == pytest.approx(
        (D(1) / D(75)).sqrt(), abs=D("1e-20")
    )
    assert metrics["annualized_volatility"] == pytest.approx(
        (D(365) / D(75)).sqrt(), abs=D("1e-18")
    )
    assert reasons == {}


def test_max_drawdown_is_negative_peak_to_trough():
    """Index from returns of closes 100,120,60: +0.2 then -0.5.

    V = 1, 1.2, 0.6. Peak 1.2 -> trough 0.6 gives (0.6-1.2)/1.2 = -0.5.
    """
    metrics, _, _, _, _ = risk.compute_over_series(
        {"A": D(1)}, {"A": series("A", ["100", "120", "60"])}, 365
    )
    assert metrics["max_drawdown"] == pytest.approx(D("-0.5"), abs=D("1e-12"))


def test_var_and_cvar_on_known_tail():
    """Closes give returns: -0.5, -0.25, +0.1, +0.2, +0.05 (5 returns).

    sorted: -0.5, -0.25, 0.05, 0.1, 0.2
    VaR 95: idx = floor(0.05 * 5) = 0 -> -0.5
    CVaR 95: tail = [-0.5] -> -0.5
    VaR 99: idx = floor(0.01 * 5) = 0 -> -0.5
    """
    returns = [D("-0.5"), D("-0.25"), D("0.1"), D("0.2"), D("0.05")]
    assert risk.empirical_var(returns, D("0.95")) == D("-0.5")
    assert risk.empirical_cvar(returns, D("0.95")) == D("-0.5")
    assert risk.empirical_var(returns, D("0.99")) == D("-0.5")


def test_cvar_averages_the_tail():
    """20 returns: five losses -0.10..-0.06, fifteen at +0.01.

    sorted: -0.10,-0.09,-0.08,-0.07,-0.06, then 0.01 x15
    VaR 95: idx = floor(0.05 * 20) = 1 -> -0.09
    CVaR 95: tail = indices 0..1 -> mean(-0.10, -0.09) = -0.095
    VaR 99: idx = floor(0.01 * 20) = 0 -> -0.10
    """
    returns = [D("-0.10"), D("-0.09"), D("-0.08"), D("-0.07"), D("-0.06")]
    returns += [D("0.01")] * 15
    assert risk.empirical_var(returns, D("0.99")) == D("-0.10")
    assert risk.empirical_var(returns, D("0.95")) == D("-0.09")
    assert risk.empirical_cvar(returns, D("0.95")) == D("-0.095")


def test_sharpe_with_zero_risk_free_rate():
    """Returns 0.1, -0.1, 0.1; mean = 1/30, stdev = sqrt(1/75).

    sharpe = (1/30) / sqrt(1/75) * sqrt(365) = sqrt(75)/30 * sqrt(365)
    """
    metrics, _, _, _, _ = risk.compute_over_series(
        {"A": D(1)}, {"A": series("A", ["100", "110", "99", "108.9"])}, 365
    )
    expected = (D(75).sqrt() / D(30)) * D(365).sqrt()
    assert metrics["sharpe"] == pytest.approx(expected, abs=D("1e-15"))


def test_sortino_uses_downside_only():
    """Returns 0.1, -0.1, 0.1 -> shortfalls 0, -0.1, 0.

    downside dev = sqrt((0 + 0.01 + 0)/3) = sqrt(1/300)
    sortino = (1/30) / sqrt(1/300) * sqrt(365) = sqrt(300)/30 * sqrt(365)
    """
    metrics, _, _, _, _ = risk.compute_over_series(
        {"A": D(1)}, {"A": series("A", ["100", "110", "99", "108.9"])}, 365
    )
    expected = (D(300).sqrt() / D(30)) * D(365).sqrt()
    assert metrics["sortino"] == pytest.approx(expected, abs=D("1e-15"))


def test_no_downside_observations_gives_sortino_reason():
    """Monotonically rising closes: every return is positive, so no downside."""
    metrics, reasons, _, _, _ = risk.compute_over_series(
        {"A": D(1)}, {"A": series("A", ["100", "110", "121"])}, 365
    )
    assert metrics["sortino"] is None
    assert "downside" in reasons["sortino"]


def test_portfolio_return_is_weighted_sum():
    """Two assets, weights 0.75 / 0.25.

    A: 100 -> 110 (+10%). B: 200 -> 180 (-10%).
    portfolio return = 0.75*0.1 + 0.25*(-0.1) = 0.05.
    Index V = 1 -> 1.05, so max_drawdown is 0 and only one return exists.
    """
    metrics, _, count, _, _ = risk.compute_over_series(
        {"A": D("0.75"), "B": D("0.25")},
        {"A": series("A", ["100", "110"]), "B": series("B", ["200", "180"])},
        365,
    )
    assert count == 1
    assert metrics["max_drawdown"] == D("0")
    assert metrics["volatility"] is None  # fewer than 2 returns
    assert "volatility" in risk.compute_over_series(
        {"A": D("0.75"), "B": D("0.25")},
        {"A": series("A", ["100", "110"]), "B": series("B", ["200", "180"])},
        365,
    )[1]


def test_only_aligned_dates_are_used():
    """A has 3 days, B has days 0 and 2 only -> only ONE aligned return (day0->day2).

    Never a gap-filled zero. A: 100->121 is +21% over the span.
    """
    b = risk.AssetSeries(
        asset_id="B",
        symbol="B",
        asset_type="CRYPTO",
        closes=[(dt(0), D("200")), (dt(2), D("200"))],
        source="1d",
    )
    _, _, count, start, end = risk.compute_over_series(
        {"A": D("0.5"), "B": D("0.5")},
        {"A": series("A", ["100", "110", "121"]), "B": b},
        365,
    )
    assert count == 1
    assert start == dt(0) and end == dt(2)


def test_constant_returns_give_zero_sharpe_and_reason():
    """Flat closes -> zero stdev: Sharpe null with a reason, never a divide error."""
    metrics, reasons, _, _, _ = risk.compute_over_series(
        {"A": D(1)}, {"A": series("A", ["100", "100", "100"])}, 365
    )
    assert metrics["volatility"] == D("0")
    assert metrics["sharpe"] is None
    assert "sharpe" in reasons


# ------------------------------------------------------------------- endpoint


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def portfolio_id(client):
    response = client.post(
        "/api/v1/portfolios", json={"name": "Risk Test", "base_currency": "USD"}
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def deposit(client, pid, amount):
    return client.post(
        "/api/v1/transactions",
        json={"portfolio_id": pid, "transaction_type": "DEPOSIT", "gross_amount": amount},
    )


def buy(client, pid, asset_id, qty, price):
    return client.post(
        "/api/v1/transactions",
        json={
            "portfolio_id": pid,
            "transaction_type": "BUY",
            "asset_id": asset_id,
            "quantity": qty,
            "price": price,
            "fee": "0",
        },
    )


def store_daily(db_session, asset_id, provider_id, closes: list[float], start_day=0):
    now = datetime.now(UTC)
    base = now - timedelta(days=len(closes) + start_day)
    for i, close in enumerate(closes):
        db_session.add(
            MarketCandle(
                asset_id=asset_id,
                provider_id=provider_id,
                timeframe="1d",
                open_time=base + timedelta(days=i),
                close_time=base + timedelta(days=i),
                open_price=D(str(close)),
                high_price=D(str(close)),
                low_price=D(str(close)),
                close_price=D(str(close)),
                volume=D("1000"),
                currency="USD",
                candle_status="CLOSED",
            )
        )
    db_session.commit()


def test_endpoint_insufficient_returns_is_unavailable(client, db_session, portfolio_id, seeded_universe):
    """Only 5 daily closes -> 4 returns < 30 -> UNAVAILABLE with reason, no numbers."""
    asset = seeded_universe["assets"]["BTCUSDT"]
    provider = seeded_universe["providers"][1]
    assert deposit(client, portfolio_id, "1000").status_code == 201
    assert buy(client, portfolio_id, str(asset.id), "1", "100").status_code == 201
    store_daily(db_session, asset.id, provider.id, [100, 101, 102, 103, 104])

    response = client.get(f"/api/v1/portfolios/{portfolio_id}/risk?window=90")
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["data_status"] == "UNAVAILABLE"
    assert "minimal 30" in data["data_status_reason"]
    assert all(value is None for value in data["metrics"].values())


def test_endpoint_asset_without_candles_is_unavailable(client, db_session, portfolio_id, seeded_universe):
    """A held asset with no stored candle -> UNAVAILABLE, never a zero-filled series."""
    asset = seeded_universe["assets"]["ETHUSDT"]
    assert deposit(client, portfolio_id, "1000").status_code == 201
    assert buy(client, portfolio_id, str(asset.id), "1", "100").status_code == 201

    response = client.get(f"/api/v1/portfolios/{portfolio_id}/risk")
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["data_status"] == "UNAVAILABLE"
    assert "ETHUSDT" in data["data_status_reason"]


def test_endpoint_empty_portfolio_is_unavailable(client, portfolio_id):
    response = client.get(f"/api/v1/portfolios/{portfolio_id}/risk")
    assert response.status_code == 200, response.text
    assert response.json()["data"]["data_status"] == "UNAVAILABLE"


def test_endpoint_available_with_real_metrics(client, db_session, portfolio_id, seeded_universe):
    """40 daily closes with alternating +10% / -5% steps -> 39 returns >= 30.

    Closes: 100, 110, 104.5, 114.95, ... All CRYPTO -> factor 365.
    """
    asset = seeded_universe["assets"]["BTCUSDT"]
    provider = seeded_universe["providers"][1]
    assert deposit(client, portfolio_id, "10000").status_code == 201
    assert buy(client, portfolio_id, str(asset.id), "1", "100").status_code == 201

    closes = [100.0]
    for i in range(39):
        closes.append(closes[-1] * (1.10 if i % 2 == 0 else 0.95))
    store_daily(db_session, asset.id, provider.id, closes)

    response = client.get(f"/api/v1/portfolios/{portfolio_id}/risk?window=90")
    assert response.status_code == 200, response.text
    raw = response.text
    data = response.json()["data"]

    assert data["data_status"] == "AVAILABLE", data["data_status_reason"]
    assert data["return_count"] == 39
    assert data["method"] == "current_weights_buy_and_hold_approximation"
    assert data["risk_free_rate"] == "0.000000000000"
    assert data["annualization"] == "crypto_calendar_365"
    assert data["annualization_factor"] == 365
    for key in ("volatility", "annualized_volatility", "max_drawdown", "var_95", "cvar_99"):
        assert data["metrics"][key] is not None
        assert isinstance(data["metrics"][key], str)
    # VaR must be the loss side (negative) for this alternating series.
    assert D(data["metrics"]["var_95"]) < 0
    assert D(data["metrics"]["cvar_95"]) <= D(data["metrics"]["var_95"])
    assert D(data["metrics"]["max_drawdown"]) <= 0
    # Single holding -> 100% weight, reported as a percentage like allocation.
    assert data["holdings"][0]["weight"] == "100.0000000000"
    # No JSON floats anywhere in the payload.
    import re

    assert not re.search(r'":\s*-?\d+\.\d+', raw), raw


def test_endpoint_window_validation(client, portfolio_id):
    assert client.get(f"/api/v1/portfolios/{portfolio_id}/risk?window=5").status_code == 422
    assert client.get(f"/api/v1/portfolios/{portfolio_id}/risk?window=5000").status_code == 422


def test_endpoint_unknown_portfolio(client):
    response = client.get(f"/api/v1/portfolios/{uuid.uuid4()}/risk")
    assert response.status_code == 404