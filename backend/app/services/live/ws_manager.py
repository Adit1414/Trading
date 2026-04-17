from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket
from websockets.client import connect

logger = logging.getLogger(__name__)


class LiveWebSocketManager:
    def __init__(self) -> None:
        self._public_clients: set[WebSocket] = set()
        self._private_clients: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def connect_public(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._public_clients.add(websocket)

    async def connect_private(self, websocket: WebSocket, user_id: str) -> None:
        await websocket.accept()
        async with self._lock:
            self._private_clients[user_id].add(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: str | None = None) -> None:
        async with self._lock:
            self._public_clients.discard(websocket)
            if user_id:
                clients = self._private_clients.get(user_id)
                if clients:
                    clients.discard(websocket)
                    if not clients:
                        self._private_clients.pop(user_id, None)

    async def publish_public(self, event: str, payload: dict[str, Any]) -> None:
        message = json.dumps({"type": event, "payload": payload, "ts": datetime.now(timezone.utc).isoformat()})
        await self._broadcast(self._public_clients.copy(), message)

    async def publish_private(self, user_id: str, event: str, payload: dict[str, Any]) -> None:
        message = json.dumps({"type": event, "payload": payload, "ts": datetime.now(timezone.utc).isoformat()})
        await self._broadcast(self._private_clients.get(user_id, set()).copy(), message)

    async def _broadcast(self, clients: set[WebSocket], message: str) -> None:
        dead: list[WebSocket] = []
        for ws in clients:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._public_clients.discard(ws)
                    for clients_set in self._private_clients.values():
                        clients_set.discard(ws)

    async def start_market_streams(self) -> None:
        if self._tasks:
            return
        streams = {
            "ticker": "wss://data-stream.binance.vision:9443/ws/!ticker@arr",
            "book_depth": "wss://data-stream.binance.vision:9443/ws/btcusdt@depth20@100ms",
            "kline_1m": "wss://data-stream.binance.vision:9443/ws/btcusdt@kline_1m",
            "kline_5m": "wss://data-stream.binance.vision:9443/ws/btcusdt@kline_5m",
            "kline_1h": "wss://data-stream.binance.vision:9443/ws/btcusdt@kline_1h",
        }
        for name, stream_url in streams.items():
            self._tasks[name] = asyncio.create_task(self._pump_binance_stream(name, stream_url))

    async def stop_market_streams(self) -> None:
        for task in self._tasks.values():
            task.cancel()
        self._tasks.clear()

    async def _pump_binance_stream(self, stream_name: str, stream_url: str) -> None:
        while True:
            try:
                async with connect(stream_url, ping_interval=20, ping_timeout=20, open_timeout=20) as ws:
                    logger.info("Connected Binance stream %s", stream_name)
                    async for raw in ws:
                        try:
                            payload = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        await self.publish_public(stream_name, payload)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Stream %s disconnected: %s. Retrying.", stream_name, exc)
                await asyncio.sleep(2)


live_ws_manager = LiveWebSocketManager()
