"""Stage E: cash integrity (no margin in MVP).

All expected numbers are hand-computed and written in comments.
SYNTHETIC fixtures only (from seeded universe); never presented as market data.
"""
from decimal import Decimal

import pytest

from app.database.models import Asset
from app.database.repositories import portfolio as repo
from app.main import app

D = Decimal


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def portfolio_id(client):
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "Cash Integrity Test Portfolio", "base_currency": "USD"},
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


def cash(db_session, pid):
    return repo.cash_balance(db_session, pid, "USD")


def test_buy_exact_cash_boundary_passes(client, db_session, portfolio_id, seeded_universe):
    """Boundary test: BUY with cash exactly equal to outflow → accepted, cash 0.

    Deposit 1000. BUY 1 @ 1000 fee 0 → outflow = 1*1000 + 0 = 1000.
    1000 <= 1000 → lolos; saldo cash menjadi 0.
    """
    asset: Asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio_id
    deposit(client, pid, "1000", key="stage-e-boundary-dep")
    r = trade(client, pid, "BUY", str(asset.id), "1", "1000", "0", key="stage-e-boundary-buy")
    assert r.status_code == 201, r.text
    assert cash(db_session, pid) == D("0")


def test_buy_one_unit_short_is_rejected(client, db_session, portfolio_id, seeded_universe):
    """Kurang 1 unit terkecil (1e-12 presisi NUMERIC) → ditolak, tidak ada yang tertulis.

    Deposit 1000. BUY 1 @ 1000 fee 0.000000000001 → outflow = 1000.000000000001.
    1000.000000000001 > 1000 → 422 INSUFFICIENT_CASH. Saldo tetap 1000.
    Tidak ada baris transactions/cash_ledger.
    """
    asset: Asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio_id
    deposit(client, pid, "1000", key="stage-e-short-dep")
    r = trade(
        client, pid, "BUY", str(asset.id), "1", "1000", "0.000000000001", key="stage-e-short-buy"
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "BUSINESS_RULE_ERROR"
    assert r.json()["error"]["details"][0]["code"] == "INSUFFICIENT_CASH"
    assert cash(db_session, pid) == D("1000")
    # Only the DEPOSIT exists; the rejected BUY wrote nothing.
    assert len(repo.list_transactions(db_session, pid)) == 1
    assert len(repo.ledger_entries(db_session, pid)) == 1


def test_second_buy_that_goes_negative_is_rejected(client, db_session, portfolio_id, seeded_universe):
    """Dua BUY berurutan; kedua bikin negatif → ditolak, hanya pertama tercatat.

    Deposit 1000.
    BUY 1 @ 500 fee 0 → outflow 500 ≤ 1000 → lolos; cash 500.
    BUY 1 @ 500 fee 0.000000000001 → outflow 500.000000000001 > 500 → 422.
    Hanya BUY pertama tercatat; cash 500; 1 transaction, 2 ledger entries.
    """
    asset: Asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio_id
    deposit(client, pid, "1000", key="stage-e-seq-dep")
    r1 = trade(client, pid, "BUY", str(asset.id), "1", "500", "0", key="stage-e-seq-buy1")
    assert r1.status_code == 201
    assert cash(db_session, pid) == D("500")
    r2 = trade(
        client, pid, "BUY", str(asset.id), "1", "500", "0.000000000001", key="stage-e-seq-buy2"
    )
    assert r2.status_code == 422
    assert r2.json()["error"]["details"][0]["code"] == "INSUFFICIENT_CASH"
    assert cash(db_session, pid) == D("500")
    # DEPOSIT + first BUY only; the rejected second BUY wrote nothing.
    assert len(repo.list_transactions(db_session, pid)) == 2
    assert len(repo.ledger_entries(db_session, pid)) == 2


def test_sell_is_not_blocked_by_cash_rule(client, db_session, portfolio_id, seeded_universe):
    """SELL menambah cash, tidak terpengaruh aturan out-flow BUY.

    Deposit 1000. BUY 1 @ 100 fee 0 → cash 900, qty 1.
    SELL 1 @ 1000 fee 0 → inflow 1000 → cash 1900. SELL accepted.
    """
    asset: Asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio_id
    deposit(client, pid, "1000", key="stage-e-sell-dep")
    r1 = trade(client, pid, "BUY", str(asset.id), "1", "100", "0", key="stage-e-sell-buy")
    assert r1.status_code == 201
    r2 = trade(client, pid, "SELL", str(asset.id), "1", "1000", "0", key="stage-e-sell")
    assert r2.status_code == 201
    assert cash(db_session, pid) == D("1900")
    holdings = client.get(f"/api/v1/portfolios/{pid}/holdings").json()["data"]
    assert holdings[0]["quantity"] == "0"
