from __future__ import annotations

import pytest

from app.bluetooth.runtime.memory_runtime import MemoryBluetoothRuntime
from app.bluetooth.service import BluetoothService
from app.services.event_hub import EventHub


@pytest.mark.anyio
async def test_service_can_scan_connect_and_disconnect(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    scanned = await service.scan()
    connected = await service.connect(scanned[0].device_id)
    disconnected = await service.disconnect()

    assert scanned
    assert connected.connected is True
    assert disconnected.connected is False


@pytest.mark.anyio
async def test_service_connect_success_publishes_control_log(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_hub = EventHub()
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json", event_hub=event_hub)

    scanned = await service.scan()
    await service.connect(scanned[0].device_id)

    control_event = event_hub.control_snapshot()[-1]

    assert control_event["type"] == "bluetooth_connect"
    assert control_event["payload"]["success"] is True
    assert control_event["payload"]["device_id"] == scanned[0].device_id
    assert control_event["payload"]["device_name"] == scanned[0].name


@pytest.mark.anyio
async def test_service_connect_failure_publishes_control_log(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_hub = EventHub()
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json", event_hub=event_hub)

    await service.scan()
    with pytest.raises(ValueError, match="未找到指定蓝牙设备"):
        await service.connect("missing-device")

    control_event = event_hub.control_snapshot()[-1]

    assert control_event["type"] == "bluetooth_connect"
    assert control_event["payload"]["success"] is False
    assert control_event["payload"]["device_id"] == "missing-device"
    assert control_event["payload"]["message"] == "未找到指定蓝牙设备"


@pytest.mark.anyio
async def test_service_status_payload_includes_runtime_details(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    await service.scan()
    status = service.get_status_payload()

    assert status["enabled"] is False
    assert status["connected"] is False
    assert status["runtime_backend"] == "memory"
    assert isinstance(status["devices"], list)
    assert isinstance(status["waveforms"], list)
    assert isinstance(status["rules"], list)
    rule_map = {
        item["id"]: item
        for item in status["rules"]
    }
    assert rule_map["gift-tier-01"]["enabled"] is True
    assert rule_map["gift-tier-01"]["event_label"] == "礼物事件"
    assert rule_map["gift-tier-01"]["rule_label"] == "礼物档位 01 · 0-99"
    assert rule_map["gift-tier-01"]["waveform_name"] == "EMS 预设 01 - 呼吸"
    assert rule_map["gift-tier-10"]["rule_label"] == "礼物档位 10 · 1000000+"
    assert rule_map["gift-tier-10"]["waveform_name"] == "EMS 预设 10 - 渐变弹跳"
    assert rule_map["like-default"]["event_label"] == "点赞事件"
    assert rule_map["like-default"]["waveform_name"] == "EMS 预设 01 - 呼吸"
    assert rule_map["danmaku-normal"]["event_label"] == "普通弹幕"
    assert rule_map["danmaku-normal"]["waveform_name"] == "EMS 预设 03 - 连击"
    assert rule_map["danmaku-captain"]["event_label"] == "舰长弹幕"
    assert rule_map["danmaku-captain"]["waveform_name"] == "EMS 预设 04 - 快速按捏"
    assert rule_map["danmaku-commander"]["event_label"] == "提督弹幕"
    assert rule_map["danmaku-commander"]["waveform_name"] == "EMS 预设 05 - 按捏渐强"
    assert rule_map["danmaku-governor"]["event_label"] == "总督弹幕"
    assert rule_map["danmaku-governor"]["waveform_name"] == "EMS 预设 06 - 心跳节奏"
    assert rule_map["super-chat-tier-01"]["event_label"] == "醒目留言"
    assert rule_map["super-chat-tier-01"]["rule_label"] == "醒目留言档位 01 · 30-49"
    assert rule_map["super-chat-tier-06"]["rule_label"] == "醒目留言档位 06 · 2000+"
    assert rule_map["guard-buy-tier-01"]["event_label"] == "上舰"
    assert rule_map["guard-buy-tier-01"]["rule_label"] == "上舰档位 01 · 100000-999999"
    assert rule_map["guard-buy-tier-03"]["event_label"] == "上舰"
    assert rule_map["guard-renew-tier-01"]["event_label"] == "续费"
    assert rule_map["guard-renew-tier-01"]["rule_label"] == "续费档位 01 · 50000-999999"
    assert rule_map["guard-renew-tier-03"]["event_label"] == "续费"
    assert rule_map["interact-default"]["event_label"] == "互动事件"
    assert status["battery_level"] is None


@pytest.mark.anyio
async def test_service_overlay_payload_includes_battery_level(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    await service.scan()
    await service.connect("ems-demo-002")
    overlay = service.get_overlay_payload()

    assert overlay["battery_level"] == 100


@pytest.mark.anyio
async def test_service_waveform_trigger_publishes_control_log(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_hub = EventHub()
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json", event_hub=event_hub)

    result = await service.trigger_waveform(event_type="gift", waveform_id="ems-preset-01")

    assert result["success"] is True
    assert event_hub.control_snapshot()[-1]["type"] == "bluetooth_trigger"
    assert event_hub.control_snapshot()[-1]["payload"]["waveform_id"] == "ems-preset-01"
    assert event_hub.control_snapshot()[-1]["payload"]["max_strength"] > 0


@pytest.mark.anyio
async def test_service_preview_waveform_publishes_control_log(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_hub = EventHub()
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json", event_hub=event_hub)

    result = await service.preview_waveform("ems-preset-01")

    assert result["success"] is True
    assert result["event_type"] == "waveform_preview"
    assert "测试播放" in result["message"]
    assert event_hub.control_snapshot()[-1]["type"] == "bluetooth_trigger"
    assert event_hub.control_snapshot()[-1]["payload"]["event_type"] == "waveform_preview"
    assert event_hub.control_snapshot()[-1]["payload"]["waveform_id"] == "ems-preset-01"


def test_service_overlay_payload_includes_recent_live_events(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_hub = EventHub()
    event_hub.publish(
        {
            "event_type": "danmaku",
            "uname": "弹幕用户",
            "timestamp": 1714113037,
            "payload": {
                "msg": "开火",
                "guard_label": "舰长",
            },
            "bluetooth_dispatch": {
                "waveform_id": "ems-preset-04",
                "waveform_name": "EMS 预设 04 - 快速按捏",
                "success": True,
            },
        }
    )
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json", event_hub=event_hub)

    overlay = service.get_overlay_payload()

    assert overlay["recent_events"][0]["msg"] == "开火"
    assert overlay["recent_events"][0]["event_label"] == "弹幕"
    assert overlay["recent_events"][0]["guard_label"] == "舰长"
    assert overlay["recent_events"][0]["waveform_name"] == "EMS 预设 04 - 快速按捏"


def test_service_overlay_payload_includes_recent_like_event(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    event_hub = EventHub()
    event_hub.publish(
        {
            "event_type": "like",
            "uname": "点赞用户",
            "timestamp": 1714113038,
            "payload": {
                "like_text": "点赞了直播间",
                "like_count": 120,
            },
        }
    )
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json", event_hub=event_hub)

    overlay = service.get_overlay_payload()

    assert overlay["recent_events"][0]["event_label"] == "点赞"
    assert overlay["recent_events"][0]["msg"] == "点赞了直播间 (120)"


def test_create_default_prefers_real_runtime_when_available(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_runtime = MemoryBluetoothRuntime()

    def fake_factory(*, scan_timeout_seconds: int, connect_timeout_seconds: int, auto_reconnect: bool):
        assert scan_timeout_seconds == 15
        assert connect_timeout_seconds == 20
        assert auto_reconnect is True
        return fake_runtime

    monkeypatch.setattr("app.bluetooth.service.create_real_bluetooth_runtime", fake_factory)

    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    assert service.runtime is fake_runtime


def test_create_default_falls_back_to_memory_runtime_when_real_runtime_unavailable(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_factory(*, scan_timeout_seconds: int, connect_timeout_seconds: int, auto_reconnect: bool):
        raise RuntimeError(f"bleak init failed: {scan_timeout_seconds}/{connect_timeout_seconds}/{auto_reconnect}")

    monkeypatch.setattr("app.bluetooth.service.create_real_bluetooth_runtime", fake_factory)

    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    assert isinstance(service.runtime, MemoryBluetoothRuntime)


def test_service_can_create_blank_custom_waveform(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    result = service.create_waveform(name="我的波形")

    assert result["success"] is True
    assert result["waveform"]["name"] == "我的波形"
    assert result["waveform"]["builtin"] is False
    assert result["waveform"]["steps"][0]["duration_ms"] == 200
    assert result["waveform"]["steps"][0]["channel_a"] == 0
    assert result["waveform"]["steps"][0]["channel_b"] == 0
    assert result["waveforms"][0]["id"] == result["waveform"]["id"]
    assert service.payload.ems_waveforms[0].id == result["waveform"]["id"]


def test_service_can_duplicate_builtin_waveform(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    result = service.duplicate_waveform(source_waveform_id="ems-preset-01", name="")
    source_waveform = next(item for item in service.payload.ems_waveforms if item.id == "ems-preset-01")

    assert result["success"] is True
    assert result["waveform"]["id"].startswith("custom-wave-")
    assert result["waveform"]["builtin"] is False
    assert result["waveform"]["name"] == "EMS 预设 01 - 呼吸 - 副本"
    assert len(result["waveform"]["steps"]) == len(source_waveform.steps)
    assert result["waveforms"][0]["id"] == result["waveform"]["id"]
    assert service.payload.ems_waveforms[0].id == result["waveform"]["id"]


def test_service_can_update_custom_waveform_steps(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")
    created = service.create_waveform(name="待编辑波形")

    result = service.update_waveform(
        waveform_id=created["waveform"]["id"],
        name="已编辑波形",
        steps=[
            {"duration_ms": 180, "channel_a": 220, "channel_b": -10},
            {"duration_ms": 220, "channel_a": 120, "channel_b": 90},
        ],
    )

    assert result["success"] is True
    assert result["waveform"]["name"] == "已编辑波形"
    assert result["waveform"]["steps"][0]["channel_a"] == 180
    assert result["waveform"]["steps"][0]["channel_b"] == 0
    assert result["waveform"]["steps"][1]["channel_a"] == 120
    assert result["waveform"]["steps"][1]["channel_b"] == 90


def test_service_rejects_delete_when_waveform_is_still_referenced(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")
    created = service.create_waveform(name="被引用波形")
    service.payload.bluetooth_event_rules[0].waveform_id = created["waveform"]["id"]

    with pytest.raises(ValueError, match="请先修改规则绑定后再删除该波形"):
        service.delete_waveform(created["waveform"]["id"])


def test_service_default_payload_includes_im_aligned_special_price_tiers(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    rule_groups = {
        group["group_id"]: group["rules"]
        for group in service.get_studio_payload()["rule_groups"]
    }

    assert [rule["rule_label"] for rule in rule_groups["super_chat"]] == [
        "醒目留言档位 01 · 30-49",
        "醒目留言档位 02 · 50-99",
        "醒目留言档位 03 · 100-499",
        "醒目留言档位 04 · 500-999",
        "醒目留言档位 05 · 1000-1999",
        "醒目留言档位 06 · 2000+",
    ]
    assert [rule["filters"] for rule in rule_groups["guard_buy"]] == [
        {"min_price": 100000, "max_price": 999999},
        {"min_price": 1000000, "max_price": 9999999},
        {"min_price": 10000000, "max_price": None},
    ]
    assert [rule["filters"] for rule in rule_groups["guard_renew"]] == [
        {"min_price": 50000, "max_price": 999999},
        {"min_price": 1000000, "max_price": 9999999},
        {"min_price": 10000000, "max_price": None},
    ]


def test_service_save_rules_allows_editing_gift_price_ranges_and_sorts_by_price(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    payload = service.save_rules(
        [
            {
                "id": "gift-tier-02",
                "enabled": True,
                "waveform_id": "ems-preset-02",
                "min_price": 200,
                "max_price": 499,
            },
            {
                "id": "gift-tier-01",
                "enabled": True,
                "waveform_id": "ems-preset-01",
                "min_price": 0,
                "max_price": 199,
            },
        ]
    )

    gift_rules = payload["rule_groups"][0]["rules"]

    assert [rule["id"] for rule in gift_rules[:2]] == ["gift-tier-01", "gift-tier-02"]
    assert gift_rules[0]["filters"] == {"min_price": 0, "max_price": 199}
    assert gift_rules[0]["rule_label"] == "礼物档位 01 · 0-199"
    assert gift_rules[1]["filters"] == {"min_price": 200, "max_price": 499}
    assert gift_rules[1]["rule_label"] == "礼物档位 02 · 200-499"


def test_service_save_rules_allows_editing_super_chat_price_ranges_and_sorts_by_price(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    payload = service.save_rules(
        [
            {
                "id": "super-chat-tier-02",
                "enabled": True,
                "waveform_id": "ems-preset-07",
                "min_price": 60,
                "max_price": 99,
            },
            {
                "id": "super-chat-tier-01",
                "enabled": True,
                "waveform_id": "ems-preset-07",
                "min_price": 30,
                "max_price": 59,
            },
        ]
    )

    super_chat_rules = next(
        group["rules"]
        for group in payload["rule_groups"]
        if group["group_id"] == "super_chat"
    )

    assert [rule["id"] for rule in super_chat_rules[:2]] == [
        "super-chat-tier-01",
        "super-chat-tier-02",
    ]
    assert super_chat_rules[0]["filters"] == {"min_price": 30, "max_price": 59}
    assert super_chat_rules[0]["rule_label"] == "醒目留言档位 01 · 30-59"
    assert super_chat_rules[1]["filters"] == {"min_price": 60, "max_price": 99}
    assert super_chat_rules[1]["rule_label"] == "醒目留言档位 02 · 60-99"


def test_service_save_rules_rejects_overlapping_enabled_gift_price_ranges(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    with pytest.raises(ValueError, match="价格区间重叠"):
        service.save_rules(
            [
                {
                    "id": "gift-tier-01",
                    "enabled": True,
                    "waveform_id": "ems-preset-01",
                    "min_price": 0,
                    "max_price": 100,
                },
                {
                    "id": "gift-tier-02",
                    "enabled": True,
                    "waveform_id": "ems-preset-02",
                    "min_price": 100,
                    "max_price": 299,
                },
            ]
        )


def test_service_save_rules_rejects_overlapping_enabled_guard_buy_price_ranges(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    with pytest.raises(ValueError, match="上舰.*价格区间重叠"):
        service.save_rules(
            [
                {
                    "id": "guard-buy-tier-01",
                    "enabled": True,
                    "waveform_id": "ems-preset-08",
                    "min_price": 100000,
                    "max_price": 999999,
                },
                {
                    "id": "guard-buy-tier-02",
                    "enabled": True,
                    "waveform_id": "ems-preset-14",
                    "min_price": 999999,
                    "max_price": 9999999,
                },
            ]
        )


def test_service_save_rules_allows_editing_super_chat_price_ranges(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    payload = service.save_rules(
        [
            {
                "id": "super-chat-tier-02",
                "enabled": True,
                "waveform_id": "ems-preset-08",
                "min_price": 60,
                "max_price": 99,
            }
        ]
    )

    sc_group = next(group for group in payload["rule_groups"] if group["group_id"] == "super_chat")
    sc_rule = next(rule for rule in sc_group["rules"] if rule["id"] == "super-chat-tier-02")

    assert sc_rule["filters"] == {"min_price": 60, "max_price": 99}
    assert sc_rule["rule_label"] == "醒目留言档位 02 · 60-99"


def test_service_save_rules_rejects_overlapping_enabled_super_chat_price_ranges(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.bluetooth.service.create_real_bluetooth_runtime",
        lambda **kwargs: MemoryBluetoothRuntime(),
    )
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    with pytest.raises(ValueError, match="醒目留言.*价格区间重叠"):
        service.save_rules(
            [
                {
                    "id": "super-chat-tier-01",
                    "enabled": True,
                    "waveform_id": "ems-preset-07",
                    "min_price": 30,
                    "max_price": 80,
                },
                {
                    "id": "super-chat-tier-02",
                    "enabled": True,
                    "waveform_id": "ems-preset-08",
                    "min_price": 80,
                    "max_price": 120,
                },
            ]
        )
