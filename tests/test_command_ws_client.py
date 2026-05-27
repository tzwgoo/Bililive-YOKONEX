from __future__ import annotations

import asyncio
import time

import pytest

from app.command_gateway.ws_client import derive_user_id_from_uid
from app.command_gateway.ws_client import CommandWebSocketClient
from websockets.exceptions import InvalidMessage


def test_derive_user_id_from_game_uid() -> None:
    assert derive_user_id_from_uid("game_123456") == "123456"


def test_derive_user_id_from_numeric_uid() -> None:
    assert derive_user_id_from_uid("123456") == "123456"


@pytest.mark.anyio
async def test_command_ws_client_rejects_non_ws_url() -> None:
    client = CommandWebSocketClient(url="http://example.com", uid="123456", token="token")

    with pytest.raises(RuntimeError, match="ws:// 或 wss://"):
        await client.login()


@pytest.mark.anyio
async def test_command_ws_client_wraps_invalid_http_response_error() -> None:
    client = CommandWebSocketClient(url="ws://example.com:43001/", uid="123456", token="token")

    async def fake_connect(*_args, **_kwargs):
        raise InvalidMessage("did not receive a valid HTTP response")

    client._validate_url()

    from app.command_gateway import ws_client as ws_client_module

    original_connect = ws_client_module.websockets.connect
    ws_client_module.websockets.connect = fake_connect
    try:
        with pytest.raises(RuntimeError, match="未收到合法的 WebSocket/HTTP 响应"):
            await client.login()
    finally:
        ws_client_module.websockets.connect = original_connect


@pytest.mark.anyio
async def test_command_ws_client_times_out_when_login_result_never_arrives() -> None:
    class HangingLoginClient(CommandWebSocketClient):
        def __init__(self) -> None:
            super().__init__(
                url="ws://example.com:43001/",
                uid="123456",
                token="token",
                user_id="123456",
                login_timeout=0.01,
            )
            self.sent_payloads: list[dict] = []

        async def _connect_locked(self) -> None:
            self._ws = object()
            self._logged_in = False

        async def _send_json_locked(self, payload: dict) -> None:
            self.sent_payloads.append(payload)

        async def _receive_json_locked(self) -> dict:
            await asyncio.sleep(0.02)
            return {"type": "connected"}

    client = HangingLoginClient()

    with pytest.raises(RuntimeError, match="登录超时"):
        await client.login()

    assert client.sent_payloads[0]["type"] == "login"


@pytest.mark.anyio
async def test_command_ws_client_reconnects_before_command_when_connection_is_idle() -> None:
    class IdleReconnectClient(CommandWebSocketClient):
        def __init__(self) -> None:
            super().__init__(
                url="ws://example.com:43001/",
                uid="123456",
                token="token",
                user_id="123456",
                idle_timeout=1,
            )
            self.connect_calls = 0
            self.sent_payloads: list[dict] = []
            self.received_payloads = [
                {"type": "loginResult", "success": True, "data": {"userId": "123456"}},
                {"type": "loginResult", "success": True, "data": {"userId": "123456"}},
                {"type": "commandResult", "success": True, "message": "ok"},
            ]

        async def _connect_locked(self) -> None:
            self.connect_calls += 1
            self._ws = object()
            self._logged_in = False
            now = time.monotonic()
            self._last_received_at = now
            self._last_sent_at = now

        async def _send_json_locked(self, payload: dict) -> None:
            self.sent_payloads.append(payload)
            self._last_sent_at = time.monotonic()

        async def _receive_json_locked(self) -> dict:
            payload = self.received_payloads.pop(0)
            self._last_received_at = time.monotonic()
            return payload

        async def _close_socket_after_login_failure(self) -> None:
            self._ws = None
            self._logged_in = False

    client = IdleReconnectClient()

    await client.login()
    client._last_received_at = time.monotonic() - 10

    result = await client.send_command(command_id="command_one")

    assert result["success"] is True
    assert client.connect_calls == 2
    assert [payload["type"] for payload in client.sent_payloads] == [
        "login",
        "login",
        "sendCommand",
    ]
