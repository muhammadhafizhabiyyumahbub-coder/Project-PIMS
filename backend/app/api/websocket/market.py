"""Market feed WebSocket channel (market.quote / market.candle / market.status).

Data is read from stored candles only: no provider is contacted per client and no
stream exists yet, so every message states is_realtime=false / source=rest_poll.
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session, sessionmaker

from app.core.db import get_session_factory
from app.data.validation.freshness import freshness_status
from app.database.models import Asset, DataProvider, MarketCandle

router = APIRouter(tags=["WebSocket"])

POLL_INTERVAL_SECONDS = 3.0
SUPPORTED_CHANNELS = {"market.quote", "market.candle", "market.status"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def envelope(event: str, data: dict) -> dict:
    return {
        "protocol_version": "1",
        "event": event,
        "event_id": str(uuid.uuid4()),
        "timestamp": _now_iso(),
        "data": data,
    }


def error_envelope(request_id: str | None, code: str, message: str) -> dict:
    return envelope("error", {"request_id": request_id, "code": code, "message": message})


def _feed_status(freshness: str) -> str:
    """REST-polled data can never be LIVE: fresh stored data is DELAYED."""
    if freshness == "STALE":
        return "STALE"
    if freshness == "LIVE":
        return "DELAYED"
    return "UNAVAILABLE"


def _latest_quote(session: Session, asset_id, symbol: str, currency: str | None) -> dict:
    now = datetime.now(timezone.utc)
    row = (
        session.query(MarketCandle, DataProvider.code.label("provider_code"))
        .join(DataProvider, MarketCandle.provider_id == DataProvider.id)
        .filter(MarketCandle.asset_id == asset_id)
        .order_by(MarketCandle.open_time.desc())
        .first()
    )
    quote = {
        "asset_id": str(asset_id),
        "symbol": symbol,
        "last_price": None,
        "bid": None,
        "ask": None,
        "currency": currency or "USD",
        "provider": "NONE",
        "source_timestamp": None,
        "freshness": "UNKNOWN",
        "freshness_status": "UNKNOWN",
        "is_realtime": False,
        "source": "rest_poll",
        "feed_status": "UNAVAILABLE",
        "data_timestamp": None,
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
    }
    if row is None:
        return quote

    candle, provider_code = row
    data_ts = candle.close_time or candle.open_time
    freshness = freshness_status(data_ts, now, candle.timeframe)
    quote.update(
        {
            "last_price": str(candle.close_price),
            "currency": candle.currency,
            "provider": provider_code,
            "source_timestamp": candle.close_time.isoformat() if candle.close_time else candle.open_time.isoformat(),
            "freshness": freshness,
            "freshness_status": freshness,
            "feed_status": _feed_status(freshness),
            "data_timestamp": data_ts.isoformat(),
        }
    )
    return quote


def _latest_candle(session: Session, asset_id, symbol: str, timeframe: str) -> dict | None:
    now = datetime.now(timezone.utc)
    candle = (
        session.query(MarketCandle)
        .filter_by(asset_id=asset_id, timeframe=timeframe)
        .order_by(MarketCandle.open_time.desc())
        .first()
    )
    if candle is None:
        return None
    data_ts = candle.close_time or candle.open_time
    freshness = freshness_status(data_ts, now, timeframe)
    return {
        "asset_id": str(asset_id),
        "symbol": symbol,
        "timeframe": timeframe,
        "candle": {
            "time": int(candle.open_time.timestamp()),
            "open": str(candle.open_price),
            "high": str(candle.high_price),
            "low": str(candle.low_price),
            "close": str(candle.close_price),
            "volume": str(candle.volume) if candle.volume is not None else "0",
        },
        "provider": "REST_PUBLIC",
        "freshness": freshness,
        "freshness_status": freshness,
        "is_closed": candle.candle_status == "CLOSED",
        "is_realtime": False,
        "source": "rest_poll",
        "data_timestamp": data_ts.isoformat(),
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
    }


def _status_from_quote(quote: dict) -> dict:
    return {
        "provider": quote["provider"],
        "market": "CRYPTO",
        "connection_status": "DISCONNECTED",
        "freshness": quote["freshness"],
        "feed_status": quote["feed_status"],
        "last_received_at": quote["data_timestamp"],
        "is_realtime": False,
        "source": "rest_poll",
        "poll_interval_seconds": POLL_INTERVAL_SECONDS,
    }


def _snapshot(factory: sessionmaker, channel: str, sub: dict) -> dict | None:
    with factory() as session:
        if channel == "market.quote":
            data = _latest_quote(session, sub["asset_id"], sub["symbol"], sub["currency"])
        elif channel == "market.candle":
            data = _latest_candle(session, sub["asset_id"], sub["symbol"], sub["timeframe"])
        else:
            data = _status_from_quote(
                _latest_quote(session, sub["asset_id"], sub["symbol"], sub["currency"])
            )
    return envelope(channel, data) if data is not None else None


def _change_key(channel: str, data: dict) -> tuple:
    if channel == "market.candle":
        candle = data.get("candle")
        if candle is None:
            return ("UNAVAILABLE",)
        return (candle["time"], candle["close"], data["is_closed"])
    if channel == "market.status":
        return (data["feed_status"], data["last_received_at"])
    return (data["last_price"], data["data_timestamp"], data["feed_status"])


async def _lookup_asset(factory: sessionmaker, asset_id: str | None, symbol: str | None) -> dict | None:
    def _load():
        with factory() as session:
            if asset_id:
                try:
                    parsed = uuid.UUID(asset_id)
                except (ValueError, AttributeError, TypeError):
                    return None
                asset = session.get(Asset, parsed)
            elif symbol:
                asset = session.query(Asset).filter(Asset.symbol == symbol.upper()).first()
            else:
                return None
            if asset is None:
                return None
            return {
                "asset_id": asset.id,
                "symbol": asset.symbol,
                "currency": asset.quote_currency,
            }

    return await asyncio.to_thread(_load)


@router.websocket("/api/v1/ws/market")
async def websocket_market(
    websocket: WebSocket,
    factory: sessionmaker = Depends(get_session_factory),
):
    await websocket.accept()
    send_lock = asyncio.Lock()

    async def send(message: dict) -> None:
        async with send_lock:
            await websocket.send_text(json.dumps(message, default=str))

    await send(
        envelope(
            "connection.accepted",
            {
                "client_id": str(uuid.uuid4()),
                "channel": "market",
                "is_realtime": False,
                "source": "rest_poll",
                "poll_interval_seconds": POLL_INTERVAL_SECONDS,
            },
        )
    )

    subscriptions: dict[str, dict] = {}
    stop_event = asyncio.Event()

    async def sender_loop() -> None:
        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=POLL_INTERVAL_SECONDS)
                break
            except asyncio.TimeoutError:
                pass

            current = list(subscriptions.items())

            def _poll():
                updates = []
                with factory() as session:
                    for sub_id, sub in current:
                        channel = sub["channel"]
                        if channel == "market.quote":
                            data = _latest_quote(session, sub["asset_id"], sub["symbol"], sub["currency"])
                        elif channel == "market.candle":
                            data = _latest_candle(session, sub["asset_id"], sub["symbol"], sub["timeframe"])
                            if data is None:
                                continue
                        else:
                            data = _status_from_quote(
                                _latest_quote(session, sub["asset_id"], sub["symbol"], sub["currency"])
                            )
                        key = _change_key(channel, data)
                        if key != sub["last_key"]:
                            sub["last_key"] = key
                            updates.append((sub_id, envelope(channel, data)))
                return updates

            try:
                updates = await asyncio.to_thread(_poll)
            except Exception:
                break
            for sub_id, message in updates:
                if sub_id in subscriptions:
                    await send(message)

    async def command_loop() -> None:
        while True:
            raw = await websocket.receive_text()
            try:
                command = json.loads(raw)
            except json.JSONDecodeError:
                await send(error_envelope(None, "INVALID_MESSAGE", "Message must be JSON."))
                continue
            if not isinstance(command, dict):
                await send(error_envelope(None, "INVALID_MESSAGE", "Message must be a JSON object."))
                continue

            action = command.get("action")
            request_id = command.get("request_id")

            if action == "ping":
                await send(envelope("pong", {"request_id": request_id}))
            elif action == "subscribe":
                channel = command.get("channel")
                if channel not in SUPPORTED_CHANNELS:
                    await send(error_envelope(request_id, "UNKNOWN_CHANNEL", f"Unsupported channel {channel}."))
                    continue
                params = command.get("params") or {}
                requested_id = params.get("asset_id")
                requested_symbol = params.get("symbol")
                if not requested_id and not requested_symbol:
                    await send(
                        error_envelope(
                            request_id,
                            "INVALID_SUBSCRIPTION",
                            "params.asset_id or params.symbol is required.",
                        )
                    )
                    continue
                ref = await _lookup_asset(factory, requested_id, requested_symbol)
                if ref is None:
                    await send(
                        error_envelope(
                            request_id,
                            "ASSET_NOT_FOUND",
                            f"Asset {requested_id or requested_symbol} not found.",
                        )
                    )
                    continue

                subscription_id = str(uuid.uuid4())
                sub = {**ref, "channel": channel, "timeframe": params.get("timeframe", "1h")}
                snapshot = await asyncio.to_thread(_snapshot, factory, channel, sub)
                if snapshot is None:
                    # No stored candle for this symbol/timeframe: keep the
                    # subscription but say so explicitly in the snapshot.
                    sub = {**ref, "channel": "market.candle", "timeframe": sub["timeframe"]}
                    snapshot = envelope(
                        "market.candle",
                        {
                            "asset_id": str(ref["asset_id"]),
                            "symbol": ref["symbol"],
                            "timeframe": sub["timeframe"],
                            "candle": None,
                            "provider": "NONE",
                            "freshness": "UNKNOWN",
                            "is_closed": None,
                            "is_realtime": False,
                            "source": "rest_poll",
                            "feed_status": "UNAVAILABLE",
                            "data_timestamp": None,
                            "poll_interval_seconds": POLL_INTERVAL_SECONDS,
                        },
                    )
                sub["last_key"] = _change_key(channel, snapshot["data"])
                subscriptions[subscription_id] = sub

                await send(
                    envelope(
                        "subscription.confirmed",
                        {
                            "request_id": request_id,
                            "subscription_id": subscription_id,
                            "channel": channel,
                            "status": "ACTIVE",
                            "is_realtime": False,
                            "source": "rest_poll",
                            "poll_interval_seconds": POLL_INTERVAL_SECONDS,
                        },
                    )
                )
                await send(snapshot)
            elif action == "unsubscribe":
                subscription_id = command.get("subscription_id")
                if subscriptions.pop(subscription_id, None) is None:
                    await send(
                        error_envelope(request_id, "INVALID_SUBSCRIPTION", "Subscription not found.")
                    )
                else:
                    await send(
                        envelope(
                            "subscription.closed",
                            {
                                "request_id": request_id,
                                "subscription_id": subscription_id,
                                "status": "CLOSED",
                            },
                        )
                    )
            else:
                await send(error_envelope(request_id, "INVALID_MESSAGE", f"Unknown action {action}."))

    sender = asyncio.create_task(sender_loop())
    try:
        await command_loop()
    except WebSocketDisconnect:
        pass
    finally:
        stop_event.set()
        sender.cancel()
