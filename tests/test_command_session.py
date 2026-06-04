from __future__ import annotations

import pytest

from app.services.command_session import CommandSessionService
from app.services.event_hub import EventHub


class FakeCommandClient:
    def __init__(self, *, url: str, uid: str, token: str, user_id: str | None = None) -> None:
        self.url = url
        self.uid = uid
        self.token = token
        self.user_id = user_id or "123456"
        self.logged_in = False
        self.disconnected = False

    async def login(self) -> dict:
        self.logged_in = True
        return {
            "success": True,
            "message": "IM 登录成功",
            "user_id": self.user_id,
        }

    async def disconnect(self) -> None:
        self.disconnected = True

    async def send_command(self, *, command_id: str) -> dict:
        return {
            "success": True,
            "message": f"{command_id} 已发送",
            "raw": {},
        }


@pytest.mark.anyio
async def test_connect_updates_status_and_user_id() -> None:
    service = CommandSessionService(client_factory=FakeCommandClient)

    await service.connect(ws_url="ws://127.0.0.1:43001/", uid="game_123456", token="token")

    payload = service.get_status_payload()
    assert payload["status"] == "connected"
    assert payload["uid"] == "game_123456"
    assert payload["user_id"] == "123456"
    assert payload["can_disconnect"] is True


@pytest.mark.anyio
async def test_send_command_publishes_control_log() -> None:
    event_hub = EventHub()
    service = CommandSessionService(client_factory=FakeCommandClient, event_hub=event_hub)
    await service.connect(ws_url="ws://127.0.0.1:43001/", uid="game_123456", token="token")

    await service.send_command(command_id="command_one")

    control_events = event_hub.control_snapshot()
    assert control_events[-1]["type"] == "command_send"
    assert control_events[-1]["payload"]["command_id"] == "command_one"


@pytest.mark.anyio
async def test_disconnect_resets_connection_state() -> None:
    service = CommandSessionService(client_factory=FakeCommandClient)
    await service.connect(ws_url="ws://127.0.0.1:43001/", uid="123456", token="token")

    await service.disconnect()

    payload = service.get_status_payload()
    assert payload["status"] == "idle"
    assert payload["user_id"] == ""
    assert payload["can_connect"] is True


def test_disconnecting_status_allows_reconnect_button() -> None:
    service = CommandSessionService(client_factory=FakeCommandClient)
    service.status = "disconnecting"

    payload = service.get_status_payload()

    assert payload["can_connect"] is True
    assert payload["can_disconnect"] is False


@pytest.mark.anyio
async def test_connect_during_disconnecting_replaces_old_connection() -> None:
    service = CommandSessionService(client_factory=FakeCommandClient)
    await service.connect(ws_url="ws://127.0.0.1:43001/", uid="123456", token="token")
    previous_client = service._client
    service.status = "disconnecting"

    await service.connect(ws_url="ws://127.0.0.1:43001/", uid="game_999999", token="token-2")

    payload = service.get_status_payload()
    assert previous_client is not None
    assert previous_client.disconnected is True
    assert payload["status"] == "connected"
    assert payload["uid"] == "game_999999"
    assert payload["can_connect"] is False
