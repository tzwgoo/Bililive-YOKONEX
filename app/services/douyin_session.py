from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
import socket
import subprocess
import time
from typing import Any
from urllib.parse import urlparse

from app.douyin.event_mapper import map_douyin_message
from app.douyin.ws_client import DEFAULT_DOUYIN_WS_BASE_URL
from app.douyin.ws_client import DouyinWsClient
from app.models import SessionStatus
from app.runtime import resolve_bundle_path
from app.models import is_danmaku_event_type
from app.models import normalize_event_type_value
from app.services.event_hub import EventHub
from app.services.third_party_session import GIFT_LIKE_EVENT_TYPES


LOGGER = logging.getLogger("bili_live.douyin")


class DouyinLiveSessionService:
    def __init__(
        self,
        *,
        event_hub: EventHub,
        gift_dispatcher: Any | None = None,
        danmaku_dispatcher: Any | None = None,
        bluetooth_dispatcher: Any | None = None,
        ws_client: Any | None = None,
        port_checker: Any | None = None,
        process_launcher: Any | None = None,
    ) -> None:
        self.event_hub = event_hub
        self.gift_dispatcher = gift_dispatcher
        self.danmaku_dispatcher = danmaku_dispatcher
        self.bluetooth_dispatcher = bluetooth_dispatcher
        self.ws_client = ws_client or DouyinWsClient()
        self.port_checker = port_checker or self._can_connect_to_service
        self.process_launcher = process_launcher or self._launch_process
        self.status = SessionStatus.IDLE
        self.room_id = ""
        self.ws_base_url = DEFAULT_DOUYIN_WS_BASE_URL
        self.executable_path = ""
        self.anchor_name = ""
        self.last_error = ""
        self.last_event_at = 0
        self.last_heartbeat_at = 0
        self.last_command_id = ""
        self.last_command_message = ""
        self.output_mode = "im"
        self.trigger_mode = "by_quantity"
        self._consume_task: asyncio.Task | None = None
        self._managed_process: Any | None = None
        self._stop_requested = False
        self._unmapped_methods_logged: set[str] = set()

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
        danmaku_user_limit_window_seconds: int = 0,
        danmaku_user_limit_max_triggers: int = 0,
        danmaku_min_guard_level: int = 0,
        douyin_ws_base_url: str = "",
        douyin_executable_path: str = "",
    ) -> None:
        room_id = value.strip()
        if not room_id:
            raise ValueError("抖音直播间标识不能为空")
        if self.status in {SessionStatus.STARTING, SessionStatus.RUNNING, SessionStatus.RECONNECTING}:
            raise ValueError("当前已有会话正在运行")

        self.room_id = room_id
        self.ws_base_url = str(douyin_ws_base_url or DEFAULT_DOUYIN_WS_BASE_URL).strip()
        self.executable_path = self._resolve_executable_path(douyin_executable_path)
        self.output_mode = str(output_mode or "im")
        self.trigger_mode = trigger_mode
        self._configure_dispatchers(
            trigger_mode=trigger_mode,
            like_multiple=like_multiple,
            danmaku_enabled=danmaku_enabled,
            danmaku_keywords=danmaku_keywords,
            danmaku_command_id=danmaku_command_id,
            danmaku_cooldown_seconds=danmaku_cooldown_seconds,
            danmaku_user_limit_window_seconds=danmaku_user_limit_window_seconds,
            danmaku_user_limit_max_triggers=danmaku_user_limit_max_triggers,
            danmaku_min_guard_level=danmaku_min_guard_level,
        )
        self.anchor_name = ""
        self.last_error = ""
        self.last_command_id = ""
        self.last_command_message = ""
        self.last_event_at = 0
        self._stop_requested = False
        self._unmapped_methods_logged.clear()
        self._reset_dispatchers()
        await self._ensure_douyin_service_started()
        self.status = SessionStatus.STARTING
        self._consume_task = asyncio.create_task(self._consume_loop())

    async def stop(self) -> None:
        if self.status == SessionStatus.IDLE and self._consume_task is None:
            return

        self.status = SessionStatus.STOPPING
        self._stop_requested = True
        try:
            try:
                await self.ws_client.disconnect()
            except Exception as exc:  # pragma: no cover - 真实联调容错路径
                LOGGER.warning("抖音断开连接时发生异常 room_id=%s error=%s", self.room_id, exc)
            if self._consume_task is not None:
                self._consume_task.cancel()
                try:
                    await self._consume_task
                except asyncio.CancelledError:
                    pass
                self._consume_task = None
        finally:
            await self._stop_managed_process()
            self.status = SessionStatus.IDLE
            self.room_id = ""
            self.anchor_name = ""

    def get_status_payload(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "message": self.last_error,
            "room_id": self.room_id,
            "anchor_name": self.anchor_name,
            "last_event_at": self.last_event_at,
            "last_heartbeat_at": self.last_heartbeat_at,
            "last_command_id": self.last_command_id,
            "last_command_message": self.last_command_message,
            "trigger_mode": self.trigger_mode,
            "douyin_ws_base_url": self.ws_base_url,
            "douyin_executable_path": self.executable_path,
            "command_dispatch_enabled": bool(
                (self.gift_dispatcher is not None and getattr(self.gift_dispatcher, "is_enabled", False))
                or (self.danmaku_dispatcher is not None and getattr(self.danmaku_dispatcher, "is_enabled", False))
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
                    base_url=self.ws_base_url,
                    on_message=self._handle_raw_message,
                )
                if self._stop_requested:
                    break
                self.status = SessionStatus.RECONNECTING
                self.last_error = "抖音长连断开，准备重连"
                LOGGER.warning("抖音长连断开 room_id=%s", self.room_id)
                await asyncio.sleep(3)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - 真实联调路径
                if self._stop_requested:
                    break
                self.status = SessionStatus.RECONNECTING
                self.last_error = f"抖音监听异常，准备重连: {exc}"
                LOGGER.warning("抖音监听异常 room_id=%s error=%s", self.room_id, exc)
                await asyncio.sleep(3)

    async def _handle_raw_message(self, message: dict[str, Any]) -> None:
        self.last_event_at = int(time.time())
        self._hydrate_room_profile_from_message(message)
        event = map_douyin_message(message, room_id=self.room_id)
        if event is None:
            self._log_unmapped_message_once(message)
            return
        event_type = normalize_event_type_value(event.get("event_type", ""))
        if self.output_mode == "im" and event_type in GIFT_LIKE_EVENT_TYPES and self.gift_dispatcher is not None:
            dispatch_result = await self.gift_dispatcher.dispatch_gift_event(event)
            self._record_command_result(event, dispatch_result)
        elif self.output_mode == "im" and event_type == "like" and self.gift_dispatcher is not None:
            dispatch_result = await self.gift_dispatcher.dispatch_like_event(event)
            self._record_command_result(event, dispatch_result)
        elif self.output_mode == "im" and event_type == "interact" and self.gift_dispatcher is not None:
            dispatch_result = await self.gift_dispatcher.dispatch_interact_event(event)
            self._record_command_result(event, dispatch_result)
        elif self.output_mode == "im" and is_danmaku_event_type(event_type) and self.danmaku_dispatcher is not None:
            dispatch_result = await self.danmaku_dispatcher.dispatch(event)
            self._record_command_result(event, dispatch_result)
        if self.output_mode == "bluetooth" and self.bluetooth_dispatcher is not None:
            dispatch_result = await self.bluetooth_dispatcher.dispatch(event)
            event["bluetooth_dispatch"] = dispatch_result
            self._publish_bluetooth_dispatch_diagnostic(dispatch_result)
        self.event_hub.publish(event)

    async def _ensure_douyin_service_started(self) -> None:
        endpoint = self._resolve_local_endpoint(self.ws_base_url)
        if endpoint is None or not self.executable_path:
            return
        host, port = endpoint
        if self.port_checker(host, port):
            return

        executable_path = Path(self.executable_path).expanduser()
        if not executable_path.exists() or not executable_path.is_file():
            raise ValueError("douyinLive.exe 路径不存在")

        # 仅在本机端口未监听时拉起 douyinLive，避免重复启动已有服务。
        self._managed_process = self.process_launcher(executable_path, port)
        for _ in range(25):
            if self.port_checker(host, port):
                LOGGER.info("douyinLive 已自动拉起 port=%s", port)
                return
            if self._process_has_exited(self._managed_process):
                break
            await asyncio.sleep(0.2)
        raise ValueError("douyinLive 自动拉起失败，请检查 exe 是否能正常启动")

    def _configure_dispatchers(self, **kwargs: Any) -> None:
        if self.gift_dispatcher is not None and hasattr(self.gift_dispatcher, "set_trigger_mode"):
            self.gift_dispatcher.set_trigger_mode(kwargs["trigger_mode"])
        if self.gift_dispatcher is not None and hasattr(self.gift_dispatcher, "set_like_multiple"):
            self.gift_dispatcher.set_like_multiple(kwargs["like_multiple"])
        if self.danmaku_dispatcher is not None and hasattr(self.danmaku_dispatcher, "configure"):
            self.danmaku_dispatcher.configure(
                enabled=kwargs["danmaku_enabled"],
                keywords=kwargs["danmaku_keywords"],
                command_id=kwargs["danmaku_command_id"],
                cooldown_seconds=kwargs["danmaku_cooldown_seconds"],
                user_limit_window_seconds=kwargs["danmaku_user_limit_window_seconds"],
                user_limit_max_triggers=kwargs["danmaku_user_limit_max_triggers"],
                min_guard_level=kwargs["danmaku_min_guard_level"],
            )
        if self.bluetooth_dispatcher is not None and hasattr(self.bluetooth_dispatcher, "configure"):
            self.bluetooth_dispatcher.configure(
                danmaku_enabled=kwargs["danmaku_enabled"],
                danmaku_keywords=kwargs["danmaku_keywords"],
                danmaku_cooldown_seconds=kwargs["danmaku_cooldown_seconds"],
                danmaku_user_limit_window_seconds=kwargs["danmaku_user_limit_window_seconds"],
                danmaku_user_limit_max_triggers=kwargs["danmaku_user_limit_max_triggers"],
                danmaku_min_guard_level=kwargs["danmaku_min_guard_level"],
            )

    def _reset_dispatchers(self) -> None:
        for dispatcher in (self.gift_dispatcher, self.danmaku_dispatcher, self.bluetooth_dispatcher):
            if dispatcher is not None and hasattr(dispatcher, "reset_runtime_state"):
                dispatcher.reset_runtime_state()

    def _hydrate_room_profile_from_message(self, message: dict[str, Any]) -> None:
        # douyinLive 会在每条业务消息里补充直播间名称，优先用它更新状态栏。
        for key in ("livename", "liveName", "title"):
            value = str(message.get(key, "") or "").strip()
            if value:
                self.anchor_name = value
                return
        if message.get("event") == "live_status":
            self.last_error = str(message.get("message", "") or "")

    def _record_command_result(self, event: dict[str, Any], dispatch_result: dict[str, Any]) -> None:
        self.last_command_id = dispatch_result.get("command_id", "")
        self.last_command_message = dispatch_result.get("message", "")
        event["command_dispatch"] = dispatch_result

    def _log_unmapped_message_once(self, message: dict[str, Any]) -> None:
        method = str(message.get("method", "") or "").strip()
        if "gift" not in method.lower() or method in self._unmapped_methods_logged:
            return
        self._unmapped_methods_logged.add(method)
        # 只输出字段名，不输出完整消息，避免日志里混入用户隐私和超长 payload。
        LOGGER.warning("抖音礼物类消息未映射 room_id=%s method=%s keys=%s", self.room_id, method, sorted(message.keys()))

    def _publish_bluetooth_dispatch_diagnostic(self, dispatch_result: Any) -> None:
        if not isinstance(dispatch_result, dict):
            return
        if dispatch_result.get("matched", False):
            return
        self.event_hub.publish_control(
            {
                "type": "bluetooth_trigger",
                "timestamp": int(time.time()),
                "payload": dispatch_result,
            }
        )

    def _resolve_local_endpoint(self, base_url: str) -> tuple[str, int] | None:
        parsed = urlparse(str(base_url or DEFAULT_DOUYIN_WS_BASE_URL).strip())
        host = parsed.hostname or ""
        if host not in {"127.0.0.1", "localhost", "::1"}:
            return None
        port = parsed.port or (443 if parsed.scheme == "wss" else 80)
        return host, port

    def _resolve_executable_path(self, value: str) -> str:
        configured_path = str(value or "").strip()
        if configured_path:
            return configured_path
        if os.name != "nt":
            return ""
        bundled_path = resolve_bundle_path("vendor/douyinLive/windows-amd64/douyinLive.exe")
        return str(bundled_path) if bundled_path.exists() else ""

    def _can_connect_to_service(self, host: str, port: int) -> bool:
        try:
            with socket.create_connection((host, port), timeout=0.35):
                return True
        except OSError:
            return False

    def _launch_process(self, executable_path: Path, port: int) -> subprocess.Popen:
        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        return subprocess.Popen(
            [str(executable_path), "--port", str(port)],
            cwd=str(executable_path.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )

    def _process_has_exited(self, process: Any | None) -> bool:
        return process is not None and hasattr(process, "poll") and process.poll() is not None

    async def _stop_managed_process(self) -> None:
        process = self._managed_process
        self._managed_process = None
        if process is None or self._process_has_exited(process):
            return
        try:
            process.terminate()
            await asyncio.to_thread(process.wait, timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception as exc:  # pragma: no cover - 真实进程退出容错
            LOGGER.warning("关闭 douyinLive 自动拉起进程失败 error=%s", exc)
