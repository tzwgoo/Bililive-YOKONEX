from __future__ import annotations

import json
from typing import Any, Awaitable, Callable
from urllib.parse import quote
from urllib.parse import urlparse

import websockets


DEFAULT_DOUYIN_WS_BASE_URL = "ws://127.0.0.1:1088"


class DouyinWsClient:
    def __init__(self, *, base_url: str = DEFAULT_DOUYIN_WS_BASE_URL) -> None:
        self.base_url = self._normalize_base_url(base_url)
        self._ws: Any | None = None

    async def connect_and_consume(
        self,
        *,
        room_id: str,
        on_message: Callable[[dict[str, Any]], Awaitable[None]],
        base_url: str = "",
    ) -> None:
        ws_url = self._build_ws_url(room_id=room_id, base_url=base_url or self.base_url)
        async with websockets.connect(ws_url, ping_interval=None) as ws:
            self._ws = ws
            try:
                async for raw_message in ws:
                    message = self._decode_message(raw_message)
                    if message is None:
                        continue
                    await on_message(message)
            finally:
                self._ws = None

    async def disconnect(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None

    def _build_ws_url(self, *, room_id: str, base_url: str) -> str:
        normalized_base_url = self._normalize_base_url(base_url)
        normalized_room_id = quote(str(room_id or "").strip(), safe="")
        if not normalized_room_id:
            raise ValueError("抖音直播间标识不能为空")
        if "/ws/" in normalized_base_url:
            return normalized_base_url.rstrip("/") + "/" + normalized_room_id
        return normalized_base_url.rstrip("/") + "/ws/" + normalized_room_id

    def _normalize_base_url(self, value: str) -> str:
        normalized = str(value or DEFAULT_DOUYIN_WS_BASE_URL).strip().rstrip("/")
        parsed = urlparse(normalized)
        if parsed.scheme not in {"ws", "wss"} or not parsed.netloc:
            raise ValueError("抖音 WebSocket 服务地址必须是 ws:// 或 wss://")
        return normalized

    def _decode_message(self, raw_message: Any) -> dict[str, Any] | None:
        if isinstance(raw_message, bytes):
            raw_message = raw_message.decode("utf-8", errors="ignore")
        if not isinstance(raw_message, str):
            return None
        if raw_message.strip().lower() == "pong":
            return None
        decoded = json.loads(raw_message)
        return decoded if isinstance(decoded, dict) else None
