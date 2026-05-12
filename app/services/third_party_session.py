from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable

from app.models import SessionStatus
from app.services.event_hub import EventHub
from app.third_party.event_mapper import map_third_party_message
from app.third_party.ws_client import ThirdPartyWsClient


LOGGER = logging.getLogger("bili_live.third_party")


class ThirdPartyLiveSessionService:
    def __init__(
        self,
        *,
        event_hub: EventHub,
        gift_dispatcher: Any | None = None,
        ws_client: Any | None = None,
        room_info_fetcher: Callable[[int], Awaitable[dict[str, Any]]] | None = None,
    ) -> None:
        self.event_hub = event_hub
        self.gift_dispatcher = gift_dispatcher
        self.ws_client = ws_client or ThirdPartyWsClient()
        self.room_info_fetcher = room_info_fetcher or self._fetch_room_info
        self.status = SessionStatus.IDLE
        self.room_id = 0
        self.anchor_name = ""
        self.last_error = ""
        self.last_event_at = 0
        self.last_heartbeat_at = 0
        self.last_command_id = ""
        self.last_command_message = ""
        self.trigger_mode = "by_quantity"
        self._consume_task: asyncio.Task | None = None
        self._stop_requested = False

    async def start(self, *, value: str, trigger_mode: str = "by_quantity") -> None:
        room_id = value.strip()
        if not room_id:
            raise ValueError("房间号不能为空")
        if self.status in {SessionStatus.STARTING, SessionStatus.RUNNING, SessionStatus.RECONNECTING}:
            raise ValueError("当前已有会话正在运行")
        try:
            normalized_room_id = int(room_id)
        except ValueError as exc:
            raise ValueError("房间号必须是数字") from exc

        self.room_id = normalized_room_id
        self.trigger_mode = trigger_mode
        if self.gift_dispatcher is not None and hasattr(self.gift_dispatcher, "set_trigger_mode"):
            self.gift_dispatcher.set_trigger_mode(trigger_mode)
        self.anchor_name = ""
        self.last_error = ""
        self.last_command_id = ""
        self.last_command_message = ""
        self.last_event_at = 0
        self._stop_requested = False
        await self._hydrate_room_profile()
        self.status = SessionStatus.STARTING
        self._consume_task = asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        if self.status == SessionStatus.IDLE and self._consume_task is None:
            return

        self.status = SessionStatus.STOPPING
        self._stop_requested = True
        await self.ws_client.disconnect()
        if self._consume_task is not None:
            self._consume_task.cancel()
            try:
                await self._consume_task
            except asyncio.CancelledError:
                pass
            self._consume_task = None
        self.status = SessionStatus.IDLE
        self.room_id = 0
        self.anchor_name = ""

    def get_status_payload(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "message": self.last_error,
            "game_id": "",
            "room_id": self.room_id,
            "anchor_name": self.anchor_name,
            "last_event_at": self.last_event_at,
            "last_heartbeat_at": self.last_heartbeat_at,
            "last_command_id": self.last_command_id,
            "last_command_message": self.last_command_message,
            "trigger_mode": self.trigger_mode,
            "command_dispatch_enabled": bool(
                self.gift_dispatcher is not None and getattr(self.gift_dispatcher, "is_enabled", False)
            ),
            "config_loaded": True,
            "can_start": self.status in {SessionStatus.IDLE, SessionStatus.ERROR},
            "can_stop": self.status in {SessionStatus.STARTING, SessionStatus.RUNNING, SessionStatus.RECONNECTING},
        }

    async def _consume_loop(self) -> None:
        while not self._stop_requested and self.room_id:
            try:
                self.status = SessionStatus.RUNNING
                await self.ws_client.connect_and_consume(
                    room_id=self.room_id,
                    on_message=self._handle_raw_message,
                )
                if self._stop_requested:
                    break
                self.status = SessionStatus.RECONNECTING
                self.last_error = "第三方长连断开，准备重连"
                LOGGER.warning("第三方长连断开 room_id=%s", self.room_id)
                await asyncio.sleep(3)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - 真实联调路径
                if self._stop_requested:
                    break
                self.status = SessionStatus.RECONNECTING
                self.last_error = f"第三方监听异常，准备重连: {exc}"
                LOGGER.warning("第三方监听异常 room_id=%s error=%s", self.room_id, exc)
                await asyncio.sleep(3)

    async def _handle_raw_message(self, message: dict[str, Any]) -> None:
        self.last_event_at = int(time.time())
        event = map_third_party_message(message, room_id=self.room_id)
        if event is None:
            return
        if event.get("event_type") == "gift" and self.gift_dispatcher is not None:
            dispatch_result = await self.gift_dispatcher.dispatch_gift_event(event)
            self.last_command_id = dispatch_result.get("command_id", "")
            self.last_command_message = dispatch_result.get("message", "")
            event["command_dispatch"] = dispatch_result
        self.event_hub.publish(event)

    async def _hydrate_room_profile(self) -> None:
        try:
            room_info = await self.room_info_fetcher(self.room_id)
        except Exception as exc:  # pragma: no cover - 联调容错路径
            LOGGER.warning("第三方房间信息获取失败 room_id=%s error=%s", self.room_id, exc)
            return
        self.anchor_name = self._extract_anchor_name(room_info)

    async def _fetch_room_info(self, room_id: int) -> dict[str, Any]:
        from bilibili_api.live import LiveRoom

        room = LiveRoom(room_id)
        return await room.get_room_info()

    def _extract_anchor_name(self, room_info: dict[str, Any]) -> str:
        candidates = [
            room_info.get("anchor_info", {}).get("base_info", {}).get("uname", ""),
            room_info.get("anchor_info", {}).get("uname", ""),
            room_info.get("room_info", {}).get("uname", ""),
            room_info.get("room_info", {}).get("anchor_name", ""),
        ]
        for candidate in candidates:
            if candidate:
                return str(candidate)
        return ""
