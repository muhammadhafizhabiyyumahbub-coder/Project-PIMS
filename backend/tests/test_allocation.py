"""Stage J: Allocation Engine tests.

All expected numbers are hand-computed and written in comments.
Decimal only; money/weights leave the API as decimal strings, never JSON floats.
Nothing is persisted to analytics tables this round.
"""
import re
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.database.models import MarketCandle
from app.engines.allocation.allocation import (
    AllocationInput,
    PositionInput,
    compute_allocation,
    serialize_weight,
)
from app.main import app

D = Decimal


def _pos(asset_id, symbol, market_value, cls="CRYPTO", market="CRYPTO", currency="USDT"):
    return PositionInput(
        asset_id=asset_id,
        symbol=symbol,
        name=symbol,
        asset_class=cls,
        market=market,
        currency=currency,
        quantity=D("1"),
        market_price=D("1"),
        price_status="AVAILABLE",
        price_time=datetime(2026, 1, 1, tzinfo=UTC),
        market_value=market_value,
    )


def _unpriced(asset_id, symbol, cls="CRYPTO", market="CRYPTO", currency="USDT", cost_basis=None):
    return PositionInput(
        asset_id=asset_id,
        symbol=symbol,
        name=symbol,
        asset_class=cls,
        market=market,
        currency=currency,
        quantity=D("1"),
        market_price=D("1"),
        price_status="MISSING",
        price_time=None,
        market_value=None,
        cost_basis=cost_basis,
    )


def _input(positions, cash_value=D("0"), status="COMPLETE", currency="USD"):
    return AllocationInput(
        portfolio_id=uuid.uuid4(),
        reporting_currency=currency,
        valuation_timestamp=datetime(2026, 11, 17, tzinfo=UTC),
        valuation_status=status,
        cash_value=cash_value,
        positions=list(positions),
    )


# ---------------------------------------------------------------------------
# 1. Two assets + cash, all priced: weights right, coverage 100%.
# ---------------------------------------------------------------------------


def test_two_assets_plus_cash_coverage_100_percent():
    # cash 100, asset A 300, asset B 600 -> valued total 1000.
    # weights: A 30%, B 60%, cash 10%; coverage 3 of 3 components = 100%.
    aid_a, aid_b = uuid.uuid4(), uuid.uuid4()
    res = compute_allocation(
        _input([_pos(aid_a, "A", D("300")), _pos(aid_b, "B", D("600"))], cash_value=D("100"))
    )

    assert res.data_status == "COMPLETE"
    assert res.coverage["total_components"] == 3
    assert res.coverage["covered_components"] == 3
    assert res.coverage["unvalued_components"] == 0
    assert res.coverage["coverage_percentage"] == D("100")

    by_name = {s.name: s for s in res.categories["asset_class"]}
    assert by_name["CRYPTO"].market_value == D("900")
    assert by_name["CRYPTO"].weight == D("90")
    assert by_name["Cash"].market_value == D("100")
    assert by_name["Cash"].weight == D("10")

    assets = {a.symbol: a for a in res.categories["individual_asset"]}
    assert assets["A"].weight == D("30")
    assert assets["B"].weight == D("60")

    # largest holding is B (600); top 3 / 5 / 10 == 30 + 60 = 90%.
    assert res.concentration["largest_holding_symbol"] == "B"
    assert res.concentration["largest_holding_weight"] == D("60")
    assert res.concentration["top_3_weight"] == D("90")
    assert res.concentration["top_5_weight"] == D("90")
    assert res.concentration["top_10_weight"] == D("90")
    assert res.concentration["largest_sector"] is None


# ---------------------------------------------------------------------------
# 2. One asset without a price: coverage < 100%, weight stays null, reason present.
# ---------------------------------------------------------------------------


