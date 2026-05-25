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


class FakeDanmakuDispatcher:
    def __init__(self) -> None:
        self.called_with: dict | None = None

    @property
    def is_enabled(self) -> bool:
        return True

        def configure(self, **kwargs) -> None:
            self.config = kwargs

    def reset_runtime_state(self) -> None:
        return None


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


class FakeFlakyThirdPartyWsClient:
    def __init__(self) -> None:
        self.connected_room_ids: list[int] = []
        self.disconnect_called = False
        self.messages_by_room = {
            123456: [
                {
                    "cmd": "SEND_GIFT",
                    "data": {
                        "giftId": 1001,
                        "giftName": "小花花",
                        "num": 1,
                        "uname": "房间A用户",
                        "price": 1000,
                        "timestamp": 1714113037,
                    },
                }
            ],
            654321: [
                {
                    "cmd": "SEND_GIFT",
                    "data": {
                        "giftId": 1002,
                        "giftName": "牛哇牛哇",
                        "num": 1,
                        "uname": "房间B用户",
                        "price": 1000,
                        "timestamp": 1714113038,
                    },
                }
            ],
        }

    async def connect_and_consume(self, *, room_id: int, on_message) -> None:
        self.connected_room_ids.append(room_id)
        for message in self.messages_by_room.get(room_id, []):
            await on_message(message)
        await asyncio.sleep(0)

    async def disconnect(self) -> None:
        self.disconnect_called = True
        raise RuntimeError("尚未连接服务器")


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
async def test_third_party_session_consumes_like_and_dispatches_command() -> None:
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

    event_hub = EventHub()
    gift_dispatcher = FakeLikeDispatcher()
    ws_client = FakeThirdPartyWsClient(
        messages=[
            {
                "cmd": "LIKE_INFO_V3_CLICK",
                "data": {
                    "uname": "点赞用户",
                    "like_text": "点赞了直播间",
                    "like_count": 100,
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
    assert events[-1]["event_type"] == "like"
    assert events[-1]["command_dispatch"]["command_id"] == "like_trigger"

    await service.stop()


@pytest.mark.anyio
async def test_third_party_session_consumes_danmaku_and_dispatches_command() -> None:
    class FakeDanmakuDispatcher(FakeGiftDispatcher):
        async def dispatch(self, event: dict) -> dict:
            self.called_with = event
            return {
                "matched": True,
                "command_id": "command_seven",
                "success": True,
                "message": "弹幕关键词触发成功",
                "trigger_count": 1,
                "sent_count": 1,
                "matched_keywords": ["开火"],
            }

    event_hub = EventHub()
    gift_dispatcher = FakeGiftDispatcher()
    danmaku_dispatcher = FakeDanmakuDispatcher()
    ws_client = FakeThirdPartyWsClient(
        messages=[
            {
                "cmd": "DANMU_MSG",
                "info": [
                    [],
                    "现在开火",
                    [123, "弹幕用户"],
                ],
            }
        ]
    )
    service = ThirdPartyLiveSessionService(
        event_hub=event_hub,
        gift_dispatcher=gift_dispatcher,
        danmaku_dispatcher=danmaku_dispatcher,
        ws_client=ws_client,
        room_info_fetcher=fake_room_info_fetcher,
    )

    await service.start(value="123456")
    await asyncio.sleep(0.05)

    events = event_hub.snapshot()

    assert danmaku_dispatcher.called_with is not None
    assert events[-1]["event_type"] == "danmaku"
    assert events[-1]["command_dispatch"]["command_id"] == "command_seven"

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


@pytest.mark.anyio
async def test_third_party_session_can_restart_another_room_after_disconnect_error() -> None:
    event_hub = EventHub()
    ws_client = FakeFlakyThirdPartyWsClient()
    service = ThirdPartyLiveSessionService(
        event_hub=event_hub,
        gift_dispatcher=FakeGiftDispatcher(),
        ws_client=ws_client,
        room_info_fetcher=fake_room_info_fetcher,
    )

    await service.start(value="123456")
    await asyncio.sleep(0.05)
    await service.stop()
    await service.start(value="654321")
    await asyncio.sleep(0.05)

    events = event_hub.snapshot()

    assert ws_client.disconnect_called is True
    assert ws_client.connected_room_ids == [123456, 654321]
    assert events[-1]["uname"] == "房间B用户"
    assert service.room_id == 654321
