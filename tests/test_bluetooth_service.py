from __future__ import annotations

import pytest

from app.bluetooth.service import BluetoothService


@pytest.mark.anyio
async def test_service_can_scan_connect_and_disconnect(tmp_path) -> None:
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    scanned = await service.scan()
    connected = await service.connect(scanned[0].device_id)
    disconnected = await service.disconnect()

    assert scanned
    assert connected.connected is True
    assert disconnected.connected is False


@pytest.mark.anyio
async def test_service_status_payload_includes_runtime_details(tmp_path) -> None:
    service = BluetoothService.create_default(config_path=tmp_path / "bluetooth.json")

    await service.scan()
    status = service.get_status_payload()

    assert status["enabled"] is False
    assert status["connected"] is False
    assert isinstance(status["devices"], list)
    assert isinstance(status["waveforms"], list)
    assert isinstance(status["rules"], list)
