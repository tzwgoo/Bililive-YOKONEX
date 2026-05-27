from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from app.config import Settings
from app.models import SessionStatus
from app.services.event_hub import EventHub


LOGGER = logging.getLogger("bili_live.session")


class OpenLiveSessionService:
    def __init__(
        self,
        *,
        settings: Settings | None,
        event_hub: EventHub,
        api_client: Any,
        ws_client: Any,
        gift_dispatcher: Any | None = None,
        danmaku_dispatcher: Any | None = None,
        bluetooth_dispatcher: Any | None = None,
        config_error: str = "",
    ) -> None:
        self.settings = settings
        self.event_hub = event_hub
        self.api_client = api_client
        self.ws_client = ws_client
        self.gift_dispatcher = gift_dispatcher
        self.danmaku_dispatcher = danmaku_dispatcher
        self.bluetooth_dispatcher = bluetooth_dispatcher
        self.config_error = config_error
        self.status = SessionStatus.IDLE
        self.game_id = ""
        self.room_id = 0
        self.anchor_name = ""
        self.last_error = ""
        self.last_command_id = ""
        self.last_command_message = ""
        self.last_event_at = 0
        self.last_heartbeat_at = 0
        self.output_mode = "im"
        self.trigger_mode = "by_quantity"
        self._heartbeat_task: asyncio.Task | None = None
        self._consume_task: asyncio.Task | None = None
        self._interaction_ended = False

    async def start(
        self,
        *,
        value: str,
        output_mode: str = "im",
        trigger_mode: str = "by_quantity",
        like_multiple: int = 100,
        danmaku_enabled: bool = False,
        danmaku_keywords: str = "",
        danmaku_command_id: str = "",
        danmaku_cooldown_seconds: int = 0,
    ) -> None:
        code = value.strip()
        if self.config_error:
            raise ValueError(self.config_error)
        if not code:
            raise ValueError("主播身份码不能为空")
        if self.settings is None or self.api_client is None:
            raise ValueError("服务配置不完整，无法启动监听")
        if self.status in {SessionStatus.STARTING, SessionStatus.RUNNING, SessionStatus.RECONNECTING}:
            raise ValueError("当前已有会话正在运行")

        self.output_mode = str(output_mode or "im")
        self.trigger_mode = trigger_mode
        if self.gift_dispatcher is not None and hasattr(self.gift_dispatcher, "set_trigger_mode"):
            self.gift_dispatcher.set_trigger_mode(trigger_mode)
        if self.gift_dispatcher is not None and hasattr(self.gift_dispatcher, "set_like_multiple"):
            self.gift_dispatcher.set_like_multiple(like_multiple)
        if self.danmaku_dispatcher is not None and hasattr(self.danmaku_dispatcher, "configure"):
            self.danmaku_dispatcher.configure(
                enabled=danmaku_enabled,
                keywords=danmaku_keywords,
                command_id=danmaku_command_id,
                cooldown_seconds=danmaku_cooldown_seconds,
            )
        if self.bluetooth_dispatcher is not None and hasattr(self.bluetooth_dispatcher, "configure"):
            self.bluetooth_dispatcher.configure(
                danmaku_enabled=danmaku_enabled,
                danmaku_keywords=danmaku_keywords,
                danmaku_cooldown_seconds=danmaku_cooldown_seconds,
            )
        self.status = SessionStatus.STARTING
        self.last_error = ""
        self.last_command_id = ""
        self.last_command_message = ""
        self._interaction_ended = False
        if self.gift_dispatcher is not None and hasattr(self.gift_dispatcher, "reset_runtime_state"):
            self.gift_dispatcher.reset_runtime_state()
        if self.danmaku_dispatcher is not None and hasattr(self.danmaku_dispatcher, "reset_runtime_state"):
            self.danmaku_dispatcher.reset_runtime_state()
        if self.bluetooth_dispatcher is not None and hasattr(self.bluetooth_dispatcher, "reset_runtime_state"):
            self.bluetooth_dispatcher.reset_runtime_state()
        start_payload = await self.api_client.start(app_id=self.settings.app_id, code=code)
        data = start_payload.get("data", {})
        game_info = data.get("game_info", {})
        ws_info = data.get("websocket_info", {})
        anchor_info = data.get("anchor_info", {})

        self.game_id = game_info.get("game_id", "")
        self.room_id = int(anchor_info.get("room_id", 0) or 0)
        self.anchor_name = anchor_info.get("uname", "")

        auth_body = ws_info.get("auth_body", "")
        wss_links = ws_info.get("wss_link", [])
        if not self.game_id or not auth_body or not wss_links:
            self.status = SessionStatus.ERROR
            self.last_error = "启动响应缺少必要长连信息"
            raise ValueError(self.last_error)

        LOGGER.info("启动监听成功 room_id=%s game_id=%s anchor=%s", self.room_id, self.game_id, self.anchor_name)
        self.status = SessionStatus.RUNNING
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._consume_task = asyncio.create_task(
            self._consume_loop(wss_links=wss_links, auth_body=auth_body)
        )

    async def stop(self) -> None:
        if self.status == SessionStatus.IDLE:
            return

        LOGGER.info("停止监听 room_id=%s game_id=%s", self.room_id, self.game_id)
        self.status = SessionStatus.STOPPING
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
        if self._consume_task is not None:
            self._consume_task.cancel()
            self._consume_task = None

        if self.game_id and self.settings is not None and self.api_client is not None:
            await self.api_client.end(app_id=self.settings.app_id, game_id=self.game_id)

        if hasattr(self.ws_client, "disconnect"):
            await self.ws_client.disconnect()

        self.game_id = ""
        self.room_id = 0
        self.anchor_name = ""
        self.status = SessionStatus.IDLE

    def get_status_payload(self) -> dict[str, Any]:
        message = self.last_error or self.config_error
        return {
            "status": self.status.value,
            "message": message,
            "game_id": self.game_id,
            "room_id": self.room_id,
            "anchor_name": self.anchor_name,
            "last_event_at": self.last_event_at,
            "last_heartbeat_at": self.last_heartbeat_at,
            "last_command_id": self.last_command_id,
            "last_command_message": self.last_command_message,
            "trigger_mode": self.trigger_mode,
            "command_dispatch_enabled": bool(
                (self.gift_dispatcher is not None and getattr(self.gift_dispatcher, "is_enabled", False))
                or (self.danmaku_dispatcher is not None and getattr(self.danmaku_dispatcher, "is_enabled", False))
            ),
            "config_loaded": not bool(self.config_error),
            "can_start": self.status in {SessionStatus.IDLE, SessionStatus.ERROR},
            "can_stop": self.status in {SessionStatus.STARTING, SessionStatus.RUNNING, SessionStatus.RECONNECTING},
        }

    async def _heartbeat_loop(self) -> None:
        while self.status == SessionStatus.RUNNING and self.game_id:
            try:
                await self.api_client.heartbeat(game_id=self.game_id)
                self.last_heartbeat_at = int(time.time())
                LOGGER.info("项目心跳成功 game_id=%s", self.game_id)
            except Exception as exc:  # pragma: no cover - 真实联调路径
                self.status = SessionStatus.ERROR
                self.last_error = f"项目心跳失败: {exc}"
                LOGGER.error("项目心跳失败 game_id=%s error=%s", self.game_id, exc)
                return
            await asyncio.sleep(20)

    async def _consume_loop(self, *, wss_links: list[str], auth_body: str) -> None:
        try:
            while self.status in {SessionStatus.RUNNING, SessionStatus.RECONNECTING}:
                try:
                    await self.ws_client.connect_and_consume(
                        wss_links=wss_links,
                        auth_body=auth_body,
                        on_event=self._handle_event,
                    )
                    if self._interaction_ended or self.status == SessionStatus.IDLE:
                        break
                except asyncio.CancelledError:
                    raise
                except Exception as exc:  # pragma: no cover - 网络联调路径
                    self.status = SessionStatus.RECONNECTING
                    self.last_error = f"长连断开，准备重连: {exc}"
                    LOGGER.warning("长连断开，准备重连 game_id=%s error=%s", self.game_id, exc)
                    await asyncio.sleep(3)
                    if self._interaction_ended:
                        break
                    if self.status == SessionStatus.RECONNECTING:
                        self.status = SessionStatus.RUNNING
                    continue
                break
        except asyncio.CancelledError:  # pragma: no cover - 关闭路径
            raise

    async def _handle_event(self, event: dict[str, Any]) -> None:
        self.last_event_at = int(time.time())
        if event.get("cmd") == "LIVE_OPEN_PLATFORM_INTERACTION_END":
            self._interaction_ended = True
            self.last_error = event.get("payload", {}).get("message", "互动场次已结束")
            LOGGER.warning("收到互动结束事件 game_id=%s", self.game_id)
            if self._heartbeat_task is not None:
                self._heartbeat_task.cancel()
                self._heartbeat_task = None
            await self.ws_client.disconnect()
            self.game_id = ""
            self.room_id = 0
            self.anchor_name = ""
            self.status = SessionStatus.IDLE
            self.event_hub.publish(event)
            return
        if self.output_mode == "im" and event.get("event_type") == "gift" and self.gift_dispatcher is not None:
            dispatch_result = await self.gift_dispatcher.dispatch_gift_event(event)
            self.last_command_id = dispatch_result.get("command_id", "")
            self.last_command_message = dispatch_result.get("message", "")
            event["command_dispatch"] = dispatch_result
        elif self.output_mode == "im" and event.get("event_type") == "like" and self.gift_dispatcher is not None:
            dispatch_result = await self.gift_dispatcher.dispatch_like_event(event)
            self.last_command_id = dispatch_result.get("command_id", "")
            self.last_command_message = dispatch_result.get("message", "")
            event["command_dispatch"] = dispatch_result
        elif self.output_mode == "im" and event.get("event_type") == "danmaku" and self.danmaku_dispatcher is not None:
            dispatch_result = await self.danmaku_dispatcher.dispatch(event)
            self.last_command_id = dispatch_result.get("command_id", "")
            self.last_command_message = dispatch_result.get("message", "")
            event["command_dispatch"] = dispatch_result
        if self.output_mode == "bluetooth" and self.bluetooth_dispatcher is not None:
            event["bluetooth_dispatch"] = await self.bluetooth_dispatcher.dispatch(event)
        self.event_hub.publish(event)
