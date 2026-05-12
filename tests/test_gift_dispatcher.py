from __future__ import annotations

import pytest

from app.command_gateway.mapping import GiftCommandMapper
from app.services.gift_dispatcher import GiftCommandDispatcher


class FakeCommandSession:
    def __init__(self) -> None:
        self.is_connected = True
        self.called_with: list[str] = []

    async def send_command(self, *, command_id: str) -> dict:
        self.called_with.append(command_id)
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
        mapper=GiftCommandMapper([{"min_price": 100, "max_price": 999, "command_slot": "command_one"}]),
        command_session=command_session,
    )

    result = await dispatcher.dispatch_gift_event(
        {
            "payload": {
                "gift_name": "小花花",
                "gift_num": 1,
                "r_price": 100,
            }
        }
    )

    assert command_session.called_with == ["command_one"]
    assert result["success"] is True


@pytest.mark.anyio
async def test_dispatcher_repeats_command_when_trigger_mode_is_by_quantity() -> None:
    command_session = FakeCommandSession()
    dispatcher = GiftCommandDispatcher(
        mapper=GiftCommandMapper([{"min_price": 100, "max_price": 999, "command_slot": "command_two"}]),
        command_session=command_session,
        trigger_mode="by_quantity",
    )

    result = await dispatcher.dispatch_gift_event(
        {
            "payload": {
                "gift_name": "牛哇牛哇",
                "gift_num": 3,
                "r_price": 100,
            }
        }
    )

    assert command_session.called_with == ["command_two", "command_two", "command_two"]
    assert result["trigger_count"] == 3


@pytest.mark.anyio
async def test_dispatcher_only_sends_once_when_trigger_mode_is_single() -> None:
    command_session = FakeCommandSession()
    dispatcher = GiftCommandDispatcher(
        mapper=GiftCommandMapper([{"min_price": 100, "max_price": 999, "command_slot": "command_three"}]),
        command_session=command_session,
        trigger_mode="single",
    )

    result = await dispatcher.dispatch_gift_event(
        {
            "payload": {
                "gift_name": "牛哇牛哇",
                "gift_num": 5,
                "r_price": 100,
            }
        }
    )

    assert command_session.called_with == ["command_three"]
    assert result["trigger_count"] == 1
