from __future__ import annotations

import pytest

from app.third_party.ws_client import ThirdPartyWsClient


def test_ws_client_prefers_aiohttp_when_no_client_selected() -> None:
    selected: list[str] = []

    def fake_get_selected_client():
        raise RuntimeError("none selected")

    def fake_get_registered_clients():
        return {
            "httpx": object(),
            "aiohttp": object(),
        }

    client = ThirdPartyWsClient(
        client_selector=selected.append,
        selected_client_getter=fake_get_selected_client,
        registered_clients_getter=fake_get_registered_clients,
    )

    client.ensure_supported_client_selected()

    assert selected == ["aiohttp"]


def test_ws_client_switches_from_httpx_to_aiohttp() -> None:
    selected: list[str] = []

    def fake_get_selected_client():
        return ("httpx", object())

    def fake_get_registered_clients():
        return {
            "httpx": object(),
            "aiohttp": object(),
        }

    client = ThirdPartyWsClient(
        client_selector=selected.append,
        selected_client_getter=fake_get_selected_client,
        registered_clients_getter=fake_get_registered_clients,
    )

    client.ensure_supported_client_selected()

    assert selected == ["aiohttp"]


def test_ws_client_keeps_supported_selected_client() -> None:
    selected: list[str] = []

    def fake_get_selected_client():
        return ("aiohttp", object())

    def fake_get_registered_clients():
        return {
            "httpx": object(),
            "aiohttp": object(),
        }

    client = ThirdPartyWsClient(
        client_selector=selected.append,
        selected_client_getter=fake_get_selected_client,
        registered_clients_getter=fake_get_registered_clients,
    )

    client.ensure_supported_client_selected()

    assert selected == []


def test_ws_client_raises_when_no_supported_ws_backend_available() -> None:
    def fake_get_selected_client():
        raise RuntimeError("none selected")

    def fake_get_registered_clients():
        return {
            "httpx": object(),
        }

    client = ThirdPartyWsClient(
        client_selector=lambda _: None,
        selected_client_getter=fake_get_selected_client,
        registered_clients_getter=fake_get_registered_clients,
    )

    with pytest.raises(RuntimeError, match="需要安装 aiohttp 或 curl_cffi"):
        client.ensure_supported_client_selected()


@pytest.mark.anyio
async def test_ws_client_registers_extended_gift_related_events() -> None:
    registered_events: list[str] = []

    class FakeLiveDanmaku:
        def on(self, event_name: str):
            registered_events.append(event_name)

            def _decorator(handler):
                return handler

            return _decorator

        async def connect(self) -> None:
            return None

        async def disconnect(self) -> None:
            return None

    client = ThirdPartyWsClient(
        live_danmaku_factory=lambda _room_id: FakeLiveDanmaku(),
        client_selector=lambda _: None,
        selected_client_getter=lambda: ("aiohttp", object()),
        registered_clients_getter=lambda: {"aiohttp": object()},
    )

    async def _on_message(_message: dict) -> None:
        return None

    await client.connect_and_consume(room_id=123456, on_message=_on_message)

    assert "SEND_GIFT" in registered_events
    assert "COMBO_SEND" in registered_events
    assert "GUARD_BUY" in registered_events
    assert "SUPER_CHAT_MESSAGE" in registered_events
    assert "SUPER_CHAT_MESSAGE_JPN" in registered_events
    assert "USER_TOAST_MSG" in registered_events
    assert "INTERACT_WORD" in registered_events
    assert "INTERACT_WORD_V2" in registered_events
