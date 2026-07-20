from __future__ import annotations

import asyncio
from typing import Any

from fastapi import WebSocket


class DeviceConnectionHub:
    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._result_waiters: dict[str, asyncio.Future[dict[str, Any]]] = {}

    @property
    def online_client_ids(self) -> set[str]:
        return set(self._connections)

    async def register(self, client_id: str, websocket: WebSocket) -> None:
        previous = self._connections.get(client_id)
        self._connections[client_id] = websocket
        if previous is not None and previous is not websocket:
            await previous.close(code=1000, reason="客户端已在其他连接上线")

    def unregister(self, client_id: str, websocket: WebSocket) -> None:
        if self._connections.get(client_id) is websocket:
            self._connections.pop(client_id, None)

    async def send_command(
        self,
        *,
        client_id: str,
        payload: dict[str, Any],
        timeout_seconds: float = 30,
    ) -> dict[str, Any]:
        websocket = self._connections.get(client_id)
        if websocket is None:
            raise RuntimeError("客户端当前不在线")
        request_id = str(payload["request_id"])
        loop = asyncio.get_running_loop()
        waiter: asyncio.Future[dict[str, Any]] = loop.create_future()
        self._result_waiters[request_id] = waiter
        try:
            await websocket.send_json(payload)
            return await asyncio.wait_for(waiter, timeout=timeout_seconds)
        finally:
            self._result_waiters.pop(request_id, None)

    def resolve_result(self, payload: dict[str, Any]) -> None:
        request_id = str(payload.get("request_id", "") or "")
        waiter = self._result_waiters.get(request_id)
        if waiter is not None and not waiter.done():
            waiter.set_result(payload)
