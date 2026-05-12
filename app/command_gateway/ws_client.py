from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed


LOGGER = logging.getLogger("bili_live.command_ws")


def derive_user_id_from_uid(uid: str) -> str:
    normalized_uid = str(uid).strip()
    if normalized_uid.startswith("game_"):
        normalized_uid = normalized_uid[5:]
    return normalized_uid


class CommandWebSocketClient:
    def __init__(self, *, url: str, uid: str, token: str, user_id: str | None = None) -> None:
        self.url = url
        self.uid = uid
        self.token = token
        self.user_id = str(user_id or "").strip() or derive_user_id_from_uid(uid)
        self._ws: Any = None
        self._lock = asyncio.Lock()
        self._ping_task: asyncio.Task | None = None
        self._logged_in = False

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
            await self._send_json_locked(
                {
                    "type": "sendCommand",
                    "userId": self.user_id,
                    "commandId": command_id,
                }
            )
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
        if self._ws is None or getattr(self._ws, "closed", False):
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
        while True:
            message = await self._receive_json_locked()
            if message.get("type") == "loginResult":
                if not message.get("success"):
                    raise RuntimeError(message.get("message") or "下游指令通道登录失败")
                user_id = str(message.get("data", {}).get("userId", "")).strip()
                if user_id:
                    self.user_id = user_id
                if not self.user_id:
                    raise RuntimeError("下游指令通道登录成功，但未返回可用的 userId")
                self._logged_in = True
                LOGGER.info("下游指令通道登录成功 user_id=%s", self.user_id)
                return
            self._log_server_message(message)

    async def _connect_locked(self) -> None:
        LOGGER.info("连接下游指令通道 url=%s", self.url)
        self._ws = await websockets.connect(self.url, ping_interval=None)
        self._logged_in = False
        if self._ping_task is not None:
            self._ping_task.cancel()
        self._ping_task = asyncio.create_task(self._ping_loop())

    async def _send_json_locked(self, payload: dict[str, Any]) -> None:
        if self._ws is None:
            raise RuntimeError("下游指令通道尚未连接")
        await self._ws.send(json.dumps(payload, ensure_ascii=False))

    async def _receive_json_locked(self) -> dict[str, Any]:
        if self._ws is None:
            raise RuntimeError("下游指令通道尚未连接")
        try:
            message = await self._ws.recv()
        except ConnectionClosed as exc:  # pragma: no cover - 真实网络路径
            self._ws = None
            self._logged_in = False
            raise RuntimeError(f"下游指令通道已断开: {exc}") from exc

        if isinstance(message, bytes):
            message = message.decode("utf-8")
        return json.loads(message)

    async def _ping_loop(self) -> None:
        try:
            while self._ws is not None:
                await asyncio.sleep(30)
                if self._ws is None:
                    return
                await self._ws.send(json.dumps({"type": "ping"}))
        except asyncio.CancelledError:  # pragma: no cover - 关闭路径
            raise
        except Exception as exc:  # pragma: no cover - 真实网络路径
            LOGGER.warning("下游指令通道心跳失败 error=%s", exc)
            self._logged_in = False
            self._ws = None

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
