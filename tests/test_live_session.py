from __future__ import annotations

import asyncio

import pytest

from app.config import Settings
from app.services.event_hub import EventHub
from app.services.live_session import LiveSessionService
from app.models import SessionStatus


class FakeApiClient:
    async def start(self, *, app_id: int, code: str) -> dict:
        return {
            "data": {
                "game_info": {"game_id": f"game-{code}"},
                "websocket_info": {
                    "auth_body": "auth-demo",
                    "wss_link": ["wss://example.test/socket"],
                },
                "anchor_info": {
                    "room_id": 123456,
                    "uname": "测试主播",
                },
            }
        }

    async def heartbeat(self, *, game_id: str) -> dict:
        return {"code": 0, "message": "ok", "data": {"game_id": game_id}}

    async def end(self, *, app_id: int, game_id: str) -> dict:
        return {"code": 0, "message": "ok", "data": {}}


class FakeWsClient:
    async def connect_and_consume(self, *, wss_links: list[str], auth_body: str, on_event) -> None:
        await asyncio.sleep(0)

    async def disconnect(self) -> None:
        return None


class FakeGiftDispatcher:
    def __init__(self) -> None:
        self.called_with: dict | None = None

    async def dispatch_gift_event(self, event: dict) -> dict:
        self.called_with = event
        return {
            "matched": True,
            "command_id": "player_hurt",
            "success": True,
            "message": "指令发送成功",
        }


class FakeDanmakuDispatcher:
    def __init__(self) -> None:
        self.called_with: dict | None = None

        def configure(self, **kwargs) -> None:
            self.config = kwargs

    def reset_runtime_state(self) -> None:
        return None


class FakeBluetoothDispatcher:
    def __init__(self) -> None:
        self.called_with: dict | None = None
        self.config: dict | None = None

    async def dispatch(self, event: dict) -> dict:
        self.called_with = event
        return {
            "matched": True,
            "waveform_id": "ems-default-pulse",
            "success": True,
            "message": "蓝牙波形触发成功",
        }

    def configure(self, **kwargs) -> None:
        self.config = kwargs


@pytest.fixture
def fake_dependencies() -> dict:
    return {
        "settings": Settings(
            app_id=1,
            access_key_id="ak",
            access_key_secret="sk",
            command_ws_url="ws://127.0.0.1:43001/",
            command_ws_uid="123456",
            command_ws_token="token",
            command_ws_user_id="123456",
            gift_mapping_path="config/gift_command_mappings.json",
        ),
        "event_hub": EventHub(),
        "api_client": FakeApiClient(),
        "ws_client": FakeWsClient(),
        "gift_dispatcher": FakeGiftDispatcher(),
        "danmaku_dispatcher": FakeDanmakuDispatcher(),
        "bluetooth_dispatcher": FakeBluetoothDispatcher(),
    }


@pytest.mark.anyio
async def test_stop_without_running_session_keeps_idle(fake_dependencies: dict) -> None:
    service = LiveSessionService(**fake_dependencies)

    await service.stop()

    assert service.status == SessionStatus.IDLE


@pytest.mark.anyio
async def test_handle_interaction_end_resets_current_session(fake_dependencies: dict) -> None:
    service = LiveSessionService(**fake_dependencies)
    service.status = SessionStatus.RUNNING
    service.game_id = "game-123"
    service.room_id = 100
    service.anchor_name = "主播"

    await service._handle_event(
        {
            "event_type": "system",
            "cmd": "LIVE_OPEN_PLATFORM_INTERACTION_END",
            "room_id": 0,
            "open_id": "",
            "uname": "",
            "timestamp": 1714113037,
            "payload": {"game_id": "game-123", "message": "互动场次已结束"},
        }
    )

    assert service.status == SessionStatus.IDLE
    assert service.game_id == ""
    assert "互动场次已结束" in service.last_error


@pytest.mark.anyio
async def test_handle_gift_event_dispatches_command(fake_dependencies: dict) -> None:
    service = LiveSessionService(**fake_dependencies)

    event = {
        "event_type": "gift",
        "cmd": "LIVE_OPEN_PLATFORM_SEND_GIFT",
        "room_id": 1,
        "open_id": "user-open-id",
        "uname": "测试用户",
        "timestamp": 1714113037,
        "payload": {
            "gift_id": 1001,
            "gift_name": "小花花",
            "gift_num": 1,
            "price": 1000,
            "r_price": 1000,
        },
    }

    await service._handle_event(event)

    assert service.gift_dispatcher.called_with == event
    assert service.last_command_id == "player_hurt"
    assert service.last_command_message == "指令发送成功"


@pytest.mark.anyio
async def test_handle_like_event_dispatches_command(fake_dependencies: dict) -> None:
    class FakeLikeDispatcher(FakeGiftDispatcher):
        async def dispatch_like_event(self, event: dict) -> dict:
            self.called_with = event
            return {
                "matched": True,
                "command_id": "like_trigger",
                "success": True,
                "message": "点赞指令发送成功",
                "trigger_count": 1,
                "sent_count": 1,
            }

        def reset_runtime_state(self) -> None:
            return None

        def set_like_multiple(self, like_multiple: int) -> None:
            self.like_multiple = like_multiple

    fake_dependencies["gift_dispatcher"] = FakeLikeDispatcher()
    service = LiveSessionService(**fake_dependencies)

    event = {
        "event_type": "like",
        "cmd": "LIVE_OPEN_PLATFORM_LIKE",
        "room_id": 1,
        "open_id": "user-open-id",
        "uname": "测试用户",
        "timestamp": 1714113037,
        "payload": {
            "like_text": "点赞了直播间",
            "like_count": 100,
        },
    }

    await service._handle_event(event)

    assert service.gift_dispatcher.called_with == event
    assert service.last_command_id == "like_trigger"
    assert service.last_command_message == "点赞指令发送成功"


