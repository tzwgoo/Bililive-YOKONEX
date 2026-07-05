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
    @property
    def is_enabled(self) -> bool:
        return True

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
