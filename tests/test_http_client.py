from __future__ import annotations

import httpx
import pytest

from app.bilibili.http_client import BilibiliOpenClient


@pytest.mark.anyio
async def test_start_returns_json_payload() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/app/start"
        return httpx.Response(
            200,
            json={"code": 0, "message": "ok", "data": {"game_info": {"game_id": "g1"}}},
        )

    transport = httpx.MockTransport(handler)
    client = BilibiliOpenClient(
        base_url="https://live-open.biliapi.com",
        access_key_id="ak",
        access_key_secret="sk",
        transport=transport,
    )

    payload = await client.start(app_id=1, code="demo")

    assert payload["data"]["game_info"]["game_id"] == "g1"
