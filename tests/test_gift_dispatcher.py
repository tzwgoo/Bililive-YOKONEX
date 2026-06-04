from __future__ import annotations

import pytest

from app.command_gateway.mapping import GiftCommandMapper
from app.services.danmaku_dispatcher import DanmakuCommandDispatcher
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


@pytest.mark.anyio
async def test_dispatcher_triggers_like_command_for_each_crossed_multiple_boundary() -> None:
    command_session = FakeCommandSession()
    dispatcher = GiftCommandDispatcher(
        mapper=GiftCommandMapper([]),
        command_session=command_session,
    )
    dispatcher.set_like_multiple(10)

    first = await dispatcher.dispatch_like_event(
        {
            "source": "open_live",
            "room_id": 123,
            "payload": {
                "like_count": 9,
            },
        }
    )
    second = await dispatcher.dispatch_like_event(
        {
            "source": "open_live",
            "room_id": 123,
            "payload": {
                "like_count": 20,
            },
        }
    )
    third = await dispatcher.dispatch_like_event(
        {
            "source": "open_live",
            "room_id": 123,
            "payload": {
                "like_count": 21,
            },
        }
    )

    assert first["trigger_count"] == 0
    assert second["trigger_count"] == 2
    assert third["trigger_count"] == 0
    assert command_session.called_with == ["like_trigger", "like_trigger"]


@pytest.mark.anyio
async def test_dispatcher_does_not_repeat_like_command_for_same_multiple_count() -> None:
    command_session = FakeCommandSession()
    dispatcher = GiftCommandDispatcher(
        mapper=GiftCommandMapper([]),
        command_session=command_session,
    )
    dispatcher.set_like_multiple(100)

    first = await dispatcher.dispatch_like_event(
        {
            "source": "open_live",
            "room_id": 123,
            "payload": {
                "like_count": 100,
            },
        }
    )
    second = await dispatcher.dispatch_like_event(
        {
            "source": "open_live",
            "room_id": 123,
            "payload": {
                "like_count": 100,
            },
        }
    )

    assert first["trigger_count"] == 1
    assert second["trigger_count"] == 0
    assert command_session.called_with == ["like_trigger"]


@pytest.mark.anyio
async def test_dispatcher_resets_like_progress_between_sessions() -> None:
    command_session = FakeCommandSession()
    dispatcher = GiftCommandDispatcher(
        mapper=GiftCommandMapper([]),
        command_session=command_session,
    )
    dispatcher.set_like_multiple(5)

    await dispatcher.dispatch_like_event(
        {
            "source": "third_party_ws",
            "room_id": 456,
            "payload": {
                "like_count": 10,
            },
        }
    )
    dispatcher.reset_runtime_state()
    result = await dispatcher.dispatch_like_event(
        {
            "source": "third_party_ws",
            "room_id": 456,
            "payload": {
                "like_count": 5,
            },
        }
    )

    assert result["trigger_count"] == 1
    assert command_session.called_with == ["like_trigger", "like_trigger", "like_trigger"]


@pytest.mark.anyio
async def test_dispatcher_uses_like_delta_to_avoid_zero_count_gaps() -> None:
    command_session = FakeCommandSession()
    dispatcher = GiftCommandDispatcher(
        mapper=GiftCommandMapper([]),
        command_session=command_session,
    )
    dispatcher.set_like_multiple(100)

    before_boundary = {
        "source": "third_party_ws",
        "room_id": 456,
        "payload": {
            "like_count": 99,
            "like_delta": 0,
        },
    }
    click_event = {
        "source": "third_party_ws",
        "room_id": 456,
        "payload": {
            "like_count": 0,
            "like_delta": 1,
        },
    }

    first = await dispatcher.dispatch_like_event(before_boundary)
    second = await dispatcher.dispatch_like_event(click_event)

    assert first["trigger_count"] == 0
    assert second["trigger_count"] == 1
    assert click_event["payload"]["like_count"] == 100
    assert command_session.called_with == ["like_trigger"]


@pytest.mark.anyio
async def test_dispatcher_ignores_zero_like_count_updates_without_resetting_progress() -> None:
    command_session = FakeCommandSession()
    dispatcher = GiftCommandDispatcher(
        mapper=GiftCommandMapper([]),
        command_session=command_session,
    )
    dispatcher.set_like_multiple(100)

    await dispatcher.dispatch_like_event(
        {
            "source": "third_party_ws",
            "room_id": 456,
            "payload": {
                "like_count": 200,
                "like_delta": 0,
            },
        }
    )
    zero_event = {
        "source": "third_party_ws",
        "room_id": 456,
        "payload": {
            "like_count": 0,
            "like_delta": 0,
        },
    }
    jumped_event = {
        "source": "third_party_ws",
        "room_id": 456,
        "payload": {
            "like_count": 305,
            "like_delta": 0,
        },
    }

    second = await dispatcher.dispatch_like_event(zero_event)
    third = await dispatcher.dispatch_like_event(jumped_event)

    assert second["trigger_count"] == 0
    assert zero_event["payload"]["like_count"] == 200
    assert third["trigger_count"] == 1
    assert command_session.called_with == ["like_trigger", "like_trigger", "like_trigger"]


