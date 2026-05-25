from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.bluetooth.models import EmsWaveform
from app.bluetooth.models import EmsWaveformStep
from app.bluetooth.runtime.bleak_runtime import BleakBluetoothRuntime


EMS_SERVICE_UUID = "0000ff30-0000-1000-8000-00805f9b34fb"
EMS_WRITE_CHAR_UUID = "0000ff31-0000-1000-8000-00805f9b34fb"


class FakeBleakClient:
    def __init__(self, ble_device, disconnected_callback=None, **kwargs) -> None:
        self.ble_device = ble_device
        self.disconnected_callback = disconnected_callback
        self.connected = False
        self.writes: list[tuple[str, bytes, bool]] = []

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def write_gatt_char(self, char_specifier, data, response: bool | None = None) -> None:
        self.writes.append((char_specifier, bytes(data), bool(response)))

    @property
    def is_connected(self) -> bool:
        return self.connected


@pytest.mark.anyio
async def test_bleak_runtime_scan_filters_and_classifies_supported_ems_devices() -> None:
    async def fake_discover(*, timeout: float, return_adv: bool):
        assert timeout == 6
        assert return_adv is True
        return {
            "AA:BB:CC:DD:EE:01": (
                SimpleNamespace(address="AA:BB:CC:DD:EE:01", name="YYC-DJ-V2-001", rssi=-41),
                SimpleNamespace(local_name="YYC-DJ-V2-001", service_uuids=[EMS_SERVICE_UUID]),
            ),
            "AA:BB:CC:DD:EE:02": (
                SimpleNamespace(address="AA:BB:CC:DD:EE:02", name="YYC-DJ-001", rssi=-53),
                SimpleNamespace(local_name="YYC-DJ-001", service_uuids=[EMS_SERVICE_UUID]),
            ),
            "AA:BB:CC:DD:EE:03": (
                SimpleNamespace(address="AA:BB:CC:DD:EE:03", name="Heart Rate Sensor", rssi=-60),
                SimpleNamespace(local_name="Heart Rate Sensor", service_uuids=["0000180d-0000-1000-8000-00805f9b34fb"]),
            ),
        }

    runtime = BleakBluetoothRuntime(
        scan_timeout_seconds=6,
        scanner_discover=fake_discover,
        client_factory=FakeBleakClient,
    )

    devices = await runtime.scan()

    assert [item.device_id for item in devices] == [
        "AA:BB:CC:DD:EE:01",
        "AA:BB:CC:DD:EE:02",
    ]
    assert devices[0].protocol == "ems_v2"
    assert devices[1].protocol == "ems_v1"
    assert all(item.device_type == "ems" for item in devices)


@pytest.mark.anyio
async def test_bleak_runtime_can_connect_and_disconnect_scanned_device() -> None:
    async def fake_discover(*, timeout: float, return_adv: bool):
        return {
            "AA:BB:CC:DD:EE:01": (
                SimpleNamespace(address="AA:BB:CC:DD:EE:01", name="YYC-DJ-V2-001", rssi=-41),
                SimpleNamespace(local_name="YYC-DJ-V2-001", service_uuids=[EMS_SERVICE_UUID]),
            ),
        }

    runtime = BleakBluetoothRuntime(
        scan_timeout_seconds=5,
        scanner_discover=fake_discover,
        client_factory=FakeBleakClient,
    )

    await runtime.scan()
    connected = await runtime.connect("AA:BB:CC:DD:EE:01")
    disconnected = await runtime.disconnect()

    assert connected.connected is True
    assert connected.device is not None
    assert connected.device.device_id == "AA:BB:CC:DD:EE:01"
    assert runtime.get_status().connected is False
    assert disconnected.connected is False


@pytest.mark.anyio
async def test_bleak_runtime_writes_waveform_packets_to_ems_characteristic() -> None:
    sleep_calls: list[float] = []

    async def fake_discover(*, timeout: float, return_adv: bool):
        return {
            "AA:BB:CC:DD:EE:01": (
                SimpleNamespace(address="AA:BB:CC:DD:EE:01", name="YYC-DJ-V2-001", rssi=-41),
                SimpleNamespace(local_name="YYC-DJ-V2-001", service_uuids=[EMS_SERVICE_UUID]),
            ),
        }

    async def fake_sleep(seconds: float) -> None:
        sleep_calls.append(seconds)

    runtime = BleakBluetoothRuntime(
        scan_timeout_seconds=5,
        scanner_discover=fake_discover,
        client_factory=FakeBleakClient,
        sleep_func=fake_sleep,
    )
    waveform = EmsWaveform(
        id="wf-1",
        name="测试波形",
        steps=[
            EmsWaveformStep(duration_ms=180, channel_a=48, channel_b=24),
            EmsWaveformStep(duration_ms=120, channel_a=0, channel_b=0),
        ],
    )

    await runtime.scan()
    await runtime.connect("AA:BB:CC:DD:EE:01")
    await runtime.play_waveform(waveform)

    client = runtime._client
    assert client is not None
    assert [item[0] for item in client.writes] == [
        EMS_WRITE_CHAR_UUID,
        EMS_WRITE_CHAR_UUID,
        EMS_WRITE_CHAR_UUID,
    ]
    assert len(client.writes[0][1]) == 10
    assert sleep_calls == [0.18, 0.12]
