from __future__ import annotations

import asyncio

import pytest

from app.services.douyin_session import DouyinLiveSessionService
from app.services.event_hub import EventHub


class FakeDouyinWsClient:
    def __init__(self, messages: list[dict]) -> None:
        self.messages = messages
        self.connected_room_id = ""
        self.base_url = ""
        self.disconnect_called = False

    async def connect_and_consume(self, *, room_id: str, base_url: str, on_message) -> None:
        self.connected_room_id = room_id
        self.base_url = base_url
        for message in self.messages:
            await on_message(message)
        await asyncio.sleep(0)

    async def disconnect(self) -> None:
        self.disconnect_called = True


class FakeGiftDispatcher:
    def __init__(self) -> None:
        self.called_with: dict | None = None

    @property
    def is_enabled(self) -> bool:
        return True

    async def dispatch_gift_event(self, event: dict) -> dict:
        self.called_with = event
        return {
            "matched": True,
            "command_id": "gift_trigger",
            "success": True,
            "message": "礼物指令发送成功",
        }

    async def dispatch_like_event(self, event: dict) -> dict:
        return {
            "matched": True,
            "command_id": "like_trigger",
            "success": True,
            "message": "点赞指令发送成功",
        }

    def set_like_multiple(self, like_multiple: int) -> None:
        self.like_multiple = like_multiple

    def set_trigger_mode(self, trigger_mode: str) -> None:
        self.trigger_mode = trigger_mode

    def reset_runtime_state(self) -> None:
        return None


class FakeManagedProcess:
    def __init__(self) -> None:
        self.terminated = False
        self.killed = False

    def poll(self):
        return None

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: int = 0) -> None:
        return None

    def kill(self) -> None:
        self.killed = True


@pytest.mark.anyio
async def test_douyin_session_consumes_like_and_dispatches_command() -> None:
    event_hub = EventHub()
    ws_client = FakeDouyinWsClient(
        [
            {
                "method": "WebcastLikeMessage",
                "count": 1,
                "total": 100,
                "livename": "抖音主播",
                "user": {"nickname": "点赞用户"},
            }
        ]
    )
    service = DouyinLiveSessionService(
        event_hub=event_hub,
        gift_dispatcher=FakeGiftDispatcher(),
        ws_client=ws_client,
    )

    await service.start(value="516466932480", douyin_ws_base_url="ws://127.0.0.1:1088")
    await asyncio.sleep(0.05)

    events = event_hub.snapshot()

    assert ws_client.connected_room_id == "516466932480"
    assert service.anchor_name == "抖音主播"
    assert events[-1]["source"] == "douyin_ws"
    assert events[-1]["event_type"] == "like"
    assert events[-1]["command_dispatch"]["command_id"] == "like_trigger"

    await service.stop()
    assert ws_client.disconnect_called is True


@pytest.mark.anyio
async def test_douyin_session_consumes_binding_gift_and_dispatches_command() -> None:
    event_hub = EventHub()
    ws_client = FakeDouyinWsClient(
        [
            {
                "method": "WebcastBindingGiftMessage",
                "msg": {
                    "giftId": "889",
                    "repeatCount": "3",
                    "fanTicketCount": "300",
                    "user": {"nickname": "送礼用户"},
                    "gift": {"name": "粉丝团礼物", "diamondCount": "100"},
                },
            }
        ]
    )
    gift_dispatcher = FakeGiftDispatcher()
    service = DouyinLiveSessionService(
        event_hub=event_hub,
        gift_dispatcher=gift_dispatcher,
        ws_client=ws_client,
    )

    await service.start(value="516466932480", douyin_ws_base_url="ws://127.0.0.1:1088")
    await asyncio.sleep(0.05)

    events = event_hub.snapshot()

    assert gift_dispatcher.called_with is not None
    assert gift_dispatcher.called_with["event_type"] == "gift"
    assert events[-1]["event_type"] == "gift"
    assert events[-1]["payload"]["gift_name"] == "粉丝团礼物"
    assert events[-1]["command_dispatch"]["command_id"] == "gift_trigger"

    await service.stop()


@pytest.mark.anyio
async def test_douyin_session_launches_configured_executable_when_local_port_is_closed(tmp_path) -> None:
    event_hub = EventHub()
    ws_client = FakeDouyinWsClient([])
    executable_path = tmp_path / "douyinLive.exe"
    executable_path.write_text("fake exe", encoding="utf-8")
    launched: list[tuple[str, int]] = []
    process = FakeManagedProcess()
    checks = iter([False, True, True])

    def fake_port_checker(host: str, port: int) -> bool:
        return next(checks, True)

    def fake_process_launcher(path, port: int):
        launched.append((str(path), port))
        return process

    service = DouyinLiveSessionService(
        event_hub=event_hub,
        ws_client=ws_client,
        port_checker=fake_port_checker,
        process_launcher=fake_process_launcher,
    )

    await service.start(
        value="516466932480",
        douyin_ws_base_url="ws://127.0.0.1:1088",
        douyin_executable_path=str(executable_path),
    )
    await asyncio.sleep(0.05)

    assert launched == [(str(executable_path), 1088)]
    assert ws_client.connected_room_id == "516466932480"

    await service.stop()
    assert process.terminated is True
