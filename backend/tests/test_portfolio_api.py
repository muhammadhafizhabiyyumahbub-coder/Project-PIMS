"""Stage B integration tests: Portfolio API over real PostgreSQL (TestClient).

All expected numbers are hand-computed and written in comments. Candle fixtures
are SYNTHETIC (labeled), never presented as market data.
"""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.database.models import MarketCandle
from app.database.repositories import portfolio as repo
from app.main import app


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def portfolio_id(client):
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "API Test Portfolio", "base_currency": "USD"},
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def deposit(client, pid, amount, key=None):
    headers = {"Idempotency-Key": key} if key else {}
    return client.post(
        "/api/v1/transactions",
        json={"portfolio_id": pid, "transaction_type": "DEPOSIT", "gross_amount": amount},
        headers=headers,
    )


def trade(client, pid, ttype, asset_id, qty, price, fee, key=None):
    headers = {"Idempotency-Key": key} if key else {}
    return client.post(
        "/api/v1/transactions",
        json={
            "portfolio_id": pid,
            "asset_id": asset_id,
            "transaction_type": ttype,
            "quantity": qty,
            "price": price,
            "fee": fee,
        },
        headers=headers,
    )


def store_candle(db_session, asset_id, provider_id, close, open_time):
    """One SYNTHETIC candle (test fixture)."""
    db_session.add(
        MarketCandle(
            asset_id=asset_id,
            provider_id=provider_id,
            timeframe="1h",
            open_time=open_time,
            close_time=open_time + timedelta(hours=1),
            open_price=close,
            high_price=close,
            low_price=close,
            close_price=close,
            volume=Decimal("1000"),
            currency="USD",
            candle_status="CLOSED",
        )
    )
    db_session.commit()


# ---------------------------------------------------------------------------
# 1. Full flow: create -> DEPOSIT -> BUY -> SELL -> holdings -> valuation
# ---------------------------------------------------------------------------


def test_full_flow(client, db_session, portfolio_id, seeded_universe):
    asset = seeded_universe["assets"]["BTCUSDT"]
    aid = str(asset.id)
    pid = portfolio_id

    # DEPOSIT 1000.00 → cash 1000
    r = deposit(client, pid, "1000.00")
    assert r.status_code == 201
    # BUY 2 @ 100 fee 2 → cost 202, cash 1000-202 = 798, basis 202, avg 101
    r = trade(client, pid, "BUY", aid, "2", "100.00", "2.00")
    assert r.status_code == 201
    # BUY 3 @ 110 fee 3 → cost 333, cash 798-333 = 465, basis 535, avg 107
    r = trade(client, pid, "BUY", aid, "3", "110.00", "3.00")
    assert r.status_code == 201
    # SELL 1 @ 120 fee 1 → proceeds 119, cash 465+119 = 584
    # allocated cost = 1*107 = 107 → realized = 119-107 = 12
    # remaining: qty 4, basis 535-107 = 428, avg still 107
    r = trade(client, pid, "SELL", aid, "1", "120.00", "1.00")
    assert r.status_code == 201

    # --- holdings (api-spec §10.2 shape) ---
    r = client.get(f"/api/v1/portfolios/{pid}/holdings")
    assert r.status_code == 200
    holdings = r.json()["data"]
    assert len(holdings) == 1
    h = holdings[0]
    assert h["symbol"] == "BTCUSDT"
    assert h["quantity"] == "4"
    assert h["average_cost"] == "107"
    assert h["cost_basis"] == "428"

    # SYNTHETIC candle (test fixture): close 105, fresh → COMPLETE valuation.
    provider = seeded_universe["providers"][1]  # YAHOO
    store_candle(db_session, asset.id, provider.id, Decimal("105"), datetime.now(timezone.utc) - timedelta(hours=1))

    # --- valuation ---
    r = client.get(f"/api/v1/portfolios/{pid}/valuation")
    assert r.status_code == 200
    v = r.json()["data"]
    assert v["valuation_status"] == "COMPLETE"
    # market value = 4 * 105 = 420; unrealized = 420 - 428 = -8
    # realized 12 + unrealized -8 = total pnl 4; total value = 584 + 420 = 1004
    assert v["cash_value"] == "584"
    assert v["invested_value"] == "420"
    assert v["total_value"] == "1004"
    assert v["realized_pnl"] == "12"
    assert v["unrealized_pnl"] == "-8"
    assert v["positions"][0]["market_value"] == "420"
    assert v["positions"][0]["unrealized_pnl"] == "-8"