@pytest.mark.anyio
async def test_dispatcher_triggers_danmaku_command_when_keyword_matches() -> None:
    command_session = FakeCommandSession()
    dispatcher = DanmakuCommandDispatcher(
        command_session=command_session,
    )
    dispatcher.configure(enabled=True, keywords="开火,冲冲冲", command_id="danmaku_trigger", cooldown_seconds=0)

    result = await dispatcher.dispatch(
        {
            "payload": {
                "msg": "兄弟们开火！",
            }
        }
    )

    assert result["success"] is True
    assert result["command_id"] == "danmaku_trigger"
    assert result["matched_keywords"] == ["开火"]
    assert command_session.called_with == ["danmaku_trigger"]


@pytest.mark.anyio
async def test_dispatcher_ignores_danmaku_when_keyword_does_not_match() -> None:
    command_session = FakeCommandSession()
    dispatcher = DanmakuCommandDispatcher(
        command_session=command_session,
    )
    dispatcher.configure(enabled=True, keywords="开火,冲冲冲", command_id="danmaku_trigger", cooldown_seconds=0)

    result = await dispatcher.dispatch(
        {
            "payload": {
                "msg": "这条弹幕不会触发",
            }
        }
    )

    assert result["matched"] is False
    assert command_session.called_with == []


@pytest.mark.anyio
async def test_dispatcher_blocks_danmaku_trigger_during_cooldown() -> None:
    command_session = FakeCommandSession()
    dispatcher = DanmakuCommandDispatcher(
        command_session=command_session,
    )
    dispatcher.configure(enabled=True, keywords="开火", command_id="danmaku_trigger", cooldown_seconds=30)

    first = await dispatcher.dispatch(
        {
            "source": "open_live",
            "room_id": 1,
            "payload": {
                "msg": "现在开火",
            },
        }
    )
    second = await dispatcher.dispatch(
        {
            "source": "open_live",
            "room_id": 1,
            "payload": {
                "msg": "继续开火",
            },
        }
    )

    assert first["trigger_count"] == 1
    assert second["trigger_count"] == 0
    assert "冷却中" in second["message"]
    assert command_session.called_with == ["danmaku_trigger"]


@pytest.mark.anyio
async def test_dispatcher_limits_danmaku_trigger_per_user_within_window() -> None:
    command_session = FakeCommandSession()
    dispatcher = DanmakuCommandDispatcher(
        command_session=command_session,
    )
    dispatcher.configure(
        enabled=True,
        keywords="开火",
        command_id="danmaku_trigger",
        cooldown_seconds=0,
        user_limit_window_seconds=60,
        user_limit_max_triggers=2,
    )

    first = await dispatcher.dispatch(
        {
            "source": "third_party_ws",
            "room_id": 1,
            "payload": {
                "msg": "开火",
                "uid": 1001,
            },
        }
    )
    second = await dispatcher.dispatch(
        {
            "source": "third_party_ws",
            "room_id": 1,
            "payload": {
                "msg": "继续开火",
                "uid": 1001,
            },
        }
    )
    third = await dispatcher.dispatch(
        {
            "source": "third_party_ws",
            "room_id": 1,
            "payload": {
                "msg": "再次开火",
                "uid": 1001,
            },
        }
    )
    another_user = await dispatcher.dispatch(
        {
            "source": "third_party_ws",
            "room_id": 1,
            "payload": {
                "msg": "开火",
                "uid": 2002,
            },
        }
    )

    assert first["trigger_count"] == 1
    assert second["trigger_count"] == 1
    assert third["trigger_count"] == 0
    assert "限流" in third["message"]
    assert another_user["trigger_count"] == 1
    assert command_session.called_with == ["danmaku_trigger", "danmaku_trigger", "danmaku_trigger"]


@pytest.mark.anyio
async def test_dispatcher_blocks_danmaku_when_guard_level_below_requirement() -> None:
    command_session = FakeCommandSession()
    dispatcher = DanmakuCommandDispatcher(
        command_session=command_session,
    )
    dispatcher.configure(
        enabled=True,
        keywords="开火",
        command_id="danmaku_trigger",
        cooldown_seconds=0,
        min_guard_level=2,
    )

    blocked = await dispatcher.dispatch(
        {
            "source": "third_party_ws",
            "room_id": 1,
            "payload": {
                "msg": "开火",
                "uid": 1001,
                "guard_level": 3,
            },
        }
    )
    allowed = await dispatcher.dispatch(
        {
            "source": "third_party_ws",
            "room_id": 1,
            "payload": {
                "msg": "开火",
                "uid": 1002,
                "guard_level": 1,
            },
        }
    )

    assert blocked["trigger_count"] == 0
    assert "舰队等级不足" in blocked["message"]
    assert allowed["trigger_count"] == 1
    assert command_session.called_with == ["danmaku_governor_trigger"]


