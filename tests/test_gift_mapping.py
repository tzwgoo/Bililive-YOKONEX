from __future__ import annotations

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
