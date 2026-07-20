from __future__ import annotations

import asyncio
import json
import logging
import platform
import socket
import time
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from app.remote_control.command_handler import RemoteCommandHandler
from app.remote_control.identity import DeviceIdentity, DeviceIdentityStore
from app.remote_control.protocol import COMMAND_IDS


LOGGER = logging.getLogger("bili_live.remote_control")


class RemoteControlClient:
    def __init__(
        self,
        *,
        ws_url: str,
        registration_token: str,
        client_name: str,
        heartbeat_seconds: int,
        identity_store: DeviceIdentityStore,
        command_session: Any,
        bluetooth_service: Any,
    ) -> None:
        self.ws_url = ws_url.strip()
        self.registration_token = registration_token.strip()
        self.client_name = client_name.strip() or socket.gethostname()
        self.heartbeat_seconds = max(5, int(heartbeat_seconds))
        self.identity_store = identity_store
        self.command_session = command_session
        self.bluetooth_service = bluetooth_service
        self.command_handler = RemoteCommandHandler(
            command_session=command_session,
            bluetooth_service=bluetooth_service,
        )
        self._task: asyncio.Task[None] | None = None
        self._command_tasks: set[asyncio.Task[None]] = set()
        self._send_lock = asyncio.Lock()
        self._processed_request_ids: set[str] = set()
        self._last_waveform_revision = ""

    @property
    def enabled(self) -> bool:
        identity = self.identity_store.load()
        return bool(self.ws_url and (identity.is_enrolled or self.registration_token))

    def start(self) -> None:
        if not self.enabled or self._task is not None:
            return
        self._task = asyncio.create_task(self._run(), name="remote-control-client")

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None
        for task in list(self._command_tasks):
            task.cancel()
        if self._command_tasks:
            await asyncio.gather(*self._command_tasks, return_exceptions=True)
        self._command_tasks.clear()

    async def _run(self) -> None:
        retry_seconds = 2
        while True:
            try:
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=20,
                    max_size=256 * 1024,
                ) as websocket:
                    await self._serve_connection(websocket)
                    retry_seconds = 2
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                LOGGER.warning("设备管理服务器连接失败，%s 秒后重试: %s", retry_seconds, exc)
                await asyncio.sleep(retry_seconds)
                retry_seconds = min(retry_seconds * 2, 30)

    async def _serve_connection(self, websocket: Any) -> None:
        identity = await self._authenticate(websocket)
        LOGGER.info("设备管理服务器连接成功 client_id=%s", identity.client_id)
        self._last_waveform_revision = ""
        await self._send_capabilities(websocket)
        await self._send_heartbeat(websocket)

        while True:
            try:
                raw_message = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=self.heartbeat_seconds,
                )
            except asyncio.TimeoutError:
                await self._send_heartbeat(websocket)
                await self._send_capabilities_if_changed(websocket)
                continue
            except ConnectionClosed:
                return
            await self._handle_server_message(websocket, raw_message)

    async def _authenticate(self, websocket: Any) -> DeviceIdentity:
        identity = self.identity_store.load()
        if identity.is_enrolled:
            await websocket.send(json.dumps({
                "type": "device.authenticate",
                "client_id": identity.client_id,
                "device_token": identity.device_token,
            }))
        else:
            await websocket.send(json.dumps({
                "type": "device.enroll",
                "registration_token": self.registration_token,
                "client_name": self.client_name,
                "platform": platform.platform(),
            }, ensure_ascii=False))

        raw_response = await asyncio.wait_for(websocket.recv(), timeout=10)
        response = json.loads(raw_response)
        if response.get("type") == "device.enrolled":
            identity = DeviceIdentity(
                client_id=str(response.get("client_id", "") or ""),
                device_token=str(response.get("device_token", "") or ""),
            )
            if not identity.is_enrolled:
                raise RuntimeError("管理服务器返回的设备凭据不完整")
            self.identity_store.save(identity)
            return identity
        if response.get("type") != "device.authenticated":
            raise RuntimeError(str(response.get("message", "设备认证失败")))
        return identity

    async def _handle_server_message(self, websocket: Any, raw_message: str | bytes) -> None:
        message = json.loads(raw_message)
        message_type = str(message.get("type", ""))
        if message_type == "device.command":
            task = asyncio.create_task(self._execute_command(websocket, message))
            self._command_tasks.add(task)
            task.add_done_callback(self._discard_command_task)
            return
        if message_type == "device.capabilities.request":
            await self._send_capabilities(websocket)
            return
        if message_type == "ping":
            await self._send_json(websocket, {"type": "pong", "timestamp": int(time.time())})

    async def _execute_command(self, websocket: Any, message: dict[str, Any]) -> None:
        request_id = str(message.get("request_id", "") or "").strip()
        expires_at = int(message.get("expires_at", 0) or 0)
        if not request_id or request_id in self._processed_request_ids:
            return
        self._processed_request_ids.add(request_id)
        if len(self._processed_request_ids) > 1000:
            self._processed_request_ids.clear()
            self._processed_request_ids.add(request_id)

        try:
            if expires_at and expires_at < int(time.time()):
                raise ValueError("远程命令已经过期")
            result = await self.command_handler.execute(
                str(message.get("action", "") or ""),
                message.get("args", {}) if isinstance(message.get("args"), dict) else {},
            )
            payload = {
                "type": "device.command_result",
                "request_id": request_id,
                "success": bool(result.get("success", True)),
                "message": str(result.get("message", "执行成功")),
                "data": result,
            }
        except Exception as exc:
            payload = {
                "type": "device.command_result",
                "request_id": request_id,
                "success": False,
                "message": str(exc),
                "data": {},
            }
        await self._send_json(websocket, payload)
        await self._send_heartbeat(websocket)

    async def _send_heartbeat(self, websocket: Any) -> None:
        status = self.bluetooth_service.get_status_payload()
        await self._send_json(websocket, {
            "type": "device.heartbeat",
            "timestamp": int(time.time()),
            "client_name": self.client_name,
            "user_id": str(self.command_session.user_id or ""),
            "command_connected": bool(self.command_session.is_connected),
            "devices": status.get("devices", []),
        })

    async def _send_capabilities_if_changed(self, websocket: Any) -> None:
        capabilities = self.bluetooth_service.get_remote_capabilities_payload()
        if capabilities["waveform_revision"] != self._last_waveform_revision:
            await self._send_capabilities(websocket, capabilities)

    async def _send_capabilities(self, websocket: Any, capabilities: dict[str, Any] | None = None) -> None:
        capabilities = capabilities or self.bluetooth_service.get_remote_capabilities_payload()
        await self._send_json(websocket, {
            "type": "device.capabilities",
            "command_ids": list(COMMAND_IDS),
            **capabilities,
        })
        self._last_waveform_revision = str(capabilities["waveform_revision"])

    async def _send_json(self, websocket: Any, payload: dict[str, Any]) -> None:
        async with self._send_lock:
            await websocket.send(json.dumps(payload, ensure_ascii=False))

    def _discard_command_task(self, task: asyncio.Task[None]) -> None:
        self._command_tasks.discard(task)
        if not task.cancelled():
            # 主连接断开时，旧连接上的结果回传可能失败；读取异常避免后台任务产生未处理告警。
            task.exception()