@pytest.mark.anyio
async def test_dispatcher_uses_guard_specific_command_slot_rules() -> None:
    command_session = FakeCommandSession()
    dispatcher = DanmakuCommandDispatcher(
        command_session=command_session,
    )
    dispatcher.configure(
        enabled=True,
        keywords="开火",
        command_id="danmaku_trigger",
        cooldown_seconds=0,
    )
    dispatcher.set_command_slot_rules(
        [
            {"guard_level": 0, "command_slot": "command_one", "enabled": True},
            {"guard_level": 1, "command_slot": "command_ten", "enabled": True},
        ]
    )

    normal_user = await dispatcher.dispatch(
        {
            "source": "third_party_ws",
            "room_id": 1,
            "payload": {
                "msg": "开火",
                "uid": 1001,
                "guard_level": 0,
            },
        }
    )
    governor_user = await dispatcher.dispatch(
        {
            "source": "third_party_ws",
            "room_id": 1,
            "payload": {
                "msg": "开火",
                "uid": 1002,
                "guard_level": 1,
            },
        }
    )

    assert normal_user["command_id"] == "command_one"
    assert governor_user["command_id"] == "command_ten"
    assert command_session.called_with == ["command_one", "command_ten"]


@pytest.mark.anyio
async def test_dispatcher_uses_explicit_danmaku_event_type_rules() -> None:
    command_session = FakeCommandSession()
    dispatcher = DanmakuCommandDispatcher(
        command_session=command_session,
    )
    dispatcher.configure(
        enabled=True,
        keywords="开火",
        command_id="danmaku_trigger",
        cooldown_seconds=0,
    )
    dispatcher.set_command_slot_rules(
        [
            {"event_type": "danmaku", "command_slot": "command_one", "enabled": True},
            {"event_type": "danmaku_governor", "command_slot": "command_ten", "enabled": True},
        ]
    )

    normal_user = await dispatcher.dispatch(
        {
            "event_type": "danmaku",
            "source": "third_party_ws",
            "room_id": 1,
            "payload": {
                "msg": "开火",
                "uid": 1001,
                "guard_level": 0,
            },
        }
    )
    governor_user = await dispatcher.dispatch(
        {
            "event_type": "danmaku_governor",
            "source": "third_party_ws",
            "room_id": 1,
            "payload": {
                "msg": "开火",
                "uid": 1002,
                "guard_level": 1,
            },
        }
    )

    assert normal_user["command_id"] == "command_one"
    assert governor_user["command_id"] == "command_ten"
    assert command_session.called_with == ["command_one", "command_ten"]


@pytest.mark.anyio
async def test_dispatcher_uses_fixed_command_ids_for_each_danmaku_event_type_by_default() -> None:
    command_session = FakeCommandSession()
    dispatcher = DanmakuCommandDispatcher(
        command_session=command_session,
    )
    dispatcher.configure(
        enabled=True,
        keywords="开火",
        command_id="danmaku_trigger",
        cooldown_seconds=0,
    )

    normal_user = await dispatcher.dispatch(
        {
            "event_type": "danmaku",
            "source": "third_party_ws",
            "room_id": 1,
            "payload": {
                "msg": "开火",
                "uid": 1001,
                "guard_level": 0,
            },
        }
    )
    captain_user = await dispatcher.dispatch(
        {
            "event_type": "danmaku_captain",
            "source": "third_party_ws",
            "room_id": 1,
            "payload": {
                "msg": "开火",
                "uid": 1002,
                "guard_level": 3,
            },
        }
    )
    commander_user = await dispatcher.dispatch(
        {
            "event_type": "danmaku_commander",
            "source": "third_party_ws",
            "room_id": 1,
            "payload": {
                "msg": "开火",
                "uid": 1003,
                "guard_level": 2,
            },
        }
    )
    governor_user = await dispatcher.dispatch(
        {
            "event_type": "danmaku_governor",
            "source": "third_party_ws",
            "room_id": 1,
            "payload": {
                "msg": "开火",
                "uid": 1004,
                "guard_level": 1,
            },
        }
    )

    assert normal_user["command_id"] == "danmaku_trigger"
    assert captain_user["command_id"] == "danmaku_captain_trigger"
    assert commander_user["command_id"] == "danmaku_commander_trigger"
    assert governor_user["command_id"] == "danmaku_governor_trigger"
    assert command_session.called_with == [
        "danmaku_trigger",
        "danmaku_captain_trigger",
        "danmaku_commander_trigger",
        "danmaku_governor_trigger",
    ]
