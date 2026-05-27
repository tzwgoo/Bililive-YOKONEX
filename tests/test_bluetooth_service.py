from __future__ import annotations

import pytest

from app.bluetooth.runtime.memory_runtime import MemoryBluetoothRuntime
from app.bluetooth.service import BluetoothService


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
    assert status["rules"][0]["enabled"] is True
    assert status["rules"][0]["event_label"] == "礼物事件"
    assert status["rules"][0]["rule_label"] == "礼物档位 01 · 0-99"
    assert status["rules"][0]["waveform_name"] == "EMS 预设 01 - 呼吸"
    assert status["rules"][9]["rule_label"] == "礼物档位 10 · 1000000+"
    assert status["rules"][9]["waveform_name"] == "EMS 预设 10 - 渐变弹跳"
    assert status["rules"][10]["event_label"] == "点赞事件"
    assert status["rules"][10]["waveform_name"] == "EMS 预设 01 - 呼吸"
    assert status["rules"][11]["event_label"] == "弹幕事件"
    assert status["rules"][11]["waveform_name"] == "EMS 预设 03 - 连击"
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