def test_money_fields_are_numeric_strings(client, db_session, portfolio_id, seeded_universe):
    """api-spec §5.3: money must not leave the API as JSON floats."""
    asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio_id
    r = trade(client, pid, "BUY", str(asset.id), "0.5", "100.123456789012", "0.5")
    assert r.status_code == 201
    body = r.json()["data"]
    for field in ("quantity", "price", "gross_amount", "fee"):
        assert isinstance(body[field], str), f"{field} must be a string, got {type(body[field])}"
    assert body["price"] == "100.123456789012"
    assert body["gross_amount"] == "50.061728394506"
    # Prove JSON never saw a float: parse raw bytes for a float-looking price.
    raw = r.content.decode()
    assert '"price":100.' not in raw and '"price": 100.' not in raw

    r = client.get(f"/api/v1/portfolios/{pid}/holdings")
    h = r.json()["data"][0]
    for field in ("quantity", "average_cost", "cost_basis"):
        assert isinstance(h[field], str)

    # Replay: 1000 deposit, BUY 0.5 @ 100.123456789012 fee 0.5 (no candle yet)
    r = client.get(f"/api/v1/portfolios/{pid}/valuation")
    v = r.json()["data"]
    assert v["valuation_status"] == "PARTIAL"
    for field in ("cash_value", "realized_pnl"):
        assert isinstance(v[field], str)
    assert v["invested_value"] is None  # honest: no price stored yet

    # SYNTHETIC candle (test fixture) → COMPLETE; every money field a string.
    provider = seeded_universe["providers"][1]
    store_candle(db_session, asset.id, provider.id, Decimal("100"), datetime.now(timezone.utc))
    v = client.get(f"/api/v1/portfolios/{pid}/valuation").json()["data"]
    assert v["valuation_status"] == "COMPLETE"
    for field in ("cash_value", "invested_value", "realized_pnl", "unrealized_pnl", "total_value"):
        assert isinstance(v[field], str), f"{field} must be a string"


def test_pnl_consistency_value_vs_deposits(client, db_session, portfolio_id, seeded_universe):
    """realized + unrealized must equal total_value - net external cash flow."""
    asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio_id
    deposit(client, pid, "1000.00")
    trade(client, pid, "BUY", str(asset.id), "2", "100.00", "2.00")
    trade(client, pid, "SELL", str(asset.id), "1", "120.00", "1.00")
    # cash after: 1000 - 202 + 119 = 917; holdings: qty 1, basis 202, avg 101... wait:
    # basis after BUY = 202; SELL 1 removes allocated 101 → basis 101, realized 119-101 = 18
    provider = seeded_universe["providers"][1]
    store_candle(db_session, asset.id, provider.id, Decimal("110"), datetime.now(timezone.utc))

    v = client.get(f"/api/v1/portfolios/{pid}/valuation").json()["data"]
    # market value = 1*110 = 110; unrealized = 110-101 = 9; total = 917+110 = 1027
    assert v["valuation_status"] == "COMPLETE"
    realized = Decimal(v["realized_pnl"])
    unrealized = Decimal(v["unrealized_pnl"])
    total_value = Decimal(v["total_value"])
    deposits = Decimal("1000.00")  # only external cash flow
    assert realized + unrealized == total_value - deposits  # 18 + 9 == 1027 - 1000
    assert (realized, unrealized) == (Decimal("18"), Decimal("9"))


def test_cash_ledger_matches_transaction_replay(client, portfolio_id, seeded_universe):
    asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio_id
    deposit(client, pid, "1000.00")
    trade(client, pid, "BUY", str(asset.id), "2", "100.00", "2.00")
    trade(client, pid, "SELL", str(asset.id), "1", "120.00", "1.00")
    txs = client.get("/api/v1/transactions", params={"portfolio_id": pid}).json()["data"]
    # Replay cash from the API's own transactions, same convention as cash_ledger:
    # BUY outflow -(gross+fee), SELL inflow gross-fee, DEPOSIT inflow gross-fee.
    total = Decimal("0")
    for t in txs:
        fee = Decimal(t["fee"])
        if t["transaction_type"] == "BUY":
            total -= Decimal(t["gross_amount"]) + fee
        elif t["transaction_type"] == "SELL":
            total += Decimal(t["gross_amount"]) - fee
        elif t["transaction_type"] in ("DEPOSIT", "DIVIDEND", "INTEREST"):
            total += Decimal(t["gross_amount"]) - fee
        else:  # WITHDRAWAL, FEE
            total -= Decimal(t["gross_amount"]) + fee
    assert total == Decimal("917")  # 1000 - 202 + 119
    v = client.get(f"/api/v1/portfolios/{pid}/valuation").json()["data"]
    assert Decimal(v["cash_value"]) == total  # API cash == replay of API transactions


# ---------------------------------------------------------------------------
# 2. Idempotency (api-spec §22)
# ---------------------------------------------------------------------------


