from __future__ import annotations

from typing import Any, Awaitable, Callable

import aiohttp  # noqa: F401


class ThirdPartyWsClient:
    def __init__(
        self,
        *,
        live_danmaku_factory: Callable[..., Any] | None = None,
        client_selector: Callable[[str], None] | None = None,
        selected_client_getter: Callable[[], tuple[str, Any]] | None = None,
        registered_clients_getter: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.live_danmaku_factory = live_danmaku_factory
        self.client_selector = client_selector
        self.selected_client_getter = selected_client_getter
        self.registered_clients_getter = registered_clients_getter
        self._live_danmaku: Any | None = None

    async def connect_and_consume(
        self,
        *,
        room_id: int,
        on_message: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        self.ensure_supported_client_selected()
        live_danmaku = self._create_live_danmaku(room_id)
        self._live_danmaku = live_danmaku

        for event_name in (
            "DANMU_MSG",
            "SEND_GIFT",
            "COMBO_SEND",
            "GUARD_BUY",
            "SUPER_CHAT_MESSAGE",
            "SUPER_CHAT_MESSAGE_JPN",
            "USER_TOAST_MSG",
            "LIKE_INFO_V3_CLICK",
            "LIKE_INFO_V3_UPDATE",
            "INTERACT_WORD",
            "INTERACT_WORD_V2",
        ):
            self._register_handler(
                live_danmaku=live_danmaku,
                event_name=event_name,
                on_message=on_message,
            )

        try:
            await live_danmaku.connect()
        finally:
            self._live_danmaku = None

    async def disconnect(self) -> None:
        if self._live_danmaku is not None:
            await self._live_danmaku.disconnect()
            self._live_danmaku = None

    def _create_live_danmaku(self, room_id: int) -> Any:
        if self.live_danmaku_factory is not None:
            return self.live_danmaku_factory(room_id)

        from bilibili_api.live import LiveDanmaku

        return LiveDanmaku(room_id, debug=False, max_retry=5, retry_after=1)

    def ensure_supported_client_selected(self) -> None:
        selector = self.client_selector
        getter = self.selected_client_getter
        registered_getter = self.registered_clients_getter

        if selector is None or getter is None or registered_getter is None:
            from bilibili_api import get_registered_clients, get_selected_client, select_client

            selector = selector or select_client
            getter = getter or get_selected_client
            registered_getter = registered_getter or get_registered_clients

        current_name = ""
        try:
            current_name, _ = getter()
        except Exception:
            current_name = ""

        if current_name in {"aiohttp", "curl_cffi"}:
            return

        registered_clients = registered_getter()
        for candidate in ("aiohttp", "curl_cffi"):
            if candidate in registered_clients:
                selector(candidate)
                return

        raise RuntimeError("第三方房间消息流需要安装 aiohttp 或 curl_cffi 作为 WebSocket 请求后端")

    def _register_handler(
        self,
        *,
        live_danmaku: Any,
        event_name: str,
        on_message: Callable[[dict[str, Any]], Awaitable[None]],
    ) -> None:
        @live_danmaku.on(event_name)
        async def _handler(event: dict[str, Any]) -> None:
            raw_message = event.get("data", event)
            if not isinstance(raw_message, dict):
                return
            message = dict(raw_message)
            message.setdefault("cmd", event_name)
            await on_message(message)
