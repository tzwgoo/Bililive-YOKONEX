from __future__ import annotations

from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from app.main import create_app
import app.api.routes as api_routes
from app.services.event_hub import EventHub
from app.services.danmaku_settings import FIXED_DANMAKU_COMMAND_ID
from app.services.danmaku_settings import FIXED_DANMAKU_COMMAND_IDS
from app.services.danmaku_settings import FIXED_INTERACT_COMMAND_ID
from app.services.danmaku_settings import FIXED_LIKE_COMMAND_ID


class FakeCommandSessionService:
    def __init__(self) -> None:
        self.status = {
            "status": "idle",
            "message": "",
            "ws_url": "",
            "uid": "",
            "user_id": "",
            "last_login_at": 0,
            "last_command_id": "",
            "last_command_message": "",
            "can_connect": True,
            "can_disconnect": False,
        }
        self.connect_called_with: dict | None = None
        self.disconnect_called = False

    def get_status_payload(self) -> dict:
        return self.status

    async def connect(self, *, ws_url: str, uid: str, token: str) -> dict:
        self.connect_called_with = {
            "ws_url": ws_url,
            "uid": uid,
            "token": token,
        }
        self.status = {
            **self.status,
            "status": "connected",
            "ws_url": ws_url,
            "uid": uid,
            "user_id": "123456",
            "can_connect": False,
            "can_disconnect": True,
        }
        return self.status

    async def disconnect(self) -> None:
        self.disconnect_called = True
        self.status = {
            **self.status,
            "status": "idle",
            "user_id": "",
            "can_connect": True,
            "can_disconnect": False,
        }


class FakeSessionManager:
    def __init__(self) -> None:
        self.status = {
            "status": "idle",
            "message": "",
            "mode": "open_live",
            "mode_label": "官方 open-live",
            "output_mode": "im",
            "trigger_mode": "by_quantity",
            "like_multiple": 100,
            "danmaku_enabled": False,
            "danmaku_keywords": "",
            "danmaku_command_id": FIXED_DANMAKU_COMMAND_ID,
            "danmaku_command_ids": FIXED_DANMAKU_COMMAND_IDS,
            "danmaku_cooldown_seconds": 0,
            "danmaku_user_limit_window_seconds": 0,
            "danmaku_user_limit_max_triggers": 0,
            "danmaku_min_guard_level": 0,
            "game_id": "",
            "room_id": 0,
            "anchor_name": "",
            "last_event_at": 0,
            "last_heartbeat_at": 0,
            "last_command_id": "",
            "last_command_message": "",
            "command_dispatch_enabled": False,
            "config_loaded": True,
            "can_start": True,
            "can_stop": False,
        }
        self.start_called_with: dict | None = None
        self.stop_called = False

    def get_status_payload(self) -> dict:
        return self.status

    async def start(
        self,
        *,
        mode: str,
        value: str,
        trigger_mode: str,
        output_mode: str = "",
        like_multiple: int = 100,
        danmaku_enabled: bool = False,
        danmaku_keywords: str = "",
        danmaku_cooldown_seconds: int = 0,
        danmaku_user_limit_window_seconds: int = 0,
        danmaku_user_limit_max_triggers: int = 0,
        danmaku_min_guard_level: int = 0,
    ) -> None:
        self.start_called_with = {
            "mode": mode,
            "value": value,
            "trigger_mode": trigger_mode,
            "output_mode": output_mode,
            "like_multiple": like_multiple,
            "danmaku_enabled": danmaku_enabled,
            "danmaku_keywords": danmaku_keywords,
            "danmaku_cooldown_seconds": danmaku_cooldown_seconds,
            "danmaku_user_limit_window_seconds": danmaku_user_limit_window_seconds,
            "danmaku_user_limit_max_triggers": danmaku_user_limit_max_triggers,
            "danmaku_min_guard_level": danmaku_min_guard_level,
        }
        self.status = {
            **self.status,
            "status": "running",
            "mode": mode,
            "trigger_mode": trigger_mode,
            "like_multiple": like_multiple,
            "danmaku_enabled": danmaku_enabled,
            "danmaku_keywords": danmaku_keywords,
            "danmaku_command_id": FIXED_DANMAKU_COMMAND_ID,
            "danmaku_command_ids": FIXED_DANMAKU_COMMAND_IDS,
            "danmaku_cooldown_seconds": danmaku_cooldown_seconds,
            "danmaku_user_limit_window_seconds": danmaku_user_limit_window_seconds,
            "danmaku_user_limit_max_triggers": danmaku_user_limit_max_triggers,
            "danmaku_min_guard_level": danmaku_min_guard_level,
            "can_start": False,
            "can_stop": True,
        }

    async def stop(self) -> None:
        self.stop_called = True
        self.status = {
            **self.status,
            "status": "idle",
            "can_start": True,
            "can_stop": False,
        }


