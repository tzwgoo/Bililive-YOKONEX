from __future__ import annotations

from typing import Protocol

from app.bluetooth.models import BluetoothConnectionStatus
from app.bluetooth.models import BluetoothDevice


class BluetoothRuntime(Protocol):
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

