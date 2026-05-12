from __future__ import annotations

from app.command_gateway.mapping import GiftCommandMapper


def test_mapper_prefers_gift_id_match() -> None:
    mapper = GiftCommandMapper(
        [
            {"gift_name": "小花花", "command_slot": "command_two"},
            {"gift_id": 1001, "command_slot": "command_one"},
        ]
    )

    command_id = mapper.resolve_command_id(
        {
            "gift_id": 1001,
            "gift_name": "小花花",
        }
    )

    assert command_id == "command_one"


def test_mapper_falls_back_to_gift_name() -> None:
    mapper = GiftCommandMapper(
        [
            {"gift_name": "小花花", "command_slot": "command_two"},
        ]
    )

    command_id = mapper.resolve_command_id(
        {
            "gift_id": 0,
            "gift_name": "小花花",
        }
    )

    assert command_id == "command_two"


def test_mapper_ignores_invalid_command_slot() -> None:
    mapper = GiftCommandMapper(
        [
            {"gift_id": 1001, "command_slot": "player_hurt"},
        ]
    )

    command_id = mapper.resolve_command_id(
        {
            "gift_id": 1001,
            "gift_name": "小花花",
        }
    )

    assert command_id is None
