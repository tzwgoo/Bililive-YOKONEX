from __future__ import annotations

import pytest

from app.services.danmaku_settings import FIXED_DANMAKU_COMMAND_ID
from app.services.danmaku_settings import FIXED_DANMAKU_COMMAND_IDS
from app.services.live_session_manager import LiveSessionManager


class FakeCommandSession:
    def __init__(self, *, connected: bool) -> None:
        self.is_connected = connected


class FakeBluetoothService:
    def __init__(self, *, connected: bool) -> None:
        self.connected = connected

    def get_status_payload(self) -> dict:
        return {
            "connected": self.connected,
        }


class FakeSession:
    def __init__(self) -> None:
        self.started_with: str | None = None
        self.stopped = False
        self.trigger_mode = "by_quantity"
        self.output_mode = "im"
        self.status_payload = {
            "status": "idle",
            "message": "",
            "room_id": 0,
            "anchor_name": "",
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

    async def start(
        self,
        *,
        value: str,
        trigger_mode: str = "by_quantity",
        output_mode: str = "im",
        like_multiple: int = 100,
        danmaku_enabled: bool = False,
        danmaku_keywords: str = "",
        danmaku_command_id: str = "",
        danmaku_cooldown_seconds: int = 0,
        danmaku_user_limit_window_seconds: int = 0,
        danmaku_user_limit_max_triggers: int = 0,
        danmaku_min_guard_level: int = 0,
    ) -> None:
        self.started_with = value
        self.trigger_mode = trigger_mode
        self.output_mode = output_mode
        self.status_payload = {
            **self.status_payload,
            "status": "running",
            "trigger_mode": trigger_mode,
            "output_mode": output_mode,
            "like_multiple": like_multiple,
            "danmaku_enabled": danmaku_enabled,
            "danmaku_keywords": danmaku_keywords,
            "danmaku_command_id": danmaku_command_id,
            "danmaku_cooldown_seconds": danmaku_cooldown_seconds,
            "danmaku_user_limit_window_seconds": danmaku_user_limit_window_seconds,
            "danmaku_user_limit_max_triggers": danmaku_user_limit_max_triggers,
            "danmaku_min_guard_level": danmaku_min_guard_level,
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


def create_manager(
    *,
    command_connected: bool = False,
    bluetooth_connected: bool = False,
) -> tuple[LiveSessionManager, FakeSession]:
    third_party = FakeSession()
    manager = LiveSessionManager(
        third_party_session=third_party,
        command_session=FakeCommandSession(connected=command_connected),
        bluetooth_service=FakeBluetoothService(connected=bluetooth_connected),
    )
    return manager, third_party


@pytest.mark.anyio
async def test_manager_routes_third_party_start() -> None:
    manager, third_party = create_manager()

    await manager.start(mode="third_party", value="123456", trigger_mode="by_quantity", output_mode="im")

    assert third_party.started_with == "123456"
    assert third_party.trigger_mode == "by_quantity"
    assert third_party.output_mode == "im"


@pytest.mark.anyio
async def test_manager_defaults_blank_mode_to_third_party() -> None:
    manager, third_party = create_manager()

    await manager.start(mode="", value="123456", trigger_mode="single", output_mode="bluetooth")

    assert manager.mode == "third_party"
    assert third_party.started_with == "123456"
    assert third_party.output_mode == "bluetooth"


@pytest.mark.anyio
async def test_manager_rejects_removed_open_live_mode() -> None:
    manager, _ = create_manager()

    with pytest.raises(ValueError, match="不支持的监听模式"):
        await manager.start(mode="open_live", value="code-demo")


@pytest.mark.anyio
async def test_manager_ignores_custom_danmaku_command_id_and_uses_fixed_slot() -> None:
    manager, third_party = create_manager()

    await manager.start(
        mode="third_party",
        value="123456",
        danmaku_enabled=True,
        danmaku_keywords="开火",
        danmaku_command_id="boss_warning",
    )

    assert third_party.status_payload["danmaku_command_id"] == FIXED_DANMAKU_COMMAND_ID
    assert manager.danmaku_command_id == FIXED_DANMAKU_COMMAND_ID


@pytest.mark.anyio
async def test_manager_defaults_output_mode_to_im() -> None:
    manager, third_party = create_manager()

    await manager.start(mode="third_party", value="123456")

    assert manager.output_mode == "im"
    assert third_party.output_mode == "im"


@pytest.mark.anyio
async def test_manager_prefers_bluetooth_output_when_bluetooth_is_connected() -> None:
    manager, third_party = create_manager(command_connected=True, bluetooth_connected=True)

    await manager.start(mode="third_party", value="123456")

    assert manager.output_mode == "bluetooth"
    assert third_party.output_mode == "bluetooth"


@pytest.mark.anyio
async def test_manager_uses_im_output_when_only_im_is_connected() -> None:
    manager, third_party = create_manager(command_connected=True, bluetooth_connected=False)

    await manager.start(mode="third_party", value="123456")

    assert manager.output_mode == "im"
    assert third_party.output_mode == "im"


@pytest.mark.anyio
async def test_manager_switches_running_session_to_bluetooth_after_device_connects() -> None:
    manager, third_party = create_manager(command_connected=True, bluetooth_connected=False)

    await manager.start(mode="third_party", value="123456", output_mode="im")

    manager.handle_bluetooth_connected()

    assert manager.output_mode == "bluetooth"
    assert third_party.output_mode == "bluetooth"


@pytest.mark.anyio
async def test_manager_stop_only_calls_active_session() -> None:
    manager, third_party = create_manager()

    await manager.start(mode="third_party", value="123456", trigger_mode="by_quantity")
    await manager.stop()

    assert third_party.stopped is True


def test_manager_status_includes_current_mode() -> None:
    manager, _ = create_manager()

    payload = manager.get_status_payload()

    assert payload["mode"] == "third_party"
    assert payload["mode_label"] == "第三方房间消息流"
    assert payload["output_mode"] == "im"
    assert payload["trigger_mode"] == "by_quantity"
    assert payload["danmaku_command_id"] == FIXED_DANMAKU_COMMAND_ID
    assert payload["danmaku_command_ids"] == FIXED_DANMAKU_COMMAND_IDS
    assert payload["danmaku_user_limit_window_seconds"] == 0
    assert payload["danmaku_user_limit_max_triggers"] == 0
    assert payload["danmaku_min_guard_level"] == 0


@pytest.mark.anyio
async def test_manager_passes_extended_danmaku_controls_to_session() -> None:
    manager, third_party = create_manager()

    await manager.start(
        mode="third_party",
        value="123456",
        danmaku_enabled=True,
        danmaku_keywords="开火",
        danmaku_cooldown_seconds=15,
        danmaku_user_limit_window_seconds=60,
        danmaku_user_limit_max_triggers=2,
        danmaku_min_guard_level=2,
    )

    assert third_party.status_payload["danmaku_user_limit_window_seconds"] == 60
    assert third_party.status_payload["danmaku_user_limit_max_triggers"] == 2
    assert third_party.status_payload["danmaku_min_guard_level"] == 2
    assert manager.danmaku_user_limit_window_seconds == 60
    assert manager.danmaku_user_limit_max_triggers == 2
    assert manager.danmaku_min_guard_level == 2
