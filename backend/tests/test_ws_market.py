"Stage O: market WebSocket protocol (envelope, subscribe/ping/unsubscribe, honest feed)."

import pytest
from fastapi.testclient import TestClient

from app.main import app

ENVELOPE_FIELDS = {"protocol_version", "event", "event_id", "timestamp", "data"}


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _subscribe(ws, asset_id: str, channel: str = "market.quote", timeframe: str | None = None):
    params = {"asset_id": asset_id}
    if timeframe:
        params["timeframe"] = timeframe
    ws.send_json({"action": "subscribe", "request_id": "req-1", "channel": channel, "params": params})
    return ws.receive_json(), ws.receive_json()


def test_market_ws_accepts_and_states_rest_poll(client):
    with client.websocket_connect("/api/v1/ws/market") as ws:
        accepted = ws.receive_json()
        assert accepted["event"] == "connection.accepted"
        assert ENVELOPE_FIELDS <= set(accepted)
        assert accepted["protocol_version"] == "1"
        assert accepted["data"]["is_realtime"] is False
        assert accepted["data"]["source"] == "rest_poll"
        assert accepted["data"]["poll_interval_seconds"] > 0


def test_market_ws_subscribe_confirms_then_sends_snapshot(client, btc_asset):
    with client.websocket_connect("/api/v1/ws/market") as ws:
        ws.receive_json()  # connection.accepted

        confirmed, snapshot = _subscribe(ws, str(btc_asset.id))

        assert confirmed["event"] == "subscription.confirmed"
        assert ENVELOPE_FIELDS <= set(confirmed)
        assert confirmed["data"]["status"] == "ACTIVE"
        assert confirmed["data"]["channel"] == "market.quote"
        assert confirmed["data"]["subscription_id"]

        assert snapshot["event"] == "market.quote"
        assert ENVELOPE_FIELDS <= set(snapshot)
        data = snapshot["data"]
        assert data["symbol"] == "BTCUSDT"
        assert data["is_realtime"] is False
        assert data["source"] == "rest_poll"
        assert data["last_price"] is not None
        assert data["data_timestamp"] is not None
        assert data["freshness"] in {"LIVE", "STALE", "UNKNOWN"}
        assert data["freshness_status"] == data["freshness"]
        # Stored candles can never be advertised as realtime.
        assert data["feed_status"] in {"DELAYED", "STALE", "UNAVAILABLE"}


def test_market_ws_ping_pong(client):
    with client.websocket_connect("/api/v1/ws/market") as ws:
        ws.receive_json()
        ws.send_json({"action": "ping", "request_id": "ping-1"})
        pong = ws.receive_json()
        assert pong["event"] == "pong"
        assert ENVELOPE_FIELDS <= set(pong)
        assert pong["data"]["request_id"] == "ping-1"


def test_market_ws_candle_snapshot(client, btc_asset):
    with client.websocket_connect("/api/v1/ws/market") as ws:
        ws.receive_json()
        confirmed, snapshot = _subscribe(ws, str(btc_asset.id), "market.candle", "1h")
        assert confirmed["data"]["channel"] == "market.candle"
        assert snapshot["event"] == "market.candle"
        candle = snapshot["data"]["candle"]
        assert set(candle) >= {"time", "open", "high", "low", "close", "volume"}
        assert float(candle["open"]) > 0
        assert snapshot["data"]["is_realtime"] is False


def test_market_ws_status_channel_is_honest(client, btc_asset):
    with client.websocket_connect("/api/v1/ws/market") as ws:
        ws.receive_json()
        _confirmed, status = _subscribe(ws, str(btc_asset.id), "market.status")
        assert status["event"] == "market.status"
        assert status["data"]["is_realtime"] is False
        assert status["data"]["source"] == "rest_poll"
        assert status["data"]["connection_status"] != "CONNECTED"


def test_market_ws_unsubscribe_stops_updates(client, btc_asset):
    with client.websocket_connect("/api/v1/ws/market") as ws:
        ws.receive_json()
        confirmed, _snapshot = _subscribe(ws, str(btc_asset.id))

        ws.send_json(
            {
                "action": "unsubscribe",
                "request_id": "unsub-1",
                "subscription_id": confirmed["data"]["subscription_id"],
            }
        )
        closed = ws.receive_json()
        assert closed["event"] == "subscription.closed"
        assert closed["data"]["status"] == "CLOSED"

        # Connection stays usable and no data events follow the unsubscribe.
        ws.send_json({"action": "ping", "request_id": "ping-after"})
        next_message = ws.receive_json()
        assert next_message["event"] == "pong"


def test_market_ws_subscribe_by_symbol(client, btc_asset):
    with client.websocket_connect("/api/v1/ws/market") as ws:
        ws.receive_json()
        ws.send_json(
            {
                "action": "subscribe",
                "request_id": "req-sym",
                "channel": "market.quote",
                "params": {"symbol": "BTCUSDT"},
            }
        )
        confirmed = ws.receive_json()
        snapshot = ws.receive_json()
        assert confirmed["event"] == "subscription.confirmed"
        assert snapshot["event"] == "market.quote"
        assert snapshot["data"]["symbol"] == "BTCUSDT"


def test_market_ws_unknown_asset_is_reported(client):
    with client.websocket_connect("/api/v1/ws/market") as ws:
        ws.receive_json()
        ws.send_json(
            {
                "action": "subscribe",
                "request_id": "req-x",
                "channel": "market.quote",
                "params": {"asset_id": "not-a-uuid"},
            }
        )
        error = ws.receive_json()
        assert error["event"] == "error"
        assert ENVELOPE_FIELDS <= set(error)
        assert error["data"]["code"] == "ASSET_NOT_FOUND"
        assert error["data"]["request_id"] == "req-x"

        ws.send_json({"action": "ping", "request_id": "still-open"})
        assert ws.receive_json()["event"] == "pong"


def test_market_ws_symbol_without_data_reports_unavailable(client, db_session):
    from app.data.storage.universe import ensure_universe
    from app.database.models import MarketCandle

    db_session.query(MarketCandle).delete()
    db_session.commit()
    universe = ensure_universe(db_session)
    asset = universe["assets"]["BTCUSDT"]  # no candles stored for this fixture

    with client.websocket_connect("/api/v1/ws/market") as ws:
        ws.receive_json()
        confirmed, snapshot = _subscribe(ws, str(asset.id))

        assert confirmed["event"] == "subscription.confirmed"
        assert snapshot["event"] == "market.quote"
        data = snapshot["data"]
        assert data["last_price"] is None
        assert data["feed_status"] == "UNAVAILABLE"
        assert data["freshness"] == "UNKNOWN"
        assert data["data_timestamp"] is None
        assert data["is_realtime"] is False


def test_market_ws_rejects_unknown_channel_and_bad_message(client):
    with client.websocket_connect("/api/v1/ws/market") as ws:
        ws.receive_json()
        ws.send_json({"action": "subscribe", "request_id": "r", "channel": "portfolio.valuation"})
        error = ws.receive_json()
        assert error["data"]["code"] == "UNKNOWN_CHANNEL"

        ws.send_text("not json")
        bad = ws.receive_json()
        assert bad["data"]["code"] == "INVALID_MESSAGE"

        ws.send_json({"action": "dance", "request_id": "r"})
        unknown = ws.receive_json()
        assert unknown["data"]["code"] == "INVALID_MESSAGE"
