from __future__ import annotations

import time
from typing import Any, Callable

from app.command_gateway.ws_client import CommandWebSocketClient


class CommandSessionService:
    def __init__(
        self,
        *,
        client_factory: Callable[..., Any] = CommandWebSocketClient,
        event_hub: Any | None = None,
    ) -> None:
        # 指令客户端工厂，用于创建实际 WebSocket 指令连接。
        self.client_factory = client_factory
        # 控制日志事件中心，用于记录登录、断开和指令发送结果。
        self.event_hub = event_hub
        self.status = "idle"
        self.message = ""
        self.ws_url = ""
        self.uid = ""
        self.user_id = ""
        self.last_login_at = 0
        self.last_command_id = ""
        self.last_command_message = ""
        self._client: Any | None = None

    @property
    def is_connected(self) -> bool:
        return self.status == "connected" and self._client is not None

    def get_status_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "ws_url": self.ws_url,
            "uid": self.uid,
            "user_id": self.user_id,
            "last_login_at": self.last_login_at,
            "last_command_id": self.last_command_id,
            "last_command_message": self.last_command_message,
            "can_connect": self.status in {"idle", "error", "disconnecting"},
            "can_disconnect": self.status == "connected",
        }

    async def connect(self, *, ws_url: str, uid: str, token: str) -> dict[str, Any]:
        if self.status in {"connecting", "connected"}:
            raise ValueError("当前指令通道已有连接正在处理")
        if not ws_url.strip() or not uid.strip() or not token.strip():
            raise ValueError("WS URL、UID、TOKEN 不能为空")
        if self.status == "disconnecting":
            await self._reset_client()

        self.status = "connecting"
        self.message = ""
        self.ws_url = ws_url.strip()
        self.uid = uid.strip()
        self.user_id = ""

        client = self.client_factory(
            url=self.ws_url,
            uid=self.uid,
            token=token.strip(),
        )
        try:
            result = await client.login()
        except Exception as exc:
            self.status = "error"
            self.message = str(exc)
            self._client = None
            raise

        self._client = client
        self.status = "connected"
        self.message = result.get("message", "IM 登录成功")
        self.user_id = result.get("user_id", "") or getattr(client, "user_id", "")
        self.last_login_at = int(time.time())
        self._publish_control(
            "command_connect",
            {
                "success": True,
                "message": self.message,
                "uid": self.uid,
                "user_id": self.user_id,
            },
        )
        return self.get_status_payload()

    async def disconnect(self) -> None:
        if self.status == "idle" and self._client is None:
            return

        self.status = "disconnecting"
        try:
            await self._reset_client()
        finally:
            self.status = "idle"
            self.message = ""
            self.user_id = ""
            self._publish_control(
                "command_disconnect",
                {
                    "success": True,
                    "message": "IM 指令通道已断开",
                    "uid": self.uid,
                },
            )

    async def send_command(self, *, command_id: str) -> dict[str, Any]:
        if not self.is_connected or self._client is None:
            raise RuntimeError("指令通道未登录")

        try:
            result = await self._client.send_command(command_id=command_id)
        except Exception as exc:
            self._publish_control(
                "command_send",
                {
                    "success": False,
                    "command_id": command_id,
                    "message": str(exc),
                },
            )
            raise
        self.last_command_id = command_id
        self.last_command_message = result.get("message", "")
        self._publish_control(
            "command_send",
            {
                "success": bool(result.get("success", True)),
                "command_id": command_id,
                "message": self.last_command_message,
            },
        )
        return result

    async def _reset_client(self) -> None:
        if self._client is not None and hasattr(self._client, "disconnect"):
            await self._client.disconnect()
        self._client = None

    def _publish_control(self, event_type: str, payload: dict[str, Any]) -> None:
        """写入控制日志事件。"""
        if self.event_hub is None or not hasattr(self.event_hub, "publish_control"):
            return
        self.event_hub.publish_control(
            {
                "type": event_type,
                "timestamp": int(time.time()),
                "payload": payload,
            }
        )
