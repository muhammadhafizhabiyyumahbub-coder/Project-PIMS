"""Asset API tests (api-spec §11) over real PostgreSQL via TestClient.

Most tests are read-only. Only test_exchange_is_market_code_null_without_market
and test_exchange_filters_only_that_market insert rows, which the db_session
fixture truncates after each test. Asset identity is asserted to be the internal
symbol (never a provider symbol).
"""
import uuid

from app.database.models import Asset, Market
import pytest

from app.main import app


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


def test_route_order_search_is_not_an_id(client, seeded_universe):
    """api-spec §11.1: /assets/search must resolve to the search endpoint even
    though /assets/{asset_id} also matches the literal string "search".

    If the declaration order were reversed, "search" would be parsed as an
    asset id and yield 404 instead of a 200 list.
    """
    response = client.get("/api/v1/assets/search", params={"query": "BTC"})
    assert response.status_code == 200
    body = response.json()
    assert "data" in body and "error" not in body
    assert body["data"][0]["symbol"] == "BTCUSDT"

    # Same literal without any filter also stays on the search route.
    assert client.get("/api/v1/assets/search").status_code == 200


def test_list_and_search_assets(client, seeded_universe):
    response = client.get("/api/v1/assets")
    assert response.status_code == 200
    body = response.json()
    symbols = {row["symbol"] for row in body["data"]}
    assert {"BTCUSDT", "ETHUSDT", "SOLUSDT"} <= symbols
    row = next(r for r in body["data"] if r["symbol"] == "BTCUSDT")
    # api-spec §11.3 example shape.
    assert set(row) >= {"id", "symbol", "name", "market", "exchange", "quote_currency"}
    assert row["name"] == "Bitcoin"
    assert row["market"] == "CRYPTO"
    assert row["quote_currency"] == "USDT"
    # exchange = markets.code via assets.market_id (§7.7), not invented.
    assert row["exchange"] == "CRYPTO"

    # Deterministic ordering by symbol.
    assert [r["symbol"] for r in body["data"]] == sorted(r["symbol"] for r in body["data"])


def test_search_by_name_and_symbol(client, seeded_universe):
    by_symbol = client.get("/api/v1/assets/search", params={"query": "eth"}).json()
    assert [r["symbol"] for r in by_symbol["data"]] == ["ETHUSDT"]  # case-insensitive

    by_name = client.get("/api/v1/assets/search", params={"query": "Solana"}).json()
    assert [r["symbol"] for r in by_name["data"]] == ["SOLUSDT"]


def test_search_filters(client, seeded_universe):
    by_market = client.get("/api/v1/assets", params={"market": "CRYPTO"}).json()
    assert len(by_market["data"]) == 3

    by_type = client.get("/api/v1/assets", params={"asset_type": "CRYPTO"}).json()
    assert len(by_type["data"]) == 3

    # Filters that match nothing return an empty list, not an error.
    none = client.get("/api/v1/assets", params={"market": "US_EQUITY"}).json()
    assert none["data"] == []
    assert none["meta"]["pagination"]["has_more"] is False

    # exchange filters on markets.code via assets.market_id (§7.7).
    by_exchange = client.get("/api/v1/assets", params={"exchange": "CRYPTO"}).json()
    assert {r["symbol"] for r in by_exchange["data"]} == {"BTCUSDT", "ETHUSDT", "SOLUSDT"}

    # An unknown exchange yields an empty list, never an error.
    unknown = client.get("/api/v1/assets", params={"exchange": "NOT_A_VENUE"}).json()
    assert unknown["data"] == []


def test_search_no_results(client, seeded_universe):
    response = client.get("/api/v1/assets/search", params={"query": "NOPE-NOTHING"})
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["meta"]["count"] == 0


def test_exchange_is_market_code_null_without_market(client, db_session, seeded_universe):
    """§7.7: exchange = markets.code via assets.market_id; null only when the
    asset has no market_id at all."""
    from app.database.models import Asset

    orphan = Asset(
        symbol="ORPHANIDX",
        name="Orphan Index",
        asset_type="INDEX",
        market_id=None,
        quote_currency="USD",
    )
    db_session.add(orphan)
    db_session.commit()

    with_market = client.get(
        f"/api/v1/assets/{seeded_universe['assets']['BTCUSDT'].id}"
    ).json()["data"]
    assert with_market["market"] == "CRYPTO"
    assert with_market["exchange"] == "CRYPTO"

    without_market = client.get(f"/api/v1/assets/{orphan.id}").json()["data"]
    assert without_market["market"] is None
    assert without_market["exchange"] is None


