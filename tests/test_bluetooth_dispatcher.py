from __future__ import annotations

import pytest

from app.bluetooth.dispatcher import BluetoothDispatcher
from app.bluetooth.models import build_default_payload


class FakeBluetoothService:
    def __init__(self) -> None:
        self.payload = build_default_payload()
        for rule in self.payload.bluetooth_event_rules:
            rule.enabled = True
        self.triggered: list[tuple[str, str]] = []

    async def trigger_waveform(self, *, event_type: str, waveform_id: str) -> dict:
        self.triggered.append((event_type, waveform_id))
        return {
            "matched": True,
            "event_type": event_type,
            "waveform_id": waveform_id,
            "success": True,
            "message": f"{event_type} 已触发波形 {waveform_id}",
        }


@pytest.mark.anyio
async def test_dispatcher_triggers_waveform_for_gift_event() -> None:
    service = FakeBluetoothService()
    dispatcher = BluetoothDispatcher(bluetooth_service=service)

    result = await dispatcher.dispatch({"event_type": "gift", "payload": {"gift_name": "小花花", "price": 30000}})

    assert result["success"] is True
    assert service.triggered == [("gift", "ems-preset-06")]


@pytest.mark.anyio
async def test_dispatcher_matches_first_gift_tier_by_price_range() -> None:
    service = FakeBluetoothService()
    dispatcher = BluetoothDispatcher(bluetooth_service=service)

    result = await dispatcher.dispatch({"event_type": "gift", "payload": {"gift_name": "小花花", "price": 80}})

    assert result["success"] is True
    assert service.triggered == [("gift", "ems-preset-01")]


@pytest.mark.anyio
async def test_dispatcher_triggers_waveform_for_like_event() -> None:
    service = FakeBluetoothService()
    dispatcher = BluetoothDispatcher(bluetooth_service=service)

    result = await dispatcher.dispatch({"event_type": "like", "payload": {"like_count": 100}})

    assert result["success"] is True
    assert service.triggered == [("like", "ems-preset-01")]


@pytest.mark.anyio
async def test_dispatcher_matches_keywords_for_danmaku_event() -> None:
    service = FakeBluetoothService()
    for rule in service.payload.bluetooth_event_rules:
        if rule.event_type == "danmaku":
            rule.filters = {"keywords": ["开火"]}
    dispatcher = BluetoothDispatcher(bluetooth_service=service)
    dispatcher.configure(danmaku_enabled=True, danmaku_keywords="开火", danmaku_cooldown_seconds=3)

    result = await dispatcher.dispatch({"event_type": "danmaku", "payload": {"msg": "大家准备开火"}})

    assert result["success"] is True
    assert service.triggered == [("danmaku", "ems-preset-03")]


@pytest.mark.anyio
async def test_dispatcher_ignores_danmaku_without_keyword_match() -> None:
    service = FakeBluetoothService()
    for rule in service.payload.bluetooth_event_rules:
        if rule.event_type == "danmaku":
            rule.filters = {"keywords": ["开火"]}
    dispatcher = BluetoothDispatcher(bluetooth_service=service)

    result = await dispatcher.dispatch({"event_type": "danmaku", "payload": {"msg": "这条不会触发"}})

    assert result["matched"] is False
    assert service.triggered == []


@pytest.mark.anyio
async def test_dispatcher_blocks_danmaku_when_session_trigger_disabled() -> None:
    service = FakeBluetoothService()
    dispatcher = BluetoothDispatcher(bluetooth_service=service)
    dispatcher.configure(danmaku_enabled=False, danmaku_keywords="开火", danmaku_cooldown_seconds=3)

    result = await dispatcher.dispatch({"event_type": "danmaku", "payload": {"msg": "大家准备开火"}})

    assert result["matched"] is False
    assert "未开启" in result["message"]
    assert service.triggered == []


@pytest.mark.anyio
async def test_dispatcher_uses_session_keywords_for_bluetooth_danmaku() -> None:
    service = FakeBluetoothService()
    dispatcher = BluetoothDispatcher(bluetooth_service=service)
    dispatcher.configure(danmaku_enabled=True, danmaku_keywords="开火,冲冲冲", danmaku_cooldown_seconds=3)

    matched = await dispatcher.dispatch({"event_type": "danmaku", "payload": {"msg": "大家准备开火"}})
    not_matched = await dispatcher.dispatch({"event_type": "danmaku", "payload": {"msg": "只是路过"}})

    assert matched["success"] is True
    assert not_matched["matched"] is False
    assert service.triggered == [("danmaku", "ems-preset-03")]
