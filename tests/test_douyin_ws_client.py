from __future__ import annotations

from urllib.parse import parse_qs
from urllib.parse import urlparse

from app.douyin.ws_client import DouyinWsClient


def test_douyin_ws_client_builds_cookie_b64_url() -> None:
    client = DouyinWsClient()

    url = client._build_ws_url(
        room_id="516466932480",
        base_url="ws://127.0.0.1:1088",
        douyin_cookie="sessionid=demo",
    )

    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "ws"
    assert parsed.netloc == "127.0.0.1:1088"
    assert parsed.path == "/ws/516466932480"
    assert query["cookie_b64"] == ["c2Vzc2lvbmlkPWRlbW8="]


def test_douyin_ws_client_preserves_existing_query_without_plain_cookie() -> None:
    client = DouyinWsClient()

    url = client._build_ws_url(
        room_id="516466932480",
        base_url="ws://127.0.0.1:1088?debug=1&cookie=old",
        douyin_cookie="sessionid=demo",
    )

    query = parse_qs(urlparse(url).query)

    assert query["debug"] == ["1"]
    assert "cookie" not in query
    assert query["cookie_b64"] == ["c2Vzc2lvbmlkPWRlbW8="]
