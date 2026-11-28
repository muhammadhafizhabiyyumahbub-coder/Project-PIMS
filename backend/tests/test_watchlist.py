"""Watchlist API tests (api-spec §17) over real PostgreSQL via TestClient.

Covers CRUD, item add/remove, duplicate handling (§17.2), FK integrity, and
404/409/422 error paths. Rows are truncated by the db_session fixture.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.database.models import Watchlist, WatchlistItem
from app.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _create(client, name="My List", description="watch these"):
    return client.post(
        "/api/v1/watchlists", json={"name": name, "description": description}
    )


def test_create_and_list(client, seeded_universe):
    created = _create(client)
    assert created.status_code == 201
    body = created.json()["data"]
    assert body["name"] == "My List"
    assert body["description"] == "watch these"
    assert body["item_count"] == 0
    assert set(body) >= {"id", "name", "description", "created_at", "updated_at"}

    listed = client.get("/api/v1/watchlists")
    assert listed.status_code == 200
    assert listed.json()["meta"]["count"] == 1
    assert listed.json()["data"][0]["id"] == body["id"]


def test_create_validation_422(client):
    assert client.post("/api/v1/watchlists", json={}).status_code == 422
    assert (
        client.post("/api/v1/watchlists", json={"name": ""}).status_code == 422
    )
    # extra="forbid" rejects unknown fields.
    assert (
        client.post(
            "/api/v1/watchlists", json={"name": "x", "bogus": 1}
        ).status_code
        == 422
    )


def test_get_detail_and_404(client, seeded_universe):
    created = _create(client).json()["data"]
    detail = client.get(f"/api/v1/watchlists/{created['id']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["items"] == []

    assert client.get(f"/api/v1/watchlists/{uuid.uuid4()}").status_code == 404
    assert client.get("/api/v1/watchlists/not-a-uuid").status_code == 404


def test_patch_updates_fields(client, seeded_universe):
    created = _create(client).json()["data"]
    patched = client.patch(
        f"/api/v1/watchlists/{created['id']}",
        json={"name": "Renamed", "description": "new desc"},
    )
    assert patched.status_code == 200
    data = patched.json()["data"]
    assert data["name"] == "Renamed"
    assert data["description"] == "new desc"

    assert (
        client.patch(
            f"/api/v1/watchlists/{uuid.uuid4()}", json={"name": "x"}
        ).status_code
        == 404
    )
    assert (
        client.patch(
            f"/api/v1/watchlists/{created['id']}", json={"name": ""}
        ).status_code
        == 422
    )


def test_delete_watchlist(client, seeded_universe):
    created = _create(client).json()["data"]
    deleted = client.delete(f"/api/v1/watchlists/{created['id']}")
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True
    assert client.get(f"/api/v1/watchlists/{created['id']}").status_code == 404
    assert client.delete(f"/api/v1/watchlists/{uuid.uuid4()}").status_code == 404


def test_add_item_and_duplicate_conflict(client, seeded_universe):
    wl = _create(client).json()["data"]
    btc = seeded_universe["assets"]["BTCUSDT"]

    added = client.post(
        f"/api/v1/watchlists/{wl['id']}/items", json={"asset_id": str(btc.id)}
    )
    assert added.status_code == 201
    assert added.json()["data"]["asset_id"] == str(btc.id)
    assert added.json()["data"]["symbol"] == "BTCUSDT"

    # §17.2: duplicate items handled.
    dup = client.post(
        f"/api/v1/watchlists/{wl['id']}/items", json={"asset_id": str(btc.id)}
    )
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "CONFLICT"

    detail = client.get(f"/api/v1/watchlists/{wl['id']}").json()["data"]
    assert detail["item_count"] == 1
    assert detail["items"][0]["symbol"] == "BTCUSDT"


def test_add_item_unknown_asset_and_watchlist(client, seeded_universe):
    wl = _create(client).json()["data"]
    missing_asset = client.post(
        f"/api/v1/watchlists/{wl['id']}/items",
        json={"asset_id": str(uuid.uuid4())},
    )
    assert missing_asset.status_code == 404

    bad_body = client.post(f"/api/v1/watchlists/{wl['id']}/items", json={})
    assert bad_body.status_code == 422

    btc = seeded_universe["assets"]["BTCUSDT"]
    missing_wl = client.post(
        f"/api/v1/watchlists/{uuid.uuid4()}/items", json={"asset_id": str(btc.id)}
    )
    assert missing_wl.status_code == 404


def test_remove_item(client, seeded_universe):
    wl = _create(client).json()["data"]
    eth = seeded_universe["assets"]["ETHUSDT"]
    client.post(
        f"/api/v1/watchlists/{wl['id']}/items", json={"asset_id": str(eth.id)}
    )

    removed = client.delete(f"/api/v1/watchlists/{wl['id']}/items/{eth.id}")
    assert removed.status_code == 200
    assert removed.json()["data"]["removed"] is True

    again = client.delete(f"/api/v1/watchlists/{wl['id']}/items/{eth.id}")
    assert again.status_code == 404

    assert (
        client.delete(f"/api/v1/watchlists/{wl['id']}/items/not-a-uuid").status_code
        == 404
    )


def test_delete_cascades_items(client, db_session, seeded_universe):
    wl = _create(client).json()["data"]
    btc = seeded_universe["assets"]["BTCUSDT"]
    client.post(
        f"/api/v1/watchlists/{wl['id']}/items", json={"asset_id": str(btc.id)}
    )
    assert db_session.query(WatchlistItem).count() == 1

    client.delete(f"/api/v1/watchlists/{wl['id']}")
    # FK ON DELETE CASCADE removes children (technical-decisions §7.17).
    assert db_session.query(WatchlistItem).count() == 0
    assert db_session.query(Watchlist).count() == 0


def test_unique_constraint_enforced_in_db(db_session, seeded_universe):
    wl = Watchlist(name="db-level")
    db_session.add(wl)
    db_session.flush()
    btc = seeded_universe["assets"]["BTCUSDT"]
    db_session.add(WatchlistItem(watchlist_id=wl.id, asset_id=btc.id))
    db_session.flush()
    db_session.add(WatchlistItem(watchlist_id=wl.id, asset_id=btc.id))
    with pytest.raises(IntegrityError):
        db_session.flush()
    db_session.rollback()
