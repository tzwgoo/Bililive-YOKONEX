from __future__ import annotations

from app.bluetooth.models import BluetoothConnectionStatus
from app.bluetooth.models import BluetoothDevice
from app.bluetooth.models import EmsWaveform


class MemoryBluetoothRuntime:
    backend_name = "memory"

    def __init__(self) -> None:
        self._devices: list[BluetoothDevice] = []
        self._connected_device_id = ""

    async def scan(self) -> list[BluetoothDevice]:
        self._devices = [
            BluetoothDevice(
                device_id="ems-demo-001",
                name="YYC-DJ-DEMO",
                device_type="ems",
                protocol="ems_v1",
                rssi=-42,
                connected=self._connected_device_id == "ems-demo-001",
            ),
            BluetoothDevice(
                device_id="ems-demo-002",
                name="YYC-DJ-V2-DEMO",
                device_type="ems",
                protocol="ems_v2",
                rssi=-51,
                connected=self._connected_device_id == "ems-demo-002",
            ),
        ]
        return list(self._devices)

    async def connect(self, device_id: str) -> BluetoothConnectionStatus:
        device = next((item for item in self._devices if item.device_id == device_id), None)
        if device is None:
            raise ValueError("未找到指定蓝牙设备")
        self._connected_device_id = device_id
        for item in self._devices:
            item.connected = item.device_id == device_id
        return BluetoothConnectionStatus(
            connected=True,
            device=device,
            message=f"已连接 {device.name}",
        )

    async def disconnect(self) -> BluetoothConnectionStatus:
        self._connected_device_id = ""
        for item in self._devices:
            item.connected = False
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
        return None
