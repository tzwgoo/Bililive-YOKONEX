from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from collections.abc import Callable
from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any

from app.bluetooth.models import BluetoothConnectionStatus
from app.bluetooth.models import BluetoothDevice
from app.bluetooth.models import EmsWaveform
from app.bluetooth.models import EmsWaveformStep

try:
    from bleak import BleakClient
    from bleak import BleakScanner
except ImportError:  # pragma: no cover - exercised through runtime fallback
    BleakClient = None
    BleakScanner = None


EMS_SERVICE_UUID = "0000ff30-0000-1000-8000-00805f9b34fb"
EMS_WRITE_CHAR_UUID = "0000ff31-0000-1000-8000-00805f9b34fb"


class BleakBluetoothRuntime:
    backend_name = "bleak"

    def __init__(
        self,
        *,
        scan_timeout_seconds: int,
        scanner_discover: Callable[..., Awaitable[Any]] | None = None,
        client_factory: Callable[..., Any] | None = None,
        sleep_func: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        if scanner_discover is None:
            if BleakScanner is None:
                raise RuntimeError("未安装 bleak，无法启用真实蓝牙运行时")
            scanner_discover = BleakScanner.discover
        if client_factory is None:
            if BleakClient is None:
                raise RuntimeError("未安装 bleak，无法启用真实蓝牙运行时")
            client_factory = BleakClient
        self._scan_timeout_seconds = scan_timeout_seconds
        self._scanner_discover = scanner_discover
        self._client_factory = client_factory
        self._sleep = sleep_func or asyncio.sleep
        self._devices: list[BluetoothDevice] = []
        self._ble_devices: dict[str, Any] = {}
        self._client: Any | None = None
        self._connected_device_id = ""

    async def scan(self) -> list[BluetoothDevice]:
        discovered = await self._scanner_discover(
            timeout=self._scan_timeout_seconds,
            return_adv=True,
        )
        devices: list[BluetoothDevice] = []
        ble_devices: dict[str, Any] = {}
        if isinstance(discovered, dict):
            values = discovered.values()
        else:
            values = ((item, SimpleNamespace(service_uuids=[])) for item in discovered)
        for ble_device, advertisement in values:
            mapped = classify_ems_device(ble_device=ble_device, advertisement=advertisement)
            if mapped is None:
                continue
            devices.append(mapped)
            ble_devices[mapped.device_id] = ble_device
        self._devices = devices
        self._ble_devices = ble_devices
        self._sync_connected_flags()
        return list(self._devices)

    async def connect(self, device_id: str) -> BluetoothConnectionStatus:
        ble_device = self._ble_devices.get(device_id)
        device = next((item for item in self._devices if item.device_id == device_id), None)
        if ble_device is None or device is None:
            raise ValueError("未找到指定蓝牙设备")
        if self._client is not None and getattr(self._client, "is_connected", False):
            await self.disconnect()
        client = self._client_factory(
            ble_device,
            disconnected_callback=self._handle_disconnect,
        )
        await client.connect()
        self._client = client
        self._connected_device_id = device_id if getattr(client, "is_connected", False) else ""
        self._sync_connected_flags()
        if not self._connected_device_id:
            raise RuntimeError("蓝牙设备连接失败")
        return BluetoothConnectionStatus(
            connected=True,
            device=device,
            message=f"已连接 {device.name}",
        )

    async def disconnect(self) -> BluetoothConnectionStatus:
        client = self._client
        self._client = None
        self._connected_device_id = ""
        if client is not None and getattr(client, "is_connected", False):
            await client.disconnect()
        self._sync_connected_flags()
        return BluetoothConnectionStatus(
            connected=False,
            device=None,
            message="已断开蓝牙设备",
        )

    def get_status(self) -> BluetoothConnectionStatus:
        device = next((item for item in self._devices if item.connected), None)
        return BluetoothConnectionStatus(
            connected=device is not None,
            device=device,
            message=f"已连接 {device.name}" if device is not None else "未连接",
        )

    def get_devices(self) -> list[BluetoothDevice]:
        return list(self._devices)

    async def play_waveform(self, waveform: EmsWaveform) -> None:
        if self._client is None or not getattr(self._client, "is_connected", False):
            raise RuntimeError("当前没有已连接的蓝牙设备")
        device = next((item for item in self._devices if item.connected), None)
        if device is None:
            raise RuntimeError("未找到当前连接设备")
        packets = create_waveform_packets(waveform=waveform, protocol=device.protocol)
        try:
            for packet, duration_seconds in packets:
                await self._client.write_gatt_char(EMS_WRITE_CHAR_UUID, packet, response=False)
                await self._sleep(duration_seconds)
        finally:
            stop_packet = create_stop_packet(protocol=device.protocol)
            await self._client.write_gatt_char(EMS_WRITE_CHAR_UUID, stop_packet, response=False)

    def _handle_disconnect(self, _client: Any) -> None:
        self._connected_device_id = ""
        self._client = None
        self._sync_connected_flags()

    def _sync_connected_flags(self) -> None:
        for item in self._devices:
            item.connected = item.device_id == self._connected_device_id


def classify_ems_device(*, ble_device: Any, advertisement: Any) -> BluetoothDevice | None:
    service_uuids = _normalize_service_uuids(getattr(advertisement, "service_uuids", []))
    name = (
        getattr(advertisement, "local_name", None)
        or getattr(ble_device, "name", None)
        or getattr(ble_device, "address", "")
    )
    name_upper = str(name).upper()
    if EMS_SERVICE_UUID not in service_uuids and not name_upper.startswith("YYC-DJ"):
        return None
    protocol = "ems_v2"
    if name_upper.startswith("YYC-DJ-V2"):
        protocol = "ems_v2"
    elif name_upper.startswith("YYC-DJ"):
        protocol = "ems_v1"
    return BluetoothDevice(
        device_id=str(getattr(ble_device, "address", "")),
        name=str(name),
        device_type="ems",
        protocol=protocol,
        rssi=int(getattr(ble_device, "rssi", getattr(advertisement, "rssi", -60)) or -60),
        connected=False,
    )


def create_waveform_packets(*, waveform: EmsWaveform, protocol: str) -> list[tuple[bytes, float]]:
    packets: list[tuple[bytes, float]] = []
    for step in waveform.steps:
        if protocol == "ems_v1":
            packet = _create_v1_packet(step)
        else:
            packet = _create_v2_fixed_packet(step)
        packets.append((packet, max(step.duration_ms, 0) / 1000))
    return packets


def create_stop_packet(*, protocol: str) -> bytes:
    if protocol == "ems_v1":
        return _create_v1_stop_packet()
    return _create_v2_fixed_packet(
        EmsWaveformStep(duration_ms=0, channel_a=0, channel_b=0),
    )


def _create_v1_packet(step: EmsWaveformStep) -> bytes:
    channel = _resolve_v1_channel(step)
    enabled = 0x01 if channel != 0x00 else 0x00
    strength = step.channel_b if channel == 0x02 or step.channel_b > step.channel_a else step.channel_a
    bytes_list = [
        0x35,
        0x11,
        channel,
        enabled,
        _high(strength),
        _low(strength),
        0x01,
        0x00,
        0x00,
    ]
    bytes_list.append(_compute_checksum(bytes_list))
    return bytes(bytes_list)


def _create_v2_fixed_packet(step: EmsWaveformStep) -> bytes:
    bytes_list = [
        0x35,
        0x11,
        0x01,
        _high(step.channel_a),
        _low(step.channel_a),
        0x01,
        _high(step.channel_b),
        _low(step.channel_b),
        0x01,
    ]
    bytes_list.append(_compute_checksum(bytes_list))
    return bytes(bytes_list)


def _create_v1_stop_packet() -> bytes:
    bytes_list = [
        0x35,
        0x11,
        0x03,
        0x00,
        0x00,
        0x01,
        0x01,
        0x00,
        0x00,
    ]
    bytes_list.append(_compute_checksum(bytes_list))
    return bytes(bytes_list)


def _resolve_v1_channel(step: EmsWaveformStep) -> int:
    a_enabled = step.channel_a > 0
    b_enabled = step.channel_b > 0
    if a_enabled and b_enabled:
        return 0x03
    if a_enabled:
        return 0x01
    if b_enabled:
        return 0x02
    return 0x00


def _normalize_service_uuids(service_uuids: Iterable[str] | None) -> set[str]:
    if service_uuids is None:
        return set()
    return {str(item).lower() for item in service_uuids if item}


def _high(value: int) -> int:
    clipped = max(0, min(int(value), 0xFFFF))
    return (clipped >> 8) & 0xFF


def _low(value: int) -> int:
    clipped = max(0, min(int(value), 0xFFFF))
    return clipped & 0xFF


def _compute_checksum(values: Iterable[int]) -> int:
    total = 0
    for item in values:
        total = (total + item) & 0xFF
    return total
