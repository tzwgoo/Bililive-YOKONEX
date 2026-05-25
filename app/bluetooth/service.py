from __future__ import annotations

import logging
from pathlib import Path

from app.bluetooth.models import BluetoothConnectionStatus
from app.bluetooth.models import BluetoothConfigPayload
from app.bluetooth.models import BluetoothDevice
from app.bluetooth.models import payload_to_dict
from app.bluetooth.runtime.base import BluetoothRuntime
from app.bluetooth.runtime.memory_runtime import MemoryBluetoothRuntime
from app.bluetooth.storage import BluetoothSettingsStore


logger = logging.getLogger(__name__)


class BluetoothService:
    def __init__(
        self,
        *,
        store: BluetoothSettingsStore,
        runtime: BluetoothRuntime,
        payload: BluetoothConfigPayload | None = None,
    ) -> None:
        self.store = store
        self.runtime = runtime
        self.payload = payload or self.store.load()

    @classmethod
    def create_default(cls, *, config_path: Path) -> "BluetoothService":
        store = BluetoothSettingsStore(config_path)
        payload = store.load()
        try:
            runtime = create_real_bluetooth_runtime(
                scan_timeout_seconds=payload.bluetooth_settings.scan_timeout_seconds,
            )
        except Exception as exc:  # pragma: no cover - verified through factory fallback test
            logger.warning("真实蓝牙运行时初始化失败，已降级到内存运行时: %s", exc)
            runtime = MemoryBluetoothRuntime()
        return cls(
            store=store,
            runtime=runtime,
            payload=payload,
        )

    async def scan(self) -> list[BluetoothDevice]:
        devices = await self.runtime.scan()
        return devices

    async def connect(self, device_id: str) -> BluetoothConnectionStatus:
        status = await self.runtime.connect(device_id)
        if status.device is not None:
            self.payload.bluetooth_settings.last_connected_device_id = status.device.device_id
            self.payload.bluetooth_settings.last_connected_device_name = status.device.name
            self.payload.bluetooth_settings.default_target_device_id = status.device.device_id
            self.store.save(self.payload)
        return status

    async def disconnect(self) -> BluetoothConnectionStatus:
        return await self.runtime.disconnect()

    async def trigger_waveform(self, *, event_type: str, waveform_id: str) -> dict:
        waveform = next((item for item in self.payload.ems_waveforms if item.id == waveform_id), None)
        if waveform is None:
            return {
                "matched": True,
                "event_type": event_type,
                "waveform_id": waveform_id,
                "success": False,
                "message": "目标波形不存在",
            }
        try:
            await self.runtime.play_waveform(waveform)
        except Exception as exc:
            return {
                "matched": True,
                "event_type": event_type,
                "waveform_id": waveform_id,
                "success": False,
                "message": f"波形执行失败: {exc}",
            }
        return {
            "matched": True,
            "event_type": event_type,
            "waveform_id": waveform_id,
            "success": True,
            "message": f"{event_type} 已触发波形 {waveform.name}",
        }

    def get_status_payload(self) -> dict:
        status = self.runtime.get_status()
        return {
            "runtime_backend": getattr(self.runtime, "backend_name", "unknown"),
            "enabled": self.payload.bluetooth_settings.enabled,
            "connected": status.connected,
            "message": status.message,
            "device": None if status.device is None else {
                "device_id": status.device.device_id,
                "name": status.device.name,
                "device_type": status.device.device_type,
                "protocol": status.device.protocol,
                "rssi": status.device.rssi,
            },
            "devices": [
                {
                    "device_id": item.device_id,
                    "name": item.name,
                    "device_type": item.device_type,
                    "protocol": item.protocol,
                    "rssi": item.rssi,
                    "connected": item.connected,
                }
                for item in self.runtime.get_devices()
            ],
            "waveforms": payload_to_dict(self.payload)["ems_waveforms"],
            "rules": payload_to_dict(self.payload)["bluetooth_event_rules"],
        }


def create_real_bluetooth_runtime(*, scan_timeout_seconds: int) -> BluetoothRuntime:
    from app.bluetooth.runtime.bleak_runtime import BleakBluetoothRuntime

    return BleakBluetoothRuntime(scan_timeout_seconds=scan_timeout_seconds)