@pytest.mark.anyio
async def test_handle_interact_event_dispatches_command(fake_dependencies: dict) -> None:
    class FakeInteractDispatcher(FakeGiftDispatcher):
        async def dispatch_interact_event(self, event: dict) -> dict:
            self.called_with = event
            return {
                "matched": True,
                "command_id": "interact_trigger",
                "success": True,
                "message": "互动指令发送成功",
                "trigger_count": 1,
                "sent_count": 1,
            }

        def reset_runtime_state(self) -> None:
            return None

    fake_dependencies["gift_dispatcher"] = FakeInteractDispatcher()
    service = LiveSessionService(**fake_dependencies)

    event = {
        "event_type": "interact",
        "cmd": "INTERACT_WORD_V2",
        "room_id": 1,
        "open_id": "user-open-id",
        "uname": "互动用户",
        "timestamp": 1714113037,
        "payload": {
            "uid": 1001,
            "msg_type": 2,
            "interact_type": "follow",
            "interact_label": "关注",
        },
    }

    await service._handle_event(event)

    assert service.gift_dispatcher.called_with == event
    assert service.last_command_id == "interact_trigger"
    assert service.last_command_message == "互动指令发送成功"


@pytest.mark.anyio
async def test_handle_danmaku_event_dispatches_command(fake_dependencies: dict) -> None:
    class FakeDanmakuDispatcher(FakeGiftDispatcher):
        async def dispatch(self, event: dict) -> dict:
            self.called_with = event
            return {
                "matched": True,
                "command_id": "danmaku_trigger",
                "success": True,
                "message": "弹幕关键词触发成功",
                "trigger_count": 1,
                "sent_count": 1,
                "matched_keywords": ["开火"],
            }

    fake_dependencies["danmaku_dispatcher"] = FakeDanmakuDispatcher()
    service = LiveSessionService(**fake_dependencies)

    event = {
        "event_type": "danmaku_governor",
        "cmd": "LIVE_OPEN_PLATFORM_DM",
        "room_id": 1,
        "open_id": "user-open-id",
        "uname": "测试用户",
        "timestamp": 1714113037,
        "payload": {
            "msg": "大家准备开火",
            "guard_level": 1,
        },
    }

    await service._handle_event(event)

    assert service.danmaku_dispatcher.called_with == event
    assert service.last_command_id == "danmaku_trigger"
    assert service.last_command_message == "弹幕关键词触发成功"


@pytest.mark.anyio
async def test_handle_gift_event_dispatches_bluetooth_waveform(fake_dependencies: dict) -> None:
    service = LiveSessionService(**fake_dependencies)
    service.output_mode = "bluetooth"

    event = {
        "event_type": "gift",
        "cmd": "LIVE_OPEN_PLATFORM_SEND_GIFT",
        "room_id": 1,
        "open_id": "user-open-id",
        "uname": "测试用户",
        "timestamp": 1714113037,
        "payload": {
            "gift_id": 1001,
            "gift_name": "小花花",
            "gift_num": 1,
            "price": 1000,
            "r_price": 1000,
        },
    }

    await service._handle_event(event)

    assert service.bluetooth_dispatcher.called_with == event
    assert event["bluetooth_dispatch"]["waveform_id"] == "ems-default-pulse"
    assert service.gift_dispatcher.called_with is None


@pytest.mark.anyio
async def test_handle_gift_event_does_not_dispatch_bluetooth_in_im_mode(fake_dependencies: dict) -> None:
    service = LiveSessionService(**fake_dependencies)
    service.output_mode = "im"

    event = {
        "event_type": "gift",
        "cmd": "LIVE_OPEN_PLATFORM_SEND_GIFT",
        "room_id": 1,
        "open_id": "user-open-id",
        "uname": "测试用户",
        "timestamp": 1714113037,
        "payload": {
            "gift_id": 1001,
            "gift_name": "小花花",
            "gift_num": 1,
            "price": 1000,
            "r_price": 1000,
        },
    }

    await service._handle_event(event)

    assert service.gift_dispatcher.called_with == event
    assert service.bluetooth_dispatcher.called_with is None
    assert "bluetooth_dispatch" not in event


@pytest.mark.anyio
async def test_start_configures_bluetooth_danmaku_keywords(fake_dependencies: dict) -> None:
    service = LiveSessionService(**fake_dependencies)

    await service.start(
        value="code-demo",
        output_mode="bluetooth",
        danmaku_enabled=True,
        danmaku_keywords="开火,冲冲冲",
        danmaku_cooldown_seconds=5,
        danmaku_user_limit_window_seconds=60,
        danmaku_user_limit_max_triggers=2,
        danmaku_min_guard_level=2,
    )

    assert service.bluetooth_dispatcher.config == {
        "danmaku_enabled": True,
        "danmaku_keywords": "开火,冲冲冲",
        "danmaku_cooldown_seconds": 5,
        "danmaku_user_limit_window_seconds": 60,
        "danmaku_user_limit_max_triggers": 2,
        "danmaku_min_guard_level": 2,
    }