def test_one_unpriced_asset_coverage_below_100_and_weight_null():
    # cash 100, asset A priced 300, asset B has no price -> valued total 400.
    # weights: A 75%, cash 25%, B null (never 0, never renormalised).
    # coverage: 2 covered components of 3 = 66.66...%.
    aid_a, aid_b = uuid.uuid4(), uuid.uuid4()
    res = compute_allocation(
        _input(
            [_pos(aid_a, "A", D("300")), _unpriced(aid_b, "B", cost_basis=D("100"))],
            cash_value=D("100"),
            status="PARTIAL",
        )
    )

    assert res.data_status == "PARTIAL"
    assert res.data_status_reason is not None
    assert "no price" in res.data_status_reason

    assert res.coverage["total_components"] == 3
    assert res.coverage["covered_components"] == 2
    assert res.coverage["unvalued_components"] == 1
    assert abs(res.coverage["coverage_percentage"] - D("66.6666666667")) < D("0.0000000001")

    assets = {a.symbol: a for a in res.categories["individual_asset"]}
    assert assets["A"].weight == D("75")
    assert assets["A"].market_value == D("300")
    assert assets["B"].market_value is None
    assert assets["B"].weight is None  # not turned into zero

    # Weights over the priced base (A + cash) sum to 100%: 75% + 25% = 100%.
    cash_weight = res.categories["cash"]["weight"]
    reported = (
        sum((a.weight for a in res.categories["individual_asset"] if a.weight is not None), D("0"))
        + cash_weight
    )
    assert reported == D("100")
    assert res.categories["cash"]["weight"] == D("25")

    # weight_base names the denominator explicitly.
    assert res.weight_base == "priced_components_incl_cash"

    # (a) position coverage: 1 priced holding of 2 = 50%.
    assert res.coverage["position_coverage_percentage"] == D("50")
    # (b) value coverage: priced 300 / (300 + unpriced cost basis 100) = 75%.
    # Cost basis is only a proxy for the unpriced value, not market value.
    assert res.coverage["value_known_percentage"] == D("75")

    # Unpriced positions are listed for audit, cost basis included, no market value.
    unpriced = res.coverage["unpriced_positions"]
    assert len(unpriced) == 1
    assert unpriced[0].symbol == "B"
    assert unpriced[0].asset_id == aid_b
    assert unpriced[0].quantity == D("1")
    assert unpriced[0].cost_basis == D("100")
    # The top-level field is what the endpoint serializes; it must be populated too.
    assert len(res.unpriced_positions) == 1
    assert res.unpriced_positions[0].symbol == "B"


# ---------------------------------------------------------------------------
# 3. Sector/industry unavailable -> null with reason, never invented.
# ---------------------------------------------------------------------------


def test_sector_unavailable_null_with_reason():
    aid = uuid.uuid4()
    res = compute_allocation(_input([_pos(aid, "A", D("300"))], cash_value=D("100")))

    sector = res.categories["sector"]
    assert sector["status"] == "UNAVAILABLE"
    assert sector["reason"] is not None
    assert sector["allocation"] == []
    assert res.concentration["largest_sector"] is None
    assert res.concentration["largest_sector_reason"] is not None


# ---------------------------------------------------------------------------
# 4. Top-N concentration correct by hand.
# ---------------------------------------------------------------------------


def test_top_n_concentration_hand_computed():
    # Values 100, 90, 80, 70, 60, 50 -> total 450.
    # top-3 = (100+90+80)/450 = 60%
    # top-5 = 400/450 = 88.888...%
    # top-10 = 450/450 = 100%
    assets = [uuid.uuid4() for _ in range(6)]
    positions = [_pos(a, f"S{i}", D(str(100 - i * 10))) for i, a in enumerate(assets)]
    res = compute_allocation(_input(positions))

    assert res.concentration["largest_holding_symbol"] == "S0"
    assert abs(res.concentration["largest_holding_weight"] - D("22.2222222222")) < D("0.0000000001")
    assert abs(res.concentration["top_3_weight"] - D("60")) < D("0.0000000001")
    assert abs(res.concentration["top_5_weight"] - D("88.8888888889")) < D("0.0000000001")
    assert abs(res.concentration["top_10_weight"] - D("100")) < D("0.0000000001")


# ---------------------------------------------------------------------------
# 5. No floats anywhere: weights are fixed-scale decimal strings.
# ---------------------------------------------------------------------------


def test_all_weights_are_fixed_scale_decimal_strings():
    aid = uuid.uuid4()
    res = compute_allocation(_input([_pos(aid, "A", D("333.333333333333"))], cash_value=D("0")))
    total = D("333.333333333333")
    weight = D("333.333333333333") / total * D("100")
    assert res.categories["individual_asset"][0].weight == weight
    assert serialize_weight(weight) == "100.0000000000"


# ===========================================================================
# 6. API wiring: read-only GET /portfolios/{id}/allocation over real PostgreSQL.
# ===========================================================================


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def portfolio_id(client):
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "Allocation Test Portfolio", "base_currency": "USD"},
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def deposit(client, pid, amount):
    return client.post(
        "/api/v1/transactions",
        json={"portfolio_id": pid, "transaction_type": "DEPOSIT", "gross_amount": amount},
    )


def trade(client, pid, ttype, asset_id, qty, price, fee):
    return client.post(
        "/api/v1/transactions",
        json={
            "portfolio_id": pid,
            "transaction_type": ttype,
            "asset_id": asset_id,
            "quantity": qty,
            "price": price,
            "fee": fee,
        },
    )


def store_candle(db_session, asset_id, provider_id, close, open_time):
    """One SYNTHETIC candle (test fixture)."""
    db_session.add(
        MarketCandle(
            asset_id=asset_id,
            provider_id=provider_id,
            timeframe="1h",
            open_time=open_time,
            close_time=open_time,
            open_price=close,
            high_price=close,
            low_price=close,
            close_price=close,
            volume=D("1000"),
            currency="USD",
            candle_status="CLOSED",
        )
    )
    db_session.commit()


