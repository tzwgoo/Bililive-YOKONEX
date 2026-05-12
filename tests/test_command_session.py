from __future__ import annotations

import pytest

from app.services.command_session import CommandSessionService


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
async def test_disconnect_resets_connection_state() -> None:
    service = CommandSessionService(client_factory=FakeCommandClient)
    await service.connect(ws_url="ws://127.0.0.1:43001/", uid="123456", token="token")

    await service.disconnect()

    payload = service.get_status_payload()
    assert payload["status"] == "idle"
    assert payload["user_id"] == ""
    assert payload["can_connect"] is True
