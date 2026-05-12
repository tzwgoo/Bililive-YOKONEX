from __future__ import annotations

import pytest

from app.services.live_session_manager import LiveSessionManager


class FakeSession:
    def __init__(self, *, mode: str) -> None:
        self.mode = mode
        self.started_with: str | None = None
        self.stopped = False
        self.trigger_mode = "by_quantity"
        self.status_payload = {
            "status": "idle",
            "message": "",
            "room_id": 0,
            "anchor_name": "",
            "game_id": "",
            "trigger_mode": "by_quantity",
            "last_event_at": 0,
            "last_heartbeat_at": 0,
            "last_command_id": "",
            "last_command_message": "",
            "command_dispatch_enabled": False,
            "config_loaded": True,
            "can_start": True,
            "can_stop": False,
        }

    async def start(self, *, value: str, trigger_mode: str = "by_quantity") -> None:
        self.started_with = value
        self.trigger_mode = trigger_mode
        self.status_payload = {
            **self.status_payload,
            "status": "running",
            "trigger_mode": trigger_mode,
            "can_start": False,
            "can_stop": True,
        }

    async def stop(self) -> None:
        self.stopped = True
        self.status_payload = {
            **self.status_payload,
            "status": "idle",
            "can_start": True,
            "can_stop": False,
        }

    def get_status_payload(self) -> dict:
        return self.status_payload


@pytest.mark.anyio
async def test_manager_routes_open_live_start() -> None:
    open_live = FakeSession(mode="open_live")
    third_party = FakeSession(mode="third_party")
    manager = LiveSessionManager(
        open_live_session=open_live,
        third_party_session=third_party,
    )

    await manager.start(mode="open_live", value="code-demo", trigger_mode="single")

    assert open_live.started_with == "code-demo"
    assert open_live.trigger_mode == "single"
    assert third_party.started_with is None


@pytest.mark.anyio
async def test_manager_routes_third_party_start() -> None:
    open_live = FakeSession(mode="open_live")
    third_party = FakeSession(mode="third_party")
    manager = LiveSessionManager(
        open_live_session=open_live,
        third_party_session=third_party,
    )

    await manager.start(mode="third_party", value="123456", trigger_mode="by_quantity")

    assert third_party.started_with == "123456"
    assert third_party.trigger_mode == "by_quantity"
    assert open_live.started_with is None


@pytest.mark.anyio
async def test_manager_stop_only_calls_active_mode() -> None:
    open_live = FakeSession(mode="open_live")
    third_party = FakeSession(mode="third_party")
    manager = LiveSessionManager(
        open_live_session=open_live,
        third_party_session=third_party,
    )

    await manager.start(mode="third_party", value="123456", trigger_mode="by_quantity")
    await manager.stop()

    assert third_party.stopped is True
    assert open_live.stopped is False


def test_manager_status_includes_current_mode() -> None:
    open_live = FakeSession(mode="open_live")
    third_party = FakeSession(mode="third_party")
    manager = LiveSessionManager(
        open_live_session=open_live,
        third_party_session=third_party,
    )

    payload = manager.get_status_payload()

    assert payload["mode"] == "open_live"
    assert payload["mode_label"] == "官方 open-live"
    assert payload["trigger_mode"] == "by_quantity"