def test_idempotent_replay_does_not_double_book(client, portfolio_id):
    pid = portfolio_id
    r1 = deposit(client, pid, "500.00", key="dep-1")
    assert r1.status_code == 201
    r2 = deposit(client, pid, "500.00", key="dep-1")
    assert r2.status_code == 200
    assert r2.json()["data"]["idempotent_replay"] is True
    assert r1.json()["data"]["id"] == r2.json()["data"]["id"]
    txs = client.get("/api/v1/transactions", params={"portfolio_id": pid}).json()["data"]
    assert len(txs) == 1
    v = client.get(f"/api/v1/portfolios/{pid}/valuation").json()["data"]
    assert v["cash_value"] == "500"  # not 1000


def test_idempotency_key_payload_conflict(client, portfolio_id):
    pid = portfolio_id
    deposit(client, pid, "500.00", key="k-1")
    # Same key, different payload → conflict, not a silent replay.
    r = deposit(client, pid, "900.00", key="k-1")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CONFLICT"
    txs = client.get("/api/v1/transactions", params={"portfolio_id": pid}).json()["data"]
    assert len(txs) == 1


def test_transaction_without_key_is_not_idempotent(client, portfolio_id):
    pid = portfolio_id
    deposit(client, pid, "10.00")
    r = deposit(client, pid, "10.00")
    assert r.status_code == 201
    txs = client.get("/api/v1/transactions", params={"portfolio_id": pid}).json()["data"]
    assert len(txs) == 2  # two deliberate distinct deposits
    assert client.get(f"/api/v1/portfolios/{pid}/valuation").json()["data"]["cash_value"] == "20"


# ---------------------------------------------------------------------------
# 3. Validation: correct error, zero rows written
# ---------------------------------------------------------------------------


