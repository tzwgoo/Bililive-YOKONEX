from __future__ import annotations

import time

from app.bluetooth.models import BluetoothConnectionStatus
from app.bluetooth.models import BluetoothDevice
from app.bluetooth.models import EmsWaveform


class MemoryBluetoothRuntime:
    backend_name = "memory"

    def __init__(self) -> None:
        self._devices: list[BluetoothDevice] = []
        self._connected_device_id = ""
        self._battery_level: int | None = None
        self._overlay_payload = {
            "connected": False,
            "device_name": "",
            "waveform_name": "",
            "battery_level": None,
            "channel_a": 0,
            "channel_b": 0,
            "step_index": 0,
            "step_count": 0,
            "updated_at": 0.0,
            "history": [],
            "revision": 0,
        }

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
        self._battery_level = 100 if device.protocol == "ems_v2" else None
        for item in self._devices:
            item.connected = item.device_id == device_id
        self._set_overlay_payload(
            connected=True,
            device_name=device.name,
            battery_level=self._battery_level,
        )
        return BluetoothConnectionStatus(
            connected=True,
            device=device,
            battery_level=self._battery_level,
            message=f"已连接 {device.name}",
        )

    async def disconnect(self) -> BluetoothConnectionStatus:
        self._connected_device_id = ""
        self._battery_level = None
        for item in self._devices:
            item.connected = False
        self._set_overlay_payload(
            connected=False,
            device_name="",
            waveform_name="",
            battery_level=None,
            channel_a=0,
            channel_b=0,
            step_index=0,
            step_count=0,
            history=[],
        )
        return BluetoothConnectionStatus(
            connected=False,
            device=None,
            battery_level=None,
            message="已断开蓝牙设备",
        )

    def get_status(self) -> BluetoothConnectionStatus:
        device = next((item for item in self._devices if item.connected), None)
        return BluetoothConnectionStatus(
            connected=device is not None,
            device=device,
            battery_level=self._battery_level if device is not None else None,
            message=f"已连接 {device.name}" if device is not None else "未连接",
        )

    def get_devices(self) -> list[BluetoothDevice]:
        return list(self._devices)

    def get_overlay_payload(self) -> dict:
        return {
            **self._overlay_payload,
            "history": list(self._overlay_payload["history"]),
        }

    async def play_waveform(self, waveform: EmsWaveform) -> None:
        if not waveform.steps:
            return None
        history = list(self._overlay_payload["history"])
        for index, step in enumerate(waveform.steps, start=1):
            history.append(
                {
                    "channel_a": step.channel_a,
                    "channel_b": step.channel_b,
                }
            )
            history = history[-90:]
            self._set_overlay_payload(
                connected=bool(self._connected_device_id),
                waveform_name=waveform.name,
                channel_a=step.channel_a,
                channel_b=step.channel_b,
                step_index=index,
                step_count=len(waveform.steps),
                history=history,
            )
        self._set_overlay_payload(
            connected=bool(self._connected_device_id),
            waveform_name="",
            channel_a=0,
            channel_b=0,
            step_index=0,
            step_count=0,
            history=[*history, {"channel_a": 0, "channel_b": 0}][-90:],
        )
        return None

    def _set_overlay_payload(self, **updates) -> None:
        self._overlay_payload = {
            **self._overlay_payload,
            **updates,
            "updated_at": time.time(),
            "revision": int(self._overlay_payload.get("revision", 0)) + 1,
        }