def test_pagination_limit_and_cursor(client, seeded_universe):
    page1 = client.get("/api/v1/assets", params={"limit": 2}).json()
    assert len(page1["data"]) == 2
    assert page1["meta"]["pagination"]["has_more"] is True
    cursor = page1["meta"]["pagination"]["next_cursor"]
    assert cursor is not None

    page2 = client.get("/api/v1/assets", params={"limit": 2, "cursor": cursor}).json()
    assert len(page2["data"]) == 1
    assert page2["meta"]["pagination"]["has_more"] is False
    assert page2["meta"]["pagination"]["next_cursor"] is None

    ids1 = {r["id"] for r in page1["data"]}
    ids2 = {r["id"] for r in page2["data"]}
    assert not ids1 & ids2  # no overlap between pages
    assert ids1 | ids2 == {str(a.id) for a in seeded_universe["assets"].values()}

    # Bad limits and cursors are rejected, not silently ignored.
    assert client.get("/api/v1/assets", params={"limit": 0}).status_code == 422
    assert client.get("/api/v1/assets", params={"limit": 500}).status_code == 422
    assert client.get("/api/v1/assets", params={"cursor": "not-a-uuid"}).status_code == 422


def test_asset_detail_and_404(client, seeded_universe):
    asset = seeded_universe["assets"]["BTCUSDT"]
    response = client.get(f"/api/v1/assets/{asset.id}")
    assert response.status_code == 200
    body = response.json()["data"]
    assert body["id"] == str(asset.id)
    assert body["symbol"] == "BTCUSDT"
    assert body["market"] == "CRYPTO"
    assert body["exchange"] == "CRYPTO"

    missing = client.get(f"/api/v1/assets/{uuid.uuid4()}")
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "NOT_FOUND"
    assert client.get("/api/v1/assets/not-a-uuid").status_code == 404


def test_internal_identity_is_not_provider_symbol(client, db_session, seeded_universe):
    """schema-spec §4.1: provider symbols are mappings, not asset identity."""
    from app.database.models import ProviderInstrument

    btc = seeded_universe["assets"]["BTCUSDT"]
    provider_symbols = {
        row.provider_symbol
        for row in db_session.query(ProviderInstrument)
        .filter(ProviderInstrument.asset_id == btc.id)
        .all()
    }
    assert provider_symbols == {"BTCUSDT", "BTC-USD"}  # bybit + yahoo mappings differ

    body = client.get(f"/api/v1/assets/{btc.id}").json()["data"]
    # The API exposes only the internal identity, never a provider mapping.
    assert body["symbol"] == "BTCUSDT"
    assert "BTC-USD" not in str(body)
    assert "provider" not in {key.lower() for key in body}


def test_exchange_filters_only_that_market(client, db_session, seeded_universe):
    """exchange=KODE mengembalikan hanya asset di market itu; exclusi terbukti
    dengan asset di market US_EQUITY yang tidak muncul saat exchange=CRYPTO."""
    us_eq = Market(code="US_EQUITY", name="US Equities", market_type="US_EQUITY", country_code="US")
    db_session.add(us_eq)
    db_session.flush()
    db_session.add(Asset(
        symbol="AAPL", name="Apple Inc", asset_type="STOCK",
        market_id=us_eq.id, quote_currency="USD",
    ))
    db_session.commit()

    only_crypto = client.get("/api/v1/assets", params={"exchange": "CRYPTO"}).json()
    assert {r["symbol"] for r in only_crypto["data"]} == {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
    assert all(r["exchange"] == "CRYPTO" for r in only_crypto["data"])

    only_us = client.get("/api/v1/assets", params={"exchange": "US_EQUITY"}).json()
    assert [r["symbol"] for r in only_us["data"]] == ["AAPL"]
    assert all(r["exchange"] == "US_EQUITY" for r in only_us["data"])
