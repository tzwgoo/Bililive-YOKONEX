from __future__ import annotations

import base64
import json
from typing import Any, Awaitable, Callable
from urllib.parse import quote
from urllib.parse import parse_qsl
from urllib.parse import urlencode
from urllib.parse import urlparse
from urllib.parse import urlunparse

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
        douyin_cookie: str = "",
    ) -> None:
        ws_url = self._build_ws_url(room_id=room_id, base_url=base_url or self.base_url, douyin_cookie=douyin_cookie)
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

    def _build_ws_url(self, *, room_id: str, base_url: str, douyin_cookie: str = "") -> str:
        normalized_base_url = self._normalize_base_url(base_url)
        normalized_room_id = quote(str(room_id or "").strip(), safe="")
        if not normalized_room_id:
            raise ValueError("抖音直播间标识不能为空")
        parsed = urlparse(normalized_base_url)
        path = parsed.path.rstrip("/")
        if "/ws/" in path or path.endswith("/ws"):
            path = path + "/" + normalized_room_id
        else:
            path = path + "/ws/" + normalized_room_id
        query_items = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key not in {"cookie", "cookie_b64"}]
        if douyin_cookie.strip():
            # douyinLive 原生支持 cookie_b64，避免直接把长 Cookie 放进 URL 时被特殊字符截断。
            cookie_b64 = base64.urlsafe_b64encode(douyin_cookie.strip().encode("utf-8")).decode("ascii")
            query_items.append(("cookie_b64", cookie_b64))
        return urlunparse((parsed.scheme, parsed.netloc, path, "", urlencode(query_items), ""))

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