def test_validation_errors_write_nothing(client, portfolio_id, seeded_universe):
    asset = seeded_universe["assets"]["BTCUSDT"]
    aid = str(asset.id)
    pid = portfolio_id
    unknown_asset = str(uuid.uuid4())
    unknown_portfolio = str(uuid.uuid4())

    cases = [
        # (payload tweak, expected status, expected error code)
        ({"transaction_type": "BUY", "asset_id": aid, "quantity": "-2", "price": "100"}, 422, "BUSINESS_RULE_ERROR"),
        ({"transaction_type": "BUY", "asset_id": aid, "quantity": "0", "price": "100"}, 422, "BUSINESS_RULE_ERROR"),
    ]
    for override, status, code in cases:
        payload = {"portfolio_id": pid, "fee": "0", **override}
        r = client.post("/api/v1/transactions", json=payload)
        assert r.status_code == status, payload
        assert r.json()["error"]["code"] == code, payload

    # Unknown asset → 404
    r = trade(client, pid, "BUY", unknown_asset, "1", "100", "0")
    assert r.status_code == 404

    # Unknown portfolio → 404
    r = trade(client, unknown_portfolio, "BUY", str(asset.id), "1", "100", "0")
    assert r.status_code == 404

    # Currency mismatch → 422
    r = client.post(
        "/api/v1/transactions",
        json={
            "portfolio_id": pid,
            "asset_id": str(asset.id),
            "transaction_type": "BUY",
            "quantity": "1",
            "price": "100",
            "fee": "0",
            "currency": "IDR",
        },
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "BUSINESS_RULE_ERROR"

    # SELL exceeding holdings (zero held) → 422
    r = trade(client, pid, "SELL", str(asset.id), "1", "100", "0")
    assert r.status_code == 422

    # Nothing was written: no transactions, no ledger rows, no holdings.
    txs = client.get("/api/v1/transactions", params={"portfolio_id": pid}).json()["data"]
    assert txs == []
    v = client.get(f"/api/v1/portfolios/{pid}/valuation").json()["data"]
    assert v["valuation_status"] == "UNAVAILABLE"
    assert Decimal(v["cash_value"]) == 0
    assert v["positions"] == []


# ---------------------------------------------------------------------------
# 4. Honesty of valuation status
# ---------------------------------------------------------------------------


def test_valuation_partial_without_price(client, portfolio_id, seeded_universe):
    """No stored candle → PARTIAL, price None, no invented numbers (spec §8.4)."""
    asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio_id
    deposit(client, pid, "1000.00")
    trade(client, pid, "BUY", str(asset.id), "1", "100.00", "0")

    r = client.get(f"/api/v1/portfolios/{pid}/valuation")
    assert r.status_code == 200
    v = r.json()["data"]
    assert v["valuation_status"] == "PARTIAL"
    assert v["positions"][0]["price_status"] == "MISSING"
    assert v["positions"][0]["market_price"] is None
    assert v["positions"][0]["market_value"] is None
    assert v["total_value"] is None  # not cash+0 — never a fake total
    assert v["cash_value"] == "900"  # 1000 deposit - 100 BUY; cash itself is exact
    # Holdings endpoint states the same truth.
    h = client.get(f"/api/v1/portfolios/{pid}/holdings").json()
    assert h["meta"]["valuation_status"] == "PARTIAL"
    assert h["data"][0]["market_price"] is None


def test_valuation_stale_price_not_used(client, db_session, portfolio_id, seeded_universe):
    asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio_id
    deposit(client, pid, "1000.00")
    trade(client, pid, "BUY", str(asset.id), "1", "100.00", "0")
    # 3h old > 2h freshness policy → STALE; price shown but flagged, value withheld.
    provider = seeded_universe["providers"][1]
    store_candle(db_session, asset.id, provider.id, Decimal("130"), datetime.now(timezone.utc) - timedelta(hours=3))

    v = client.get(f"/api/v1/portfolios/{pid}/valuation").json()["data"]
    assert v["valuation_status"] == "STALE"
    assert v["positions"][0]["price_status"] == "STALE"
    assert v["positions"][0]["market_price"] == "130"  # displayed, not used
    assert v["positions"][0]["market_value"] is None
    assert v["total_value"] is None


# ---------------------------------------------------------------------------
# 5. 404s and portfolio lifecycle
# ---------------------------------------------------------------------------


def test_unknown_portfolio_404(client):
    missing = uuid.uuid4()
    for path in (
        f"/api/v1/portfolios/{missing}",
        f"/api/v1/portfolios/{missing}/holdings",
        f"/api/v1/portfolios/{missing}/valuation",
    ):
        assert client.get(path).status_code == 404
    assert client.patch(f"/api/v1/portfolios/{missing}", json={"name": "x"}).status_code == 404
    assert client.delete(f"/api/v1/portfolios/{missing}").status_code == 404


def test_unknown_holding_404(client, portfolio_id):
    r = client.get(f"/api/v1/portfolios/{portfolio_id}/holdings/{uuid.uuid4()}")
    assert r.status_code == 404


def test_portfolio_lifecycle(client, portfolio_id):
    pid = portfolio_id
    r = client.patch(f"/api/v1/portfolios/{pid}", json={"name": "Renamed", "status": "ACTIVE"})
    assert r.status_code == 200
    assert r.json()["data"]["name"] == "Renamed"

    # Empty portfolio deletable.
    r = client.delete(f"/api/v1/portfolios/{pid}")
    assert r.status_code == 200
    assert client.get(f"/api/v1/portfolios/{pid}").status_code == 404


def test_portfolio_with_transactions_cannot_be_deleted(client, portfolio_id):
    pid = portfolio_id
    deposit(client, pid, "100.00")
    r = client.delete(f"/api/v1/portfolios/{pid}")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "CONFLICT"
    # Archival is the supported path.
    r = client.patch(f"/api/v1/portfolios/{pid}", json={"status": "ARCHIVED"})
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "ARCHIVED"


# ---------------------------------------------------------------------------
# 6. Transactions list + cursor pagination (api-spec §19)
# ---------------------------------------------------------------------------


def test_transactions_pagination_deterministic(client, portfolio_id):
    pid = portfolio_id
    for i in range(3):
        deposit(client, pid, f"{100 + i}.00")
    r = client.get("/api/v1/transactions", params={"portfolio_id": pid, "limit": 2})
    assert r.status_code == 200
    body = r.json()
    assert len(body["data"]) == 2
    assert body["meta"]["pagination"]["has_more"] is True
    cursor = body["meta"]["pagination"]["next_cursor"]
    r2 = client.get("/api/v1/transactions", params={"portfolio_id": pid, "limit": 2, "cursor": cursor})
    page2 = r2.json()
    assert len(page2["data"]) == 1
    assert page2["meta"]["pagination"]["has_more"] is False
    assert page2["meta"]["pagination"]["next_cursor"] is None
    ids_page1 = {t["id"] for t in body["data"]}
    ids_page2 = {t["id"] for t in page2["data"]}
    assert not ids_page1 & ids_page2  # no duplicates across pages


def test_transaction_type_filter(client, portfolio_id):
    pid = portfolio_id
    deposit(client, pid, "100.00")
    asset = "00000000-0000-0000-0000-000000000000"
    r = client.get("/api/v1/transactions", params={"portfolio_id": pid, "transaction_type": "DEPOSIT"})
    assert all(t["transaction_type"] == "DEPOSIT" for t in r.json()["data"])
    r = client.get("/api/v1/transactions", params={"portfolio_id": pid, "transaction_type": "NOT_A_TYPE"})
    assert r.status_code == 422
