from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import create_app


class FakeBluetoothService:
    def __init__(self) -> None:
        self.devices = [
            {
                "device_id": "ems-demo-001",
                "name": "YYC-DJ-DEMO",
                "device_type": "ems",
                "protocol": "ems_v1",
                "rssi": -42,
                "connected": False,
            }
        ]
        self.connected = False
        self.connect_called_with = ""
        self.scan_called = False
        self.disconnect_called = False

    def get_status_payload(self) -> dict:
        return {
            "enabled": False,
            "connected": self.connected,
            "message": "已连接" if self.connected else "未连接",
            "device": self.devices[0] if self.connected else None,
            "devices": self.devices,
            "waveforms": [],
            "rules": [],
        }

    async def scan(self) -> list:
        self.scan_called = True
        return self.devices

    async def connect(self, device_id: str):
        if device_id != self.devices[0]["device_id"]:
            raise ValueError("未找到指定蓝牙设备")
        self.connected = True
        self.connect_called_with = device_id
        return type("Status", (), {"connected": True, "device": type("Device", (), self.devices[0]), "message": "已连接"})()

    async def disconnect(self):
        self.connected = False
        self.disconnect_called = True
        return type("Status", (), {"connected": False, "device": None, "message": "已断开蓝牙设备"})()


def test_bluetooth_status_endpoint_returns_payload() -> None:
    app = create_app()
    fake_service = FakeBluetoothService()
    app.state.bluetooth_service = fake_service
    client = TestClient(app)

    response = client.get("/api/bluetooth/status")

    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert response.json()["devices"][0]["device_id"] == "ems-demo-001"


def test_bluetooth_scan_endpoint_returns_devices() -> None:
    app = create_app()
    fake_service = FakeBluetoothService()
    app.state.bluetooth_service = fake_service
    client = TestClient(app)

    response = client.post("/api/bluetooth/scan")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert fake_service.scan_called is True


def test_bluetooth_connect_endpoint_validates_device_id() -> None:
    app = create_app()
    fake_service = FakeBluetoothService()
    app.state.bluetooth_service = fake_service
    client = TestClient(app)

    response = client.post("/api/bluetooth/connect", json={"device_id": "missing-device"})

    assert response.status_code == 400
    assert response.json()["detail"] == "未找到指定蓝牙设备"


def test_bluetooth_disconnect_endpoint_returns_disconnected_status() -> None:
    app = create_app()
    fake_service = FakeBluetoothService()
    app.state.bluetooth_service = fake_service
    client = TestClient(app)

    response = client.post("/api/bluetooth/disconnect")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert fake_service.disconnect_called is True
