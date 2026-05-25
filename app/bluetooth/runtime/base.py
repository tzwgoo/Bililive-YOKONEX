from __future__ import annotations

from typing import Protocol

from app.bluetooth.models import BluetoothConnectionStatus
from app.bluetooth.models import BluetoothDevice
from app.bluetooth.models import EmsWaveform


class BluetoothRuntime(Protocol):
    backend_name: str

    async def scan(self) -> list[BluetoothDevice]:
        ...

    async def connect(self, device_id: str) -> BluetoothConnectionStatus:
        ...

    async def disconnect(self) -> BluetoothConnectionStatus:
        ...

    def get_status(self) -> BluetoothConnectionStatus:
        ...

    def get_devices(self) -> list[BluetoothDevice]:
        ...

    def get_overlay_payload(self) -> dict:
        ...

    async def play_waveform(self, waveform: EmsWaveform) -> None:
        ...
