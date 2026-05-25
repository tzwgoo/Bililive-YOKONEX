from __future__ import annotations

import asyncio
import json
import logging
import time
from urllib.parse import urlparse
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed
from websockets.exceptions import InvalidHandshake, InvalidMessage, InvalidStatus


LOGGER = logging.getLogger("bili_live.command_ws")


def derive_user_id_from_uid(uid: str) -> str:
    normalized_uid = str(uid).strip()
    if normalized_uid.startswith("game_"):
        normalized_uid = normalized_uid[5:]
    return normalized_uid


class CommandWebSocketClient:
    def __init__(
        self,
        *,
        url: str,
        uid: str,
        token: str,
        user_id: str | None = None,
        login_timeout: float = 8.0,
        ping_interval: float = 30.0,
        idle_timeout: float = 270.0,
    ) -> None:
        self.url = url
        self.uid = uid
        self.token = token
        self.user_id = str(user_id or "").strip() or derive_user_id_from_uid(uid)
        self.login_timeout = login_timeout
        self.ping_interval = ping_interval
        self.idle_timeout = idle_timeout
        self._ws: Any = None
        self._lock = asyncio.Lock()
        self._ping_task: asyncio.Task | None = None
        self._logged_in = False
        self._last_received_at = 0.0
        self._last_sent_at = 0.0

    async def login(self) -> dict[str, Any]:
        async with self._lock:
            await self._ensure_logged_in_locked()
            return {
                "success": True,
                "message": "IM 登录成功",
                "user_id": self.user_id,
            }

    async def send_command(self, *, command_id: str) -> dict[str, Any]:
        async with self._lock:
            await self._ensure_logged_in_locked()
            payload = {
                "type": "sendCommand",
                "userId": self.user_id,
                "commandId": command_id,
            }
            try:
                await self._send_json_locked(payload)
            except RuntimeError:
                LOGGER.warning("下游指令发送前连接已失效，准备自动重连后重试 command_id=%s", command_id)
                await self._ensure_logged_in_locked()
                await self._send_json_locked(payload)
            while True:
                message = await self._receive_json_locked()
                if message.get("type") == "commandResult":
                    return {
                        "success": bool(message.get("success")),
                        "message": message.get("message") or "",
                        "raw": message,
                    }
                self._log_server_message(message)

    async def disconnect(self) -> None:
        async with self._lock:
            if self._ping_task is not None:
                self._ping_task.cancel()
                self._ping_task = None

            if self._ws is not None:
                try:
                    if self._logged_in and self.user_id:
                        await self._send_json_locked({"type": "logout", "userId": self.user_id})
                except Exception:  # pragma: no cover - 真实网络清理路径
                    LOGGER.debug("下游指令通道登出时忽略异常", exc_info=True)

                try:
                    await self._ws.close()
                finally:
                    self._ws = None
                    self._logged_in = False

    async def _ensure_logged_in_locked(self) -> None:
        if self._should_refresh_connection_locked():
            if self._ws is not None and not getattr(self._ws, "closed", False):
                LOGGER.warning(
                    "下游指令通道空闲超过阈值，发送前主动重建连接 idle_timeout=%s",
                    self.idle_timeout,
                )
                await self._close_socket_after_login_failure()
            await self._connect_locked()
        if self._logged_in:
            return

        await self._send_json_locked(
            {
                "type": "login",
                "uid": self.uid,
                "token": self.token,
            }
        )
        try:
            await asyncio.wait_for(self._wait_login_result_locked(), timeout=self.login_timeout)
        except asyncio.TimeoutError as exc:
            await self._close_socket_after_login_failure()
            raise RuntimeError("下游指令通道登录超时，请确认服务端会返回 loginResult") from exc

    async def _connect_locked(self) -> None:
        self._validate_url()
        LOGGER.info("连接下游指令通道 url=%s", self.url)
        try:
            self._ws = await websockets.connect(self.url, ping_interval=None)
        except InvalidStatus as exc:
            raise RuntimeError(
                f"下游指令通道握手失败，服务返回了异常状态码 {exc.response.status_code}。请确认 WS URL 指向正确的 WebSocket 接口。"
            ) from exc
        except (InvalidHandshake, InvalidMessage) as exc:
            raise RuntimeError(
                "下游指令通道握手失败，未收到合法的 WebSocket/HTTP 响应。请确认 WS URL 正确，且该地址确实提供 WebSocket 服务。"
            ) from exc
        except OSError as exc:
            raise RuntimeError(
                f"下游指令通道连接失败，请确认服务已启动且地址可访问: {exc}"
            ) from exc
        self._logged_in = False
        now = time.monotonic()
        self._last_received_at = now
        self._last_sent_at = now
        if self._ping_task is not None:
            self._ping_task.cancel()
        self._ping_task = asyncio.create_task(self._ping_loop())

    async def _wait_login_result_locked(self) -> None:
        while True:
            message = await self._receive_json_locked()
            if message.get("type") == "loginResult":
                if not message.get("success"):
                    await self._close_socket_after_login_failure()
                    raise RuntimeError(message.get("message") or "下游指令通道登录失败")
                user_id = str(message.get("data", {}).get("userId", "")).strip()
                if user_id:
                    self.user_id = user_id
                if not self.user_id:
                    await self._close_socket_after_login_failure()
                    raise RuntimeError("下游指令通道登录成功，但未返回可用的 userId")
                self._logged_in = True
                LOGGER.info("下游指令通道登录成功 user_id=%s", self.user_id)
                return
            self._log_server_message(message)

    async def _close_socket_after_login_failure(self) -> None:
        if self._ping_task is not None:
            self._ping_task.cancel()
            self._ping_task = None
        if self._ws is not None and hasattr(self._ws, "close"):
            try:
                await self._ws.close()
            except Exception:  # pragma: no cover - 清理容错
                LOGGER.debug("登录失败后关闭下游指令通道时忽略异常", exc_info=True)
        self._ws = None
        self._logged_in = False
        self._last_received_at = 0.0
        self._last_sent_at = 0.0

    def _validate_url(self) -> None:
        parsed = urlparse(self.url)
        if parsed.scheme not in {"ws", "wss"}:
            raise RuntimeError("WS URL 必须以 ws:// 或 wss:// 开头")
        if not parsed.netloc:
            raise RuntimeError("WS URL 缺少主机或端口")

    async def _send_json_locked(self, payload: dict[str, Any]) -> None:
        if self._ws is None:
            raise RuntimeError("下游指令通道尚未连接")
        try:
            await self._ws.send(json.dumps(payload, ensure_ascii=False))
        except ConnectionClosed as exc:
            self._mark_connection_broken()
            raise RuntimeError(f"下游指令通道已断开: {exc}") from exc
        self._last_sent_at = time.monotonic()

    async def _receive_json_locked(self) -> dict[str, Any]:
        if self._ws is None:
            raise RuntimeError("下游指令通道尚未连接")
        try:
            message = await self._ws.recv()
        except ConnectionClosed as exc:  # pragma: no cover - 真实网络路径
            self._mark_connection_broken()
            raise RuntimeError(f"下游指令通道已断开: {exc}") from exc

        if isinstance(message, bytes):
            message = message.decode("utf-8")
        self._last_received_at = time.monotonic()
        return json.loads(message)

    async def _ping_loop(self) -> None:
        try:
            while self._ws is not None:
                await asyncio.sleep(self.ping_interval)
                if self._ws is None:
                    return
                if self.idle_timeout > 0 and self._last_received_at:
                    idle_for = time.monotonic() - self._last_received_at
                    if idle_for >= self.idle_timeout:
                        LOGGER.warning(
                            "下游指令通道超过 %.0f 秒未收到消息，关闭旧连接等待自动重连",
                            self.idle_timeout,
                        )
                        await self._close_stale_socket()
                        return
                await self._send_json_locked({"type": "ping"})
        except asyncio.CancelledError:  # pragma: no cover - 关闭路径
            raise
        except Exception as exc:  # pragma: no cover - 真实网络路径
            LOGGER.warning("下游指令通道心跳失败 error=%s", exc)
            self._mark_connection_broken()
        finally:
            if self._ping_task is asyncio.current_task():
                self._ping_task = None

    def _should_refresh_connection_locked(self) -> bool:
        if self._ws is None or getattr(self._ws, "closed", False):
            return True
        if self.idle_timeout <= 0 or self._last_received_at <= 0:
            return False
        return (time.monotonic() - self._last_received_at) >= self.idle_timeout

    def _mark_connection_broken(self) -> None:
        if self._ping_task is not None and self._ping_task is not asyncio.current_task():
            self._ping_task.cancel()
            self._ping_task = None
        self._ws = None
        self._logged_in = False

    async def _close_stale_socket(self) -> None:
        if self._ws is not None and hasattr(self._ws, "close"):
            try:
                await self._ws.close()
            except Exception:  # pragma: no cover - 清理容错
                LOGGER.debug("关闭空闲下游指令通道时忽略异常", exc_info=True)
        self._ws = None
        self._logged_in = False

    def _log_server_message(self, message: dict[str, Any]) -> None:
        message_type = message.get("type", "unknown")
        if message_type in {"connected", "heartbeat", "pong"}:
            LOGGER.debug("下游指令通道消息 type=%s", message_type)
            return
        if message_type in {"status", "network", "message"}:
            LOGGER.info("下游指令通道消息 type=%s payload=%s", message_type, message)
            return
        if message_type == "error":
            LOGGER.warning("下游指令通道错误 message=%s", message.get("message", ""))
            return
        LOGGER.debug("下游指令通道忽略消息 type=%s payload=%s", message_type, message)
