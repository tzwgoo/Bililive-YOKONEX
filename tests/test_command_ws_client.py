from __future__ import annotations

from app.command_gateway.ws_client import derive_user_id_from_uid


def test_derive_user_id_from_game_uid() -> None:
    assert derive_user_id_from_uid("game_123456") == "123456"


def test_derive_user_id_from_numeric_uid() -> None:
    assert derive_user_id_from_uid("123456") == "123456"
