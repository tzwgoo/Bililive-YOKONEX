from __future__ import annotations

import asyncio
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
        self.notify_callbacks: dict[str, object] = {}

    async def connect(self) -> None:
        self.connected = True

    async def disconnect(self) -> None:
        self.connected = False

    async def write_gatt_char(self, char_specifier, data, response: bool | None = None) -> None:
        self.writes.append((char_specifier, bytes(data), bool(response)))

    async def start_notify(self, char_specifier, callback) -> None:
        self.notify_callbacks[str(char_specifier)] = callback

    async def stop_notify(self, char_specifier) -> None:
        self.notify_callbacks.pop(str(char_specifier), None)

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
async def test_bleak_runtime_connect_queries_battery_for_ems_v2_device() -> None:
    created_clients: list[FakeBleakClient] = []

    async def fake_discover(*, timeout: float, return_adv: bool):
        return {
            "AA:BB:CC:DD:EE:01": (
                SimpleNamespace(address="AA:BB:CC:DD:EE:01", name="YYC-DJ-V2-001", rssi=-41),
                SimpleNamespace(local_name="YYC-DJ-V2-001", service_uuids=[EMS_SERVICE_UUID]),
            ),
        }

    def client_factory(*args, **kwargs):
        client = FakeBleakClient(*args, **kwargs)
        created_clients.append(client)
        return client

    runtime = BleakBluetoothRuntime(
        scan_timeout_seconds=5,
        scanner_discover=fake_discover,
        client_factory=client_factory,
    )

    await runtime.scan()
    await runtime.connect("AA:BB:CC:DD:EE:01")

    client = created_clients[-1]
    assert "0000ff32-0000-1000-8000-00805f9b34fb" in client.notify_callbacks
    assert client.writes[0][0] == EMS_WRITE_CHAR_UUID
    assert client.writes[0][1] == bytes([0x35, 0x71, 0x04, 0xAA])


@pytest.mark.anyio
async def test_bleak_runtime_connect_queries_battery_for_ems_v1_device() -> None:
    created_clients: list[FakeBleakClient] = []

    async def fake_discover(*, timeout: float, return_adv: bool):
        return {
            "AA:BB:CC:DD:EE:02": (
                SimpleNamespace(address="AA:BB:CC:DD:EE:02", name="YYC-DJ-001", rssi=-53),
                SimpleNamespace(local_name="YYC-DJ-001", service_uuids=[EMS_SERVICE_UUID]),
            ),
        }

    def client_factory(*args, **kwargs):
        client = FakeBleakClient(*args, **kwargs)
        created_clients.append(client)
        return client

    runtime = BleakBluetoothRuntime(
        scan_timeout_seconds=5,
        scanner_discover=fake_discover,
        client_factory=client_factory,
    )

    await runtime.scan()
    await runtime.connect("AA:BB:CC:DD:EE:02")

    client = created_clients[-1]
    assert "0000ff32-0000-1000-8000-00805f9b34fb" in client.notify_callbacks
    assert client.writes[0][0] == EMS_WRITE_CHAR_UUID
    assert client.writes[0][1] == bytes([0x35, 0x71, 0x04, 0xAA])


@pytest.mark.anyio
async def test_bleak_runtime_updates_battery_level_from_notify_packet() -> None:
    created_clients: list[FakeBleakClient] = []

    async def fake_discover(*, timeout: float, return_adv: bool):
        return {
            "AA:BB:CC:DD:EE:01": (
                SimpleNamespace(address="AA:BB:CC:DD:EE:01", name="YYC-DJ-V2-001", rssi=-41),
                SimpleNamespace(local_name="YYC-DJ-V2-001", service_uuids=[EMS_SERVICE_UUID]),
            ),
        }

    def client_factory(*args, **kwargs):
        client = FakeBleakClient(*args, **kwargs)
        created_clients.append(client)
        return client

    runtime = BleakBluetoothRuntime(
        scan_timeout_seconds=5,
        scanner_discover=fake_discover,
        client_factory=client_factory,
    )

    await runtime.scan()
    await runtime.connect("AA:BB:CC:DD:EE:01")
    notify_callback = created_clients[-1].notify_callbacks["0000ff32-0000-1000-8000-00805f9b34fb"]
    await notify_callback("0000ff32-0000-1000-8000-00805f9b34fb", bytearray([0x35, 0x71, 0x04, 88, 0x00]))

    status = runtime.get_status()
    overlay = runtime.get_overlay_payload()

    assert status.battery_level == 88
    assert overlay["battery_level"] == 88


