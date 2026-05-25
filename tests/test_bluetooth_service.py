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


def test_create_default_prefers_real_runtime_when_available(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_runtime = MemoryBluetoothRuntime()

    def fake_factory(*, scan_timeout_seconds: int):
        assert scan_timeout_seconds == 8
        return fake_runtime

    monkeypatch.setattr("app.bluetooth.service.create_real_bluetooth_runtime", fake_factory)

    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    assert service.runtime is fake_runtime


def test_create_default_falls_back_to_memory_runtime_when_real_runtime_unavailable(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_factory(*, scan_timeout_seconds: int):
        raise RuntimeError(f"bleak init failed: {scan_timeout_seconds}")

    monkeypatch.setattr("app.bluetooth.service.create_real_bluetooth_runtime", fake_factory)

    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    assert isinstance(service.runtime, MemoryBluetoothRuntime)