def test_allocation_endpoint_hand_computed(client, db_session, portfolio_id, seeded_universe):
    # DEPOSIT 1000 -> cash 1000; BUY 2 @ 100 fee 2 -> outflow 202, cash 798,
    # holdings qty 2 cost 202.
    asset = seeded_universe["assets"]["BTCUSDT"]
    assert deposit(client, portfolio_id, "1000.00").status_code == 201
    assert trade(client, portfolio_id, "BUY", str(asset.id), "2", "100.00", "2.00").status_code == 201

    # SYNTHETIC fresh candle close 105 -> market value 2 * 105 = 210.
    provider = seeded_universe["providers"][1]  # YAHOO
    store_candle(db_session, asset.id, provider.id, D("105"), datetime.now(UTC) - timedelta(hours=1))

    response = client.get(f"/api/v1/portfolios/{portfolio_id}/allocation")
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    raw = response.content.decode()

    assert data["data_status"] == "COMPLETE"
    assert data["total_value"] == "1008"   # 798 cash + 210 invested
    assert data["cash_value"] == "798"
    assert data["invested_value"] == "210"
    assert data["coverage"]["coverage_percentage"] == "100.0000000000"
    # Endpoint serializes the top-level unpriced list (empty when all priced).
    assert data["unpriced_positions"] == []

    assets_by_symbol = {a["symbol"]: a for a in data["categories"]["individual_asset"]}
    assert assets_by_symbol["BTCUSDT"]["market_value"] == "210"
    assert assets_by_symbol["BTCUSDT"]["weight"] == "20.8333333333"  # 210/1008 * 100

    cash = data["categories"]["cash"]
    assert cash["weight"] == "79.1666666667"  # 798/1008 * 100

    asset_class = {s["name"]: s for s in data["categories"]["asset_class"]}
    assert asset_class["CRYPTO"]["weight"] == "20.8333333333"
    assert asset_class["Cash"]["weight"] == "79.1666666667"

    # Concentration: only one holding -> top-N all equal its weight.
    assert data["concentration"]["top_3_weight"] == "20.8333333333"
    assert data["concentration"]["largest_holding_symbol"] == "BTCUSDT"

    # Sector must not be invented.
    assert data["categories"]["sector"]["status"] == "UNAVAILABLE"
    assert data["categories"]["sector"]["allocation"] == []
    assert data["concentration"]["largest_sector"] is None

    # No JSON floats: every money/weight is a decimal string. Match only real
    # JSON numeric values (":" followed by digits), so decimal points inside
    # ISO timestamp strings do not false-positive.
    assert not re.search(r'":\s*-?\d+\.\d+', raw), raw
    assert all(isinstance(v, str) or v is None for row in assets_by_symbol.values() for v in row.values())
    assert data["categories"]["individual_asset"][0]["weight"] == "20.8333333333"


def test_allocation_endpoint_lists_unpriced_positions(client, db_session, portfolio_id, seeded_universe):
    # BUY priced BTCUSDT and unpriced SOLUSDT (no candle stored for it).
    btc = seeded_universe["assets"]["BTCUSDT"]
    sol = seeded_universe["assets"]["SOLUSDT"]
    assert deposit(client, portfolio_id, "1000.00").status_code == 201
    assert trade(client, portfolio_id, "BUY", str(btc.id), "2", "100.00", "0").status_code == 201
    assert trade(client, portfolio_id, "BUY", str(sol.id), "5", "20.00", "0").status_code == 201
    provider = seeded_universe["providers"][1]  # YAHOO
    store_candle(db_session, btc.id, provider.id, D("105"), datetime.now(UTC) - timedelta(hours=1))

    response = client.get(f"/api/v1/portfolios/{portfolio_id}/allocation")
    assert response.status_code == 200, response.text
    data = response.json()["data"]

    # One priced holding, one unpriced -> the list must surface it for audit.
    assert data["coverage"]["unvalued_components"] == 1
    assert len(data["unpriced_positions"]) == 1
    unpriced = data["unpriced_positions"][0]
    assert unpriced["symbol"] == "SOLUSDT"
    assert unpriced["quantity"] == "5"
    assert unpriced["cost_basis"] == "100"  # 5 @ 20, cost basis is a proxy not a market value
    assert set(unpriced.keys()) == {"asset_id", "symbol", "quantity", "cost_basis"}

    # Two honest coverage measures, kept distinct and never merged.
    assert data["coverage"]["position_coverage_percentage"] == "50.0000000000"
    assert data["coverage"]["value_known_percentage"] == "67.7419354839"  # 210 / (210 + 100) * 100
    assert data["weight_base"] == "priced_components_incl_cash"
