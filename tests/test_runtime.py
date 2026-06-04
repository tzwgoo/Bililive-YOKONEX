from __future__ import annotations

import json
from pathlib import Path

from app.runtime import resolve_bundle_path, resolve_runtime_path


def test_resolve_bundle_path_points_to_repo_resource() -> None:
    path = resolve_bundle_path("app/templates/index.html")

    assert path == Path(__file__).resolve().parent.parent / "app" / "templates" / "index.html"


def test_resolve_runtime_path_points_to_repo_runtime_file() -> None:
    path = resolve_runtime_path("config/gift_command_mappings.json")

    assert path == Path(__file__).resolve().parent.parent / "config" / "gift_command_mappings.json"


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
