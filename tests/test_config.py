from __future__ import annotations

from app.config import load_settings


def test_load_settings_reads_third_party_runtime_config(
    monkeypatch,
    tmp_path,
) -> None:
    monkeypatch.setenv("GIFT_MAPPING_PATH", "config/custom.json")
    monkeypatch.setattr("app.config.resolve_runtime_path", lambda _path: tmp_path / ".env")

    settings = load_settings()

    assert settings.gift_mapping_path == "config/custom.json"