class FakeCommandRuleService:
    def __init__(self) -> None:
        self.payload = {
            "rules": [
                {
                    "id": "gift-tier-1",
                    "enabled": True,
                    "event_type": "gift",
                    "min_price": 0,
                    "max_price": 99,
                    "command_slot": "command_one",
                }
            ],
            "like_rules": [],
            "like_command_id": FIXED_LIKE_COMMAND_ID,
            "interact_command_id": FIXED_INTERACT_COMMAND_ID,
            "danmaku_slot_rules": [],
            "danmaku_command_ids": {
                "danmaku": "danmaku_trigger",
                "danmaku_captain": "danmaku_captain_trigger",
                "danmaku_commander": "danmaku_commander_trigger",
                "danmaku_governor": "danmaku_governor_trigger",
            },
            "command_slots": ["command_one", "command_two"],
        }
        self.saved_payload: dict | None = None

    def get_studio_payload(self) -> dict:
        return self.payload

    def save_rules(self, payload: dict) -> dict:
        self.saved_payload = payload
        return {
            "success": True,
            **self.payload,
        }


def test_status_endpoint_returns_idle_state() -> None:
    app = create_app()
    app.state.session_service = FakeSessionManager()
    client = TestClient(app)

    response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json()["status"] == "idle"
    assert response.json()["mode"] == "open_live"
    assert response.json()["output_mode"] == "im"
    assert response.json()["trigger_mode"] == "by_quantity"
    assert response.json()["danmaku_command_id"] == FIXED_DANMAKU_COMMAND_ID
    assert response.json()["danmaku_command_ids"] == FIXED_DANMAKU_COMMAND_IDS
    assert response.json()["danmaku_user_limit_window_seconds"] == 0
    assert response.json()["danmaku_user_limit_max_triggers"] == 0
    assert response.json()["danmaku_min_guard_level"] == 0


def test_command_status_endpoint_returns_idle_state() -> None:
    client = TestClient(create_app())

    response = client.get("/api/command/status")

    assert response.status_code == 200
    assert response.json()["status"] == "idle"


def test_index_page_no_longer_renders_fixed_danmaku_slot() -> None:
    client = TestClient(create_app())

    response = client.get("/")

    assert response.status_code == 200
    assert "固定指令槽位" not in response.text
    assert "danmaku-command-id-label" not in response.text


