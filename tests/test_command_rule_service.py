from __future__ import annotations

import pytest

from app.command_gateway.mapping import GiftCommandMapper
from app.services.command_rule_service import CommandRuleService


class FakeDanmakuDispatcher:
    def __init__(self) -> None:
        self.rules: list[dict] = []

    def set_command_slot_rules(self, rules: list[dict]) -> None:
        self.rules = rules


def test_service_sorts_price_rules_by_event_type_and_min_price(tmp_path) -> None:
    service = CommandRuleService(
        config_path=tmp_path / "gift_command_mappings.json",
        mapper=GiftCommandMapper([]),
        danmaku_dispatcher=FakeDanmakuDispatcher(),
    )

    payload = service.save_rules(
        {
            "rules": [
                {
                    "id": "gift-b",
                    "enabled": True,
                    "event_type": "gift",
                    "min_price": 100,
                    "max_price": 199,
                    "command_slot": "command_two",
                },
                {
                    "id": "gift-a",
                    "enabled": True,
                    "event_type": "gift",
                    "min_price": 0,
                    "max_price": 99,
                    "command_slot": "command_one",
                },
                {
                    "id": "sc-a",
                    "enabled": True,
                    "event_type": "super_chat",
                    "min_price": 0,
                    "max_price": 199,
                    "command_slot": "command_five",
                },
            ],
            "like_rules": [
                {
                    "id": "like-default",
                    "enabled": True,
                    "like_multiple": 100,
                    "command_slot": "command_three",
                }
            ],
            "danmaku_slot_rules": [],
        }
    )

    assert [rule["id"] for rule in payload["rules"]] == ["gift-a", "gift-b", "sc-a"]


def test_service_rejects_overlapping_price_rules_in_same_event_type(tmp_path) -> None:
    service = CommandRuleService(
        config_path=tmp_path / "gift_command_mappings.json",
        mapper=GiftCommandMapper([]),
        danmaku_dispatcher=FakeDanmakuDispatcher(),
    )

    with pytest.raises(ValueError, match="价格区间重叠"):
        service.save_rules(
            {
                "rules": [
                    {
                        "id": "gift-a",
                        "enabled": True,
                        "event_type": "gift",
                        "min_price": 0,
                        "max_price": 100,
                        "command_slot": "command_one",
                    },
                    {
                        "id": "gift-b",
                        "enabled": True,
                        "event_type": "gift",
                        "min_price": 100,
                        "max_price": 199,
                        "command_slot": "command_two",
                    },
                ],
                "like_rules": [
                    {
                        "id": "like-default",
                        "enabled": True,
                        "like_multiple": 100,
                        "command_slot": "command_three",
                    }
                ],
                "danmaku_slot_rules": [],
            }
        )


def test_service_exposes_fixed_danmaku_command_ids_without_editable_rules(tmp_path) -> None:
    dispatcher = FakeDanmakuDispatcher()
    service = CommandRuleService(
        config_path=tmp_path / "gift_command_mappings.json",
        mapper=GiftCommandMapper([]),
        danmaku_dispatcher=dispatcher,
    )

    payload = service.save_rules(
        {
            "rules": [],
            "like_rules": [],
            "danmaku_slot_rules": [
                {
                    "id": "danmaku-governor",
                    "enabled": True,
                    "event_type": "danmaku_governor",
                    "command_slot": "command_ten",
                }
            ],
        }
    )

    assert payload["danmaku_slot_rules"] == []
    assert payload["danmaku_command_ids"]["danmaku"] == "danmaku_trigger"
    assert payload["danmaku_command_ids"]["danmaku_governor"] == "danmaku_governor_trigger"
    assert dispatcher.rules == []


def test_service_exposes_fixed_like_command_id_without_editable_rules(tmp_path) -> None:
    service = CommandRuleService(
        config_path=tmp_path / "gift_command_mappings.json",
        mapper=GiftCommandMapper([]),
        danmaku_dispatcher=FakeDanmakuDispatcher(),
    )

    payload = service.save_rules(
        {
            "rules": [],
            "like_rules": [
                {
                    "id": "like-default",
                    "enabled": True,
                    "like_multiple": 50,
                    "command_slot": "command_nine",
                }
            ],
            "danmaku_slot_rules": [],
        }
    )

    assert payload["like_rules"] == []
    assert payload["like_command_id"] == "like_trigger"
