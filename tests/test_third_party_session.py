from __future__ import annotations

import asyncio

import pytest

from app.services.event_hub import EventHub
from app.services.third_party_session import ThirdPartyLiveSessionService


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
            "command_id": "player_hurt",
            "success": True,
            "message": "指令发送成功",
        }


class FakeThirdPartyWsClient:
    def __init__(self, messages: list[dict] | None = None) -> None:
        self.messages = messages or []
        self.connected_room_id: int | None = None
        self.disconnect_called = False

    async def connect_and_consume(self, *, room_id: int, on_message) -> None:
        self.connected_room_id = room_id
        for message in self.messages:
            await on_message(message)
        await asyncio.sleep(0)

    async def disconnect(self) -> None:
        self.disconnect_called = True


async def fake_room_info_fetcher(room_id: int) -> dict:
    return {
        "anchor_info": {
            "base_info": {
                "uname": f"主播{room_id}",
            }
        }
    }


@pytest.mark.anyio
async def test_third_party_session_consumes_gift_and_dispatches_command() -> None:
    event_hub = EventHub()
    gift_dispatcher = FakeGiftDispatcher()
    ws_client = FakeThirdPartyWsClient(
        messages=[
            {
                "cmd": "SEND_GIFT",
                "data": {
                    "giftId": 1001,
                    "giftName": "小花花",
                    "num": 2,
                    "uname": "测试用户",
                    "price": 1000,
                    "timestamp": 1714113037,
                },
            }
        ]
    )
    service = ThirdPartyLiveSessionService(
        event_hub=event_hub,
        gift_dispatcher=gift_dispatcher,
        ws_client=ws_client,
        room_info_fetcher=fake_room_info_fetcher,
    )

    await service.start(value="123456")
    await asyncio.sleep(0.05)

    events = event_hub.snapshot()

    assert ws_client.connected_room_id == 123456
    assert service.anchor_name == "主播123456"
    assert gift_dispatcher.called_with is not None
    assert events[-1]["source"] == "third_party_ws"
    assert events[-1]["command_dispatch"]["command_id"] == "player_hurt"

    await service.stop()


@pytest.mark.anyio
async def test_third_party_session_consumes_combo_gift_and_dispatches_command() -> None:
    event_hub = EventHub()
    gift_dispatcher = FakeGiftDispatcher()
    ws_client = FakeThirdPartyWsClient(
        messages=[
            {
                "cmd": "COMBO_SEND",
                "data": {
                    "gift_id": 31039,
                    "gift_name": "牛哇牛哇",
                    "combo_num": 3,
                    "uname": "测试用户",
                    "price": 100,
                    "combo_total_coin": 300,
                    "timestamp": 1714113037,
                },
            }
        ]
    )
    service = ThirdPartyLiveSessionService(
        event_hub=event_hub,
        gift_dispatcher=gift_dispatcher,
        ws_client=ws_client,
        room_info_fetcher=fake_room_info_fetcher,
    )

    await service.start(value="123456")
    await asyncio.sleep(0.05)

    events = event_hub.snapshot()

    assert gift_dispatcher.called_with is not None
    assert events[-1]["event_type"] == "gift"
    assert events[-1]["cmd"] == "COMBO_SEND"
    assert events[-1]["payload"]["gift_num"] == 3

    await service.stop()


@pytest.mark.anyio
async def test_third_party_session_stop_disconnects_ws_client() -> None:
    ws_client = FakeThirdPartyWsClient()
    service = ThirdPartyLiveSessionService(
        event_hub=EventHub(),
        ws_client=ws_client,
    )

    await service.start(value="123456")
    await service.stop()

    assert ws_client.disconnect_called is True
