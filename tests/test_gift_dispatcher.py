from __future__ import annotations

import pytest

from app.command_gateway.mapping import GiftCommandMapper
from app.services.gift_dispatcher import GiftCommandDispatcher


class FakeCommandSession:
    def __init__(self) -> None:
        self.is_connected = True
        self.called_with: str | None = None

    async def send_command(self, *, command_id: str) -> dict:
        self.called_with = command_id
        return {
            "success": True,
            "message": "指令发送成功",
            "raw": {},
        }


def test_dispatcher_is_enabled_when_command_session_connected() -> None:
    dispatcher = GiftCommandDispatcher(
        mapper=GiftCommandMapper([]),
        command_session=FakeCommandSession(),
    )

    assert dispatcher.is_enabled is True


@pytest.mark.anyio
async def test_dispatcher_sends_command_via_logged_in_command_session() -> None:
    command_session = FakeCommandSession()
    dispatcher = GiftCommandDispatcher(
        mapper=GiftCommandMapper([{"gift_id": 1001, "command_id": "player_hurt"}]),
        command_session=command_session,
    )

    result = await dispatcher.dispatch_gift_event({"payload": {"gift_id": 1001, "gift_name": "小花花"}})

    assert command_session.called_with == "player_hurt"
    assert result["success"] is True
