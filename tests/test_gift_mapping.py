from __future__ import annotations

import json

from app.command_gateway.mapping import GiftCommandMapper


def test_mapper_resolves_command_slot_by_price_range() -> None:
    mapper = GiftCommandMapper(
        [
            {"min_price": 0, "max_price": 99, "command_slot": "command_one"},
            {"min_price": 100, "max_price": 999, "command_slot": "command_two"},
        ]
    )

    command_id = mapper.resolve_command_id(
        {
            "gift_name": "小花花",
            "r_price": 100,
            "price": 100,
        }
    )

    assert command_id == "command_two"


def test_mapper_supports_open_ended_price_range() -> None:
    mapper = GiftCommandMapper(
        [
            {"min_price": 1000, "max_price": None, "command_slot": "command_ten"},
        ]
    )

    command_id = mapper.resolve_command_id(
        {
            "gift_name": "B站星跃",
            "r_price": 1000000,
        }
    )

    assert command_id == "command_ten"


def test_mapper_ignores_invalid_command_slot() -> None:
    mapper = GiftCommandMapper(
        [
            {"min_price": 0, "max_price": 999, "command_slot": "player_hurt"},
        ]
    )

    command_id = mapper.resolve_command_id(
        {
            "gift_name": "小花花",
            "r_price": 100,
        }
    )

    assert command_id is None


def test_mapper_prefers_unit_price_over_total_price() -> None:
    mapper = GiftCommandMapper(
        [
            {"min_price": 100, "max_price": 999, "command_slot": "command_two"},
            {"min_price": 1000, "max_price": 4999, "command_slot": "command_four"},
        ]
    )

    command_id = mapper.resolve_command_id(
        {
            "gift_name": "连击礼物",
            "gift_num": 3,
            "price": 100,
            "r_price": 3000,
        }
    )

    assert command_id == "command_two"


def test_mapper_supports_like_rule() -> None:
    mapper = GiftCommandMapper(
        [
            {"event_type": "like", "like_multiple": 10, "command_slot": "command_three"},
        ]
    )

    command_id, like_multiple = mapper.resolve_like_command({"like_count": 23})

    assert command_id == "command_three"
    assert like_multiple == 10


def test_mapper_supports_like_rules_from_dict_payload(tmp_path) -> None:
    path = tmp_path / "mapping.json"
    path.write_text(
        json.dumps(
            {
                "rules": [
                    {"min_price": 100, "max_price": 999, "command_slot": "command_two"},
                ],
                "like_rules": [
                    {"like_multiple": 5, "command_slot": "command_four"},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    mapper = GiftCommandMapper.from_file(path)

    command_id, like_multiple = mapper.resolve_like_command({"like_count": 11})

    assert command_id == "command_four"
    assert like_multiple == 5
