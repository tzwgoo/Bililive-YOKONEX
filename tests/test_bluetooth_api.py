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
        self.saved_rules: list[dict] = []
        self.overlay_payload = {
            "connected": False,
            "device_name": "YYC-DJ-DEMO",
            "waveform_name": "",
            "battery_level": None,
            "channel_a": 0,
            "channel_b": 0,
            "step_index": 0,
            "step_count": 0,
            "updated_at": 0,
            "history": [],
            "revision": 1,
        }

    def get_status_payload(self) -> dict:
        return {
            "enabled": False,
            "connected": self.connected,
            "message": "已连接" if self.connected else "未连接",
            "battery_level": 76 if self.connected else None,
            "device": self.devices[0] if self.connected else None,
            "devices": self.devices,
            "waveforms": [],
            "rules": [
                {
                    "id": "gift-tier-01",
                    "enabled": True,
                    "event_type": "gift",
                    "event_label": "礼物事件",
                    "rule_label": "礼物档位 01 · 0-99",
                    "waveform_id": "ems-preset-01",
                    "waveform_name": "EMS 预设 01 - 呼吸",
                }
            ],
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

    def get_studio_payload(self) -> dict:
        return {
            "waveforms": [
                {
                    "id": "ems-preset-01",
                    "name": "EMS 预设 01 - 呼吸",
                    "builtin": True,
                    "editable": False,
                    "execution_mode": "fixed",
                    "loop_count": 1,
                    "steps": [
                        {
                            "duration_ms": 120,
                            "channel_a": 40,
                            "channel_a_mode": 1,
                            "channel_b": 40,
                            "channel_b_mode": 1,
                        }
                    ],
                }
            ],
            "rule_groups": [
                {
                    "group_id": "gift",
                    "group_label": "礼物事件",
                    "rules": [
                        {
                            "id": "gift-tier-01",
                            "event_type": "gift",
                            "rule_label": "礼物档位 01 · 0-99",
                            "enabled": True,
                            "waveform_id": "ems-preset-01",
                            "waveform_name": "EMS 预设 01 - 呼吸",
                        }
                    ],
                }
            ],
        }

    def save_rules(self, rules: list[dict]) -> dict:
        self.saved_rules = rules
        return {"success": True, "updated_count": len(rules)}

    def get_overlay_payload(self) -> dict:
        return dict(self.overlay_payload)


def test_bluetooth_status_endpoint_returns_payload() -> None:
    app = create_app()
    fake_service = FakeBluetoothService()
    app.state.bluetooth_service = fake_service
    client = TestClient(app)

    response = client.get("/api/bluetooth/status")

    assert response.status_code == 200
    assert response.json()["connected"] is False
    assert response.json()["battery_level"] is None
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


def test_bluetooth_connect_endpoint_returns_runtime_errors() -> None:
    class FailingBluetoothService(FakeBluetoothService):
        async def connect(self, device_id: str):
            raise RuntimeError("蓝牙连接超时，请重试")

    app = create_app()
    app.state.bluetooth_service = FailingBluetoothService()
    client = TestClient(app)

    response = client.post("/api/bluetooth/connect", json={"device_id": "ems-demo-001"})

    assert response.status_code == 400
    assert response.json()["detail"] == "蓝牙连接超时，请重试"


def test_bluetooth_disconnect_endpoint_returns_disconnected_status() -> None:
    app = create_app()
    fake_service = FakeBluetoothService()
    app.state.bluetooth_service = fake_service
    client = TestClient(app)

    response = client.post("/api/bluetooth/disconnect")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert fake_service.disconnect_called is True


def test_bluetooth_studio_endpoint_returns_waveforms_and_rule_groups() -> None:
    app = create_app()
    fake_service = FakeBluetoothService()
    app.state.bluetooth_service = fake_service
    client = TestClient(app)

    response = client.get("/api/bluetooth/studio")

    assert response.status_code == 200
    assert response.json()["waveforms"][0]["id"] == "ems-preset-01"
    assert response.json()["rule_groups"][0]["group_id"] == "gift"


def test_bluetooth_overlay_page_is_available() -> None:
    client = TestClient(create_app())

    response = client.get("/bluetooth/overlay")

    assert response.status_code == 200
    assert "蓝牙实时叠加窗" in response.text
    assert "overlay-root" in response.text


def test_bluetooth_overlay_status_endpoint_returns_telemetry() -> None:
    app = create_app()
    fake_service = FakeBluetoothService()
    fake_service.overlay_payload = {
        **fake_service.overlay_payload,
        "connected": True,
        "waveform_name": "EMS 预设 06 - 心跳节奏",
        "battery_level": 63,
        "channel_a": 48,
        "channel_b": 45,
        "history": [{"channel_a": 48, "channel_b": 45}],
    }
    app.state.bluetooth_service = fake_service
    client = TestClient(app)

    response = client.get("/api/bluetooth/overlay/status")

    assert response.status_code == 200
    assert response.json()["connected"] is True
    assert response.json()["waveform_name"] == "EMS 预设 06 - 心跳节奏"
    assert response.json()["battery_level"] == 63
    assert response.json()["channel_a"] == 48
    assert response.json()["channel_b"] == 45


def test_bluetooth_overlay_stream_endpoint_uses_sse_content_type() -> None:
    app = create_app()
    app.state.bluetooth_service = FakeBluetoothService()
    client = TestClient(app)

    with client.stream("GET", "/api/bluetooth/overlay/stream?once=true") as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")


def test_bluetooth_rules_endpoint_saves_rule_selection() -> None:
    app = create_app()
    fake_service = FakeBluetoothService()
    app.state.bluetooth_service = fake_service
    client = TestClient(app)

    response = client.post(
        "/api/bluetooth/rules",
        json={
            "rules": [
                {
                    "id": "gift-tier-01",
                    "enabled": True,
                    "waveform_id": "ems-preset-06",
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert fake_service.saved_rules == [
        {
            "id": "gift-tier-01",
            "enabled": True,
            "waveform_id": "ems-preset-06",
        }
    ]
