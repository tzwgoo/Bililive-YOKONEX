from __future__ import annotations

from app.config import load_settings


def test_load_settings_reads_third_party_runtime_config(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("GIFT_MAPPING_PATH", "config/custom.json")
    monkeypatch.setattr("app.config.resolve_persistent_path", lambda _path: tmp_path / ".env")

    settings = load_settings()

    assert settings.gift_mapping_path == "config/custom.json"


def test_load_settings_reads_silent_management_config(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("MANAGEMENT_WS_URL", "ws://127.0.0.1:9000/device/ws")
    monkeypatch.setenv("MANAGEMENT_REGISTRATION_TOKEN", "register-token")
    monkeypatch.setenv("MANAGEMENT_CLIENT_NAME", "直播电脑")
    monkeypatch.setenv("MANAGEMENT_HEARTBEAT_SECONDS", "20")
    monkeypatch.setattr("app.config.resolve_persistent_path", lambda _path: tmp_path / ".env")

    settings = load_settings()

    assert settings.management_ws_url == "ws://127.0.0.1:9000/device/ws"
    assert settings.management_registration_token == "register-token"
    assert settings.management_client_name == "直播电脑"
    assert settings.management_heartbeat_seconds == 20
