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