@pytest.mark.anyio
async def test_bleak_runtime_updates_battery_level_from_notify_packet_for_ems_v1() -> None:
    created_clients: list[FakeBleakClient] = []

    async def fake_discover(*, timeout: float, return_adv: bool):
        return {
            "AA:BB:CC:DD:EE:02": (
                SimpleNamespace(address="AA:BB:CC:DD:EE:02", name="YYC-DJ-001", rssi=-53),
                SimpleNamespace(local_name="YYC-DJ-001", service_uuids=[EMS_SERVICE_UUID]),
            ),
        }

    def client_factory(*args, **kwargs):
        client = FakeBleakClient(*args, **kwargs)
        created_clients.append(client)
        return client

    runtime = BleakBluetoothRuntime(
        scan_timeout_seconds=5,
        scanner_discover=fake_discover,
        client_factory=client_factory,
    )

    await runtime.scan()
    await runtime.connect("AA:BB:CC:DD:EE:02")
    notify_callback = created_clients[-1].notify_callbacks["0000ff32-0000-1000-8000-00805f9b34fb"]
    await notify_callback("0000ff32-0000-1000-8000-00805f9b34fb", bytearray([0x35, 0x71, 0x04, 76, 0x00]))

    status = runtime.get_status()
    overlay = runtime.get_overlay_payload()

    assert status.battery_level == 76
    assert overlay["battery_level"] == 76


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
        execution_mode="fixed",
        steps=[
            EmsWaveformStep(duration_ms=180, channel_a=48, channel_b=24, channel_a_mode=6, channel_b_mode=6),
            EmsWaveformStep(duration_ms=120, channel_a=0, channel_b=0),
        ],
    )

    await runtime.scan()
    await runtime.connect("AA:BB:CC:DD:EE:01")
    await runtime.play_waveform(waveform)

    client = runtime._client
    assert client is not None
    assert [item[0] for item in client.writes[-3:]] == [
        EMS_WRITE_CHAR_UUID,
        EMS_WRITE_CHAR_UUID,
        EMS_WRITE_CHAR_UUID,
    ]
    assert len(client.writes[-3][1]) == 10
    assert client.writes[-3][1][5] == 0x06
    assert client.writes[-3][1][8] == 0x06
    assert sleep_calls == [0.18, 0.12]


@pytest.mark.anyio
async def test_bleak_runtime_connect_respects_connect_timeout() -> None:
    class SlowBleakClient(FakeBleakClient):
        async def connect(self) -> None:
            await asyncio.sleep(0.05)
            self.connected = True

    async def fake_discover(*, timeout: float, return_adv: bool):
        return {
            "AA:BB:CC:DD:EE:01": (
                SimpleNamespace(address="AA:BB:CC:DD:EE:01", name="YYC-DJ-V2-001", rssi=-41),
                SimpleNamespace(local_name="YYC-DJ-V2-001", service_uuids=[EMS_SERVICE_UUID]),
            ),
        }

    runtime = BleakBluetoothRuntime(
        scan_timeout_seconds=5,
        connect_timeout_seconds=0.01,
        scanner_discover=fake_discover,
        client_factory=SlowBleakClient,
    )

    await runtime.scan()

    with pytest.raises(TimeoutError):
        await runtime.connect("AA:BB:CC:DD:EE:01")


@pytest.mark.anyio
async def test_bleak_runtime_marks_disconnect_reason_when_device_drops() -> None:
    created_clients: list[FakeBleakClient] = []

    async def fake_discover(*, timeout: float, return_adv: bool):
        return {
            "AA:BB:CC:DD:EE:01": (
                SimpleNamespace(address="AA:BB:CC:DD:EE:01", name="YYC-DJ-V2-001", rssi=-41),
                SimpleNamespace(local_name="YYC-DJ-V2-001", service_uuids=[EMS_SERVICE_UUID]),
            ),
        }

    def client_factory(*args, **kwargs):
        client = FakeBleakClient(*args, **kwargs)
        created_clients.append(client)
        return client

    runtime = BleakBluetoothRuntime(
        scan_timeout_seconds=5,
        scanner_discover=fake_discover,
        client_factory=client_factory,
    )

    await runtime.scan()
    await runtime.connect("AA:BB:CC:DD:EE:01")
    created_clients[-1].connected = False
    created_clients[-1].disconnected_callback(created_clients[-1])

    status = runtime.get_status()

    assert status.connected is False
    assert "断开" in status.message


@pytest.mark.anyio
async def test_bleak_runtime_auto_reconnects_after_unexpected_disconnect() -> None:
    created_clients: list[FakeBleakClient] = []

    async def fake_discover(*, timeout: float, return_adv: bool):
        return {
            "AA:BB:CC:DD:EE:01": (
                SimpleNamespace(address="AA:BB:CC:DD:EE:01", name="YYC-DJ-V2-001", rssi=-41),
                SimpleNamespace(local_name="YYC-DJ-V2-001", service_uuids=[EMS_SERVICE_UUID]),
            ),
        }

    async def fake_sleep(_seconds: float) -> None:
        return None

    def client_factory(*args, **kwargs):
        client = FakeBleakClient(*args, **kwargs)
        created_clients.append(client)
        return client

    runtime = BleakBluetoothRuntime(
        scan_timeout_seconds=5,
        scanner_discover=fake_discover,
        client_factory=client_factory,
        sleep_func=fake_sleep,
        auto_reconnect=True,
    )

    await runtime.scan()
    await runtime.connect("AA:BB:CC:DD:EE:01")
    created_clients[-1].connected = False
    created_clients[-1].disconnected_callback(created_clients[-1])
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    status = runtime.get_status()

    assert len(created_clients) >= 2
    assert status.connected is True
    assert "重连" in status.message