def test_index_page_prefers_spa_response_when_available(monkeypatch) -> None:
    client = TestClient(create_app())

    monkeypatch.setattr(
        api_routes,
        "_spa_index_response",
        lambda: HTMLResponse("<html><body>spa-index</body></html>"),
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "spa-index" in response.text


def test_events_page_prefers_spa_response_when_available(monkeypatch) -> None:
    client = TestClient(create_app())

    monkeypatch.setattr(
        api_routes,
        "_spa_index_response",
        lambda: HTMLResponse("<html><body>spa-index-events</body></html>"),
    )

    response = client.get("/events")

    assert response.status_code == 200
    assert "spa-index-events" in response.text


def test_waveforms_page_prefers_spa_response_when_available(monkeypatch) -> None:
    client = TestClient(create_app())

    monkeypatch.setattr(
        api_routes,
        "_spa_index_response",
        lambda: HTMLResponse("<html><body>spa-index-waveforms</body></html>"),
    )

    response = client.get("/waveforms")

    assert response.status_code == 200
    assert "spa-index-waveforms" in response.text


def test_command_connect_endpoint_uses_frontend_payload() -> None:
    app = create_app()
    fake_command_session = FakeCommandSessionService()
    app.state.command_session = fake_command_session
    client = TestClient(app)

    response = client.post(
        "/api/command/connect",
        json={
            "ws_url": "ws://127.0.0.1:43001/",
            "uid": "game_123456",
            "token": "token",
        },
    )

    assert response.status_code == 200
    assert fake_command_session.connect_called_with == {
        "ws_url": "ws://127.0.0.1:43001/",
        "uid": "game_123456",
        "token": "token",
    }


def test_session_start_endpoint_uses_mode_and_value_payload() -> None:
    app = create_app()
    fake_session_manager = FakeSessionManager()
    app.state.session_service = fake_session_manager
    client = TestClient(app)

    response = client.post(
        "/api/session/start",
        json={
            "mode": "third_party",
            "value": "123456",
            "trigger_mode": "single",
            "like_multiple": 200,
            "danmaku_enabled": True,
            "danmaku_keywords": "开火,冲冲冲",
            "danmaku_cooldown_seconds": 15,
            "danmaku_user_limit_window_seconds": 60,
            "danmaku_user_limit_max_triggers": 2,
            "danmaku_min_guard_level": 2,
        },
    )

    assert response.status_code == 200
    assert fake_session_manager.start_called_with == {
        "mode": "third_party",
        "value": "123456",
        "trigger_mode": "single",
        "output_mode": "",
        "like_multiple": 200,
        "danmaku_enabled": True,
        "danmaku_keywords": "开火,冲冲冲",
        "danmaku_cooldown_seconds": 15,
        "danmaku_user_limit_window_seconds": 60,
        "danmaku_user_limit_max_triggers": 2,
        "danmaku_min_guard_level": 2,
    }


def test_command_disconnect_endpoint_calls_command_session() -> None:
    app = create_app()
    fake_command_session = FakeCommandSessionService()
    app.state.command_session = fake_command_session
    client = TestClient(app)

    response = client.post("/api/command/disconnect")

    assert response.status_code == 200
    assert fake_command_session.disconnect_called is True


def test_command_studio_endpoint_returns_rule_payload() -> None:
    app = create_app()
    fake_command_rule_service = FakeCommandRuleService()
    app.state.command_rule_service = fake_command_rule_service
    client = TestClient(app)

    response = client.get("/api/command/studio")

    assert response.status_code == 200
    assert response.json()["rules"][0]["event_type"] == "gift"
    assert response.json()["like_rules"] == []
    assert response.json()["like_command_id"] == FIXED_LIKE_COMMAND_ID
    assert response.json()["interact_command_id"] == FIXED_INTERACT_COMMAND_ID
    assert response.json()["danmaku_slot_rules"] == []
    assert response.json()["danmaku_command_ids"]["danmaku_governor"] == "danmaku_governor_trigger"


def test_command_studio_save_endpoint_uses_frontend_payload() -> None:
    app = create_app()
    fake_command_rule_service = FakeCommandRuleService()
    app.state.command_rule_service = fake_command_rule_service
    client = TestClient(app)

    response = client.post(
        "/api/command/studio",
        json={
            "rules": [
                {
                    "id": "gift-tier-1",
                    "enabled": True,
                    "event_type": "super_chat",
                    "min_price": 0,
                    "max_price": 199,
                    "command_slot": "command_five",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert fake_command_rule_service.saved_payload == {
        "rules": [
            {
                "id": "gift-tier-1",
                "enabled": True,
                "event_type": "super_chat",
                "min_price": 0,
                "max_price": 199,
                "command_slot": "command_five",
            }
        ],
        "like_rules": [],
        "danmaku_slot_rules": [],
    }


def test_control_stream_endpoint_returns_control_snapshot() -> None:
    app = create_app()
    event_hub = EventHub()
    event_hub.publish_control({"type": "bluetooth_trigger", "payload": {"waveform_id": "ems-preset-01"}})
    app.state.event_hub = event_hub
    client = TestClient(app)

    with client.stream("GET", "/api/control/stream?once=true") as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    assert '"type": "bluetooth_trigger"' in body
