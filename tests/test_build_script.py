from __future__ import annotations

from pathlib import Path


def test_build_script_includes_bilibili_client_hidden_imports() -> None:
    script = (Path(__file__).resolve().parent.parent / "build_exe.ps1").read_text(encoding="utf-8")

    assert "bilibili_api.clients.HTTPXClient" in script
    assert "bilibili_api.clients.AioHTTPClient" in script
