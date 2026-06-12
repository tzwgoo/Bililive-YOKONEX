from __future__ import annotations

import json
from pathlib import Path

from app.runtime import ensure_persistent_file, resolve_bundle_path, resolve_persistent_path, resolve_runtime_path


def test_resolve_bundle_path_points_to_repo_resource() -> None:
    path = resolve_bundle_path("app/templates/index.html")

    assert path == Path(__file__).resolve().parent.parent / "app" / "templates" / "index.html"


def test_resolve_runtime_path_points_to_repo_runtime_file() -> None:
    path = resolve_runtime_path("config/gift_command_mappings.json")

    assert path == Path(__file__).resolve().parent.parent / "config" / "gift_command_mappings.json"


def test_resolve_persistent_path_uses_runtime_root_in_source_mode() -> None:
    path = resolve_persistent_path("config/gift_command_mappings.json")

    assert path == Path(__file__).resolve().parent.parent / "config" / "gift_command_mappings.json"


def test_resolve_persistent_path_uses_appdata_and_migrates_legacy_file(monkeypatch, tmp_path) -> None:
    legacy_root = tmp_path / "legacy"
    legacy_file = legacy_root / "config" / "gift_command_mappings.json"
    legacy_file.parent.mkdir(parents=True, exist_ok=True)
    legacy_file.write_text('{"rules":[]}', encoding="utf-8")

    appdata_root = tmp_path / "appdata"
    monkeypatch.setenv("APPDATA", str(appdata_root))
    monkeypatch.delenv("BILILIVE_USER_DATA_DIR", raising=False)
    monkeypatch.setattr("app.runtime.runtime_root", lambda: legacy_root)
    monkeypatch.setattr("app.runtime.sys", type("FrozenSys", (), {"frozen": True, "executable": str(legacy_root / "app.exe")})())

    path = resolve_persistent_path("config/gift_command_mappings.json")

    assert path == appdata_root / "Bililive-YOKONEX" / "config" / "gift_command_mappings.json"
    assert path.exists()
    assert path.read_text(encoding="utf-8") == '{"rules":[]}'


def test_ensure_persistent_file_copies_bundled_default_when_no_legacy_exists(monkeypatch, tmp_path) -> None:
    legacy_root = tmp_path / "legacy"
    appdata_root = tmp_path / "appdata"
    bundled_default = legacy_root / "config" / "gift_command_mappings.json"
    bundled_default.parent.mkdir(parents=True, exist_ok=True)
    bundled_default.write_text('{"rules":[{"min_price":0}]}', encoding="utf-8")

    monkeypatch.setenv("APPDATA", str(appdata_root))
    monkeypatch.delenv("BILILIVE_USER_DATA_DIR", raising=False)
    monkeypatch.setattr("app.runtime.runtime_root", lambda: legacy_root)
    monkeypatch.setattr("app.runtime.sys", type("FrozenSys", (), {"frozen": True, "executable": str(legacy_root / "app.exe")})())

    path = ensure_persistent_file(
        "config/gift_command_mappings.json",
        default_source_path=bundled_default,
    )

    assert path == appdata_root / "Bililive-YOKONEX" / "config" / "gift_command_mappings.json"
    assert path.exists()
    assert path.read_text(encoding="utf-8") == '{"rules":[{"min_price":0}]}'


def test_default_command_mapping_config_includes_sc_and_guard_event_rules() -> None:
    config_path = Path(__file__).resolve().parent.parent / "config" / "gift_command_mappings.json"

    payload = json.loads(config_path.read_text(encoding="utf-8"))
    rules = payload["rules"]

    super_chat_rules = [rule for rule in rules if rule.get("event_type") == "super_chat"]
    guard_buy_rules = [rule for rule in rules if rule.get("event_type") == "guard_buy"]
    guard_renew_rules = [rule for rule in rules if rule.get("event_type") == "guard_renew"]

    assert [rule["min_price"] for rule in super_chat_rules] == [30, 50, 100, 500, 1000, 2000]
    assert [rule["command_slot"] for rule in super_chat_rules] == [
        "command_one",
        "command_two",
        "command_three",
        "command_four",
        "command_five",
        "command_six",
    ]
    assert [rule["min_price"] for rule in guard_buy_rules] == [100000, 1000000, 10000000]
    assert [rule["command_slot"] for rule in guard_buy_rules] == [
        "command_eight",
        "command_nine",
        "command_ten",
    ]
    assert [rule["min_price"] for rule in guard_renew_rules] == [50000, 1000000, 10000000]
    assert [rule["command_slot"] for rule in guard_renew_rules] == [
        "command_seven",
        "command_eight",
        "command_nine",
    ]
