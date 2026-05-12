from __future__ import annotations

from app.bilibili.signature import build_content_md5


def test_build_content_md5_is_lowercase_hex() -> None:
    assert build_content_md5('{"app_id":1}') == "9531e062cc94e68b5ba708eec735ff95"
