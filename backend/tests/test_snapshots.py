"""Stage F: SELL net-proceeds guard + manual portfolio snapshots.

All expected numbers are hand-computed and written in comments.
SYNTHETIC fixtures only (from seeded universe); never presented as market data.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.database.models import MarketCandle
from app.main import app

D = Decimal

STALE_AGE_SECONDS = 7200  # portfolio/valuation.py PRICE_FRESHNESS_SECONDS


@pytest.fixture()
def portfolio_id(client):
    response = client.post(
        "/api/v1/portfolios",
        json={"name": "Snapshot Test Portfolio", "base_currency": "USD"},
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]

@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


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
            open_price=close,
            high_price=close,
            low_price=close,
            close_price=close,
            volume=1000.0,
            quote_volume=close * Decimal("1000"),
            candle_status="CLOSED",
            open_time=open_time,
            close_time=open_time + timedelta(hours=1),
            currency="USD",
        )
    )
    db_session.commit()


# ---------------------------------------------------------------------------
# 1. SELL net-proceeds guard
# ---------------------------------------------------------------------------

def test_sell_net_proceeds_zero_is_rejected(client, portfolio_id, seeded_universe):
    """SELL 1 @ 100 with fee 100 → net proceeds 0 → 422 FEE_EXCEEDS_PROCEEDS.

    Owner decision A (2026-11-17): a SELL whose net proceeds (quantity*price -
    fee) are <= 0 is rejected before anything is written.
    """
    asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio_id
    deposit(client, pid, "1000", key="stage-f-sell-dep")
    trade(client, pid, "BUY", str(asset.id), "1", "100", "0", key="stage-f-sell-buy")

    r = trade(client, pid, "SELL", str(asset.id), "1", "100", "100", key="stage-f-sell-fee-eq")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "BUSINESS_RULE_ERROR"
    assert r.json()["error"]["details"][0]["code"] == "FEE_EXCEEDS_PROCEEDS"

    # Nothing survived the rejection: only deposit + buy exist; holding still 1.
    txs = client.get("/api/v1/transactions", params={"portfolio_id": pid}).json()["data"]
    assert [t["transaction_type"] for t in txs] == ["DEPOSIT", "BUY"]
    holdings = client.get(f"/api/v1/portfolios/{pid}/holdings").json()["data"]
    assert holdings[0]["quantity"] == "1"


def test_sell_fee_just_below_proceeds_passes(client, portfolio_id, seeded_universe):
    """SELL 1 @ 100 with fee 99.999999999999 → net 0.000000000001 > 0 → lolos."""
    asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio_id
    deposit(client, pid, "1000", key="stage-f-sell2-dep")
    trade(client, pid, "BUY", str(asset.id), "1", "100", "0", key="stage-f-sell2-buy")

    r = trade(
        client, pid, "SELL", str(asset.id), "1", "100", "99.999999999999", key="stage-f-sell2"
    )
    assert r.status_code == 201, r.text
    holdings = client.get(f"/api/v1/portfolios/{pid}/holdings").json()["data"]
    assert holdings[0]["quantity"] == "0"


# ---------------------------------------------------------------------------
# 2. Snapshot endpoints
# ---------------------------------------------------------------------------

def test_snapshot_complete_stores_correct_numbers(client, db_session, portfolio_id, seeded_universe):
    """COMPLETE snapshot stores hand-computed values as strings.

    Deposit 1000; BUY 1 @ 100 fee 0 → cash 900, holding 1 @ avg 100.
    Candle close 120 → market value 120; invested 120; total 1020; unrealized 20.
    """
    asset = seeded_universe["assets"]["BTCUSDT"]
    provider = seeded_universe["providers"][1]  # YAHOO
    pid = portfolio_id
    deposit(client, pid, "1000", key="stage-f-snap-dep")
    trade(client, pid, "BUY", str(asset.id), "1", "100", "0", key="stage-f-snap-buy")
    store_candle(
        db_session,
        asset.id,
        provider.id,
        Decimal("120"),
        datetime.now(timezone.utc) - timedelta(hours=1),
    )

    r = client.post(f"/api/v1/portfolios/{pid}/snapshots", headers={"Idempotency-Key": "snap-1"})
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["portfolio_id"] == pid
    assert body["cash_value"] == "900"
    assert body["invested_value"] == "120"
    assert body["total_value"] == "1020"
    assert body["reporting_currency"] == "USD"
    assert body["valuation_status"] == "COMPLETE"
    assert body["status_reason"] == SNAPSHOT_REASONS["COMPLETE"]
    assert len(body["positions"]) == 1
    assert body["positions"][0]["symbol"] == "BTCUSDT"
    assert body["positions"][0]["market_price"] == "120"
    assert body["positions"][0]["market_value"] == "120"


def test_snapshot_idempotent_replay(client, db_session, portfolio_id, seeded_universe):
    """Dua POST dengan idempotency key yang sama → satu baris, created=False."""
    asset = seeded_universe["assets"]["BTCUSDT"]
    provider = seeded_universe["providers"][1]
    pid = portfolio_id
    deposit(client, pid, "1000", key="stage-f-snapid-dep")
    trade(client, pid, "BUY", str(asset.id), "1", "100", "0", key="stage-f-snapid-buy")
    store_candle(db_session, asset.id, provider.id, Decimal("120"), datetime.now(timezone.utc))

    r1 = client.post(f"/api/v1/portfolios/{pid}/snapshots", headers={"Idempotency-Key": "snap-idem"})
    assert r1.status_code == 201
    assert r1.json()["data"]["idempotent_replay"] is False
    first_id = r1.json()["data"]["id"]

    r2 = client.post(f"/api/v1/portfolios/{pid}/snapshots", headers={"Idempotency-Key": "snap-idem"})
    assert r2.status_code == 200
    assert r2.json()["data"]["idempotent_replay"] is True
    assert r2.json()["data"]["id"] == first_id

    rows = client.get(f"/api/v1/portfolios/{pid}/snapshots").json()["data"]
    assert len(rows) == 1  # tidak ada duplikat menyesatkan


def test_snapshot_without_key_always_creates(client, db_session, portfolio_id, seeded_universe):
    """Tanpa idempotency key, setiap POST adalah snapshot manual baru."""
    asset = seeded_universe["assets"]["BTCUSDT"]
    provider = seeded_universe["providers"][1]
    pid = portfolio_id
    deposit(client, pid, "1000", key="stage-f-snapnk-dep")
    trade(client, pid, "BUY", str(asset.id), "1", "100", "0", key="stage-f-snapnk-buy")
    store_candle(db_session, asset.id, provider.id, Decimal("120"), datetime.now(timezone.utc))

    r1 = client.post(f"/api/v1/portfolios/{pid}/snapshots")
    r2 = client.post(f"/api/v1/portfolios/{pid}/snapshots")
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["data"]["id"] != r2.json()["data"]["id"]
    rows = client.get(f"/api/v1/portfolios/{pid}/snapshots").json()["data"]
    assert len(rows) == 2


def test_snapshot_partial_stores_nulls(client, db_session, portfolio_id, seeded_universe):
    """PARTIAL (harga tidak tersedia): nilai tidak tersedia disimpan null,
    bukan disamarkan sebagai nol."""
    asset = seeded_universe["assets"]["BTCUSDT"]
    pid = portfolio_id
    deposit(client, pid, "1000", key="stage-f-partial-dep")
    trade(client, pid, "BUY", str(asset.id), "1", "100", "0", key="stage-f-partial-buy")
    # Tidak ada candle → semua posisi MISSING → PARTIAL.

    r = client.post(f"/api/v1/portfolios/{pid}/snapshots", headers={"Idempotency-Key": "snap-partial"})
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["valuation_status"] == "PARTIAL"
    assert body["cash_value"] == "900"
    assert body["invested_value"] is None
    assert body["total_value"] is None
    assert body["status_reason"] == SNAPSHOT_REASONS["PARTIAL"]


def test_snapshot_stale_stores_nulls(client, db_session, portfolio_id, seeded_universe):
    """STALE (harga lebih tua dari kebijakan segar): total denganheld, null.

    Candle open_time must be older than PRICE_FRESHNESS_SECONDS (7200s) counted
    from close_time (open_time + 1h), so it is placed 10860s in the past:
    close_time = now-7260s → age 7260s > 7200s → STALE.
    """
    asset = seeded_universe["assets"]["BTCUSDT"]
    provider = seeded_universe["providers"][1]
    pid = portfolio_id
    old = datetime.now(timezone.utc) - timedelta(seconds=STALE_AGE_SECONDS + 3660)
    deposit(client, pid, "1000", key="stage-f-stale-dep")
    trade(client, pid, "BUY", str(asset.id), "1", "100", "0", key="stage-f-stale-buy")
    store_candle(db_session, asset.id, provider.id, Decimal("120"), open_time=old)

    r = client.post(f"/api/v1/portfolios/{pid}/snapshots", headers={"Idempotency-Key": "snap-stale"})
    assert r.status_code == 201
    body = r.json()["data"]
    assert body["valuation_status"] == "STALE"
    assert body["cash_value"] == "900"
    assert body["invested_value"] is None
    assert body["total_value"] is None
    assert body["status_reason"] == SNAPSHOT_REASONS["STALE"]


def test_snapshot_list_ordered_and_paginated(client, db_session, portfolio_id, seeded_universe):
    """Daftar snapshot berurutan waktu (ascending) dengan limit/cursor."""
    asset = seeded_universe["assets"]["BTCUSDT"]
    provider = seeded_universe["providers"][1]
    pid = portfolio_id
    deposit(client, pid, "1000", key="stage-f-pag-dep")
    trade(client, pid, "BUY", str(asset.id), "1", "100", "0", key="stage-f-pag-buy")
    store_candle(db_session, asset.id, provider.id, Decimal("120"), datetime.now(timezone.utc))

    client.post(f"/api/v1/portfolios/{pid}/snapshots", headers={"Idempotency-Key": "pag-1"})
    client.post(f"/api/v1/portfolios/{pid}/snapshots", headers={"Idempotency-Key": "pag-2"})

    page = client.get(f"/api/v1/portfolios/{pid}/snapshots?limit=1").json()
    assert len(page["data"]) == 1
    assert page["meta"]["pagination"]["has_more"] is True
    cursor = page["meta"]["pagination"]["next_cursor"]
    assert cursor is not None

    page2 = client.get(f"/api/v1/portfolios/{pid}/snapshots?limit=1&cursor={cursor}").json()
    assert len(page2["data"]) == 1
    assert page2["meta"]["pagination"]["has_more"] is False
    assert page["data"][0]["id"] != page2["data"][0]["id"]

    all_rows = client.get(f"/api/v1/portfolios/{pid}/snapshots").json()["data"]
    stamps = [r["snapshot_at"] for r in all_rows]
    assert stamps == sorted(stamps)  # stabil ascending


def test_snapshot_404_missing_portfolio(client):
    pid = "00000000-0000-0000-0000-000000000000"
    r = client.post(f"/api/v1/portfolios/{pid}/snapshots")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"
    r = client.get(f"/api/v1/portfolios/{pid}/snapshots")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


SNAPSHOT_REASONS = {
    "COMPLETE": "All held positions priced from fresh stored candles; totals are final.",
    "PARTIAL": "At least one position has no stored price; unavailable values are stored as NULL.",
    "STALE": "Stored prices are older than the freshness policy; values are withheld, not estimated.",
    "UNAVAILABLE": "No transactions or holdings; only cash (if any) is meaningful.",
}
