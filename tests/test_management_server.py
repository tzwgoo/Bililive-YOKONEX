from __future__ import annotations

from fastapi.testclient import TestClient

from management_server.config import ManagementSettings
from management_server.main import _validate_command_args, create_management_app
from management_server.store import ManagementStore


def create_test_client(tmp_path) -> TestClient:
    app = create_management_app(ManagementSettings(
        database_path=tmp_path / "management.db",
        admin_username="admin",
        admin_password="password-123",
        registration_token="register-123",
    ))
    return TestClient(app)


def test_admin_api_requires_login(tmp_path) -> None:
    client = create_test_client(tmp_path)

    response = client.get("/api/admin/clients")

    assert response.status_code == 401


def test_admin_login_sets_session_and_csrf_is_required(tmp_path) -> None:
    client = create_test_client(tmp_path)

    login = client.post("/api/admin/login", json={"username": "admin", "password": "password-123"})

    assert login.status_code == 200
    assert "bililive_management_session" in login.cookies
    assert client.get("/api/admin/clients").status_code == 200
    assert client.post("/api/admin/logout").status_code == 403
    csrf_token = client.get("/api/admin/me").json()["csrf_token"]
    assert client.post("/api/admin/logout", headers={"X-CSRF-Token": csrf_token}).status_code == 200


def test_device_can_enroll_and_report_capabilities(tmp_path) -> None:
    client = create_test_client(tmp_path)
    login = client.post("/api/admin/login", json={"username": "admin", "password": "password-123"})
    assert login.status_code == 200

    with client.websocket_connect("/device/ws") as websocket:
        websocket.send_json({
            "type": "device.enroll",
            "registration_token": "register-123",
            "client_name": "测试电脑",
            "platform": "Windows",
        })
        enrolled = websocket.receive_json()
        assert enrolled["type"] == "device.enrolled"
        websocket.send_json({
            "type": "device.capabilities",
            "command_ids": ["command_one"],
            "waveform_revision": "revision-1",
            "waveforms": [{
                "waveform_id": "wave-1",
                "name": "测试波形",
                "waveform_type": "ems",
                "device_family": "ems",
                "builtin": False,
                "editable": True,
                "version_hash": "hash-1",
            }],
        })
        websocket.send_json({
            "type": "device.heartbeat",
            "client_name": "测试电脑",
            "user_id": "123456",
            "command_connected": True,
            "devices": [{
                "device_id": "ems-1",
                "name": "EMS 设备",
                "device_type": "ems",
                "protocol": "ems_v1",
                "connected": True,
            }],
        })

        clients = client.get("/api/admin/clients").json()["clients"]
        assert clients[0]["online"] is True
        assert clients[0]["waveform_count"] == 1
        detail = client.get(f"/api/admin/clients/{enrolled['client_id']}").json()
        assert detail["user_id"] == "123456"
        assert detail["waveforms"][0]["waveform_id"] == "wave-1"
        assert detail["devices"][0]["connected"] is True


def test_server_validates_fixed_output_limits(tmp_path) -> None:
    store = ManagementStore(tmp_path / "management.db")
    store.initialize()
    client_id, _token = store.enroll_client(client_name="测试电脑", platform="Windows")
    store.update_heartbeat(client_id, {
        "client_name": "测试电脑",
        "devices": [{
            "device_id": "ems-1",
            "name": "EMS 设备",
            "device_type": "ems",
            "protocol": "ems_v1",
            "connected": True,
        }],
    })

    args = _validate_command_args(store, client_id, "output.fixed", {
        "device_id": "ems-1",
        "strength": 90,
        "duration_seconds": 8,
    })

    assert args == {"device_id": "ems-1", "strength": 90, "duration_seconds": 8}
