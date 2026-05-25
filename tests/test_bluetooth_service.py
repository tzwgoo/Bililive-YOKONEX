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
