from __future__ import annotations

from pathlib import Path


def test_release_workflow_publishes_windows_exe_on_version_tag() -> None:
    workflow = (
        Path(__file__).resolve().parent.parent / ".github" / "workflows" / "release.yml"
    ).read_text(encoding="utf-8")

    assert 'tags:' in workflow
    assert '- "v*"' in workflow
    assert "windows-latest" in workflow
    assert "contents: write" in workflow
    assert "build_exe.ps1" in workflow
    assert "Compress-Archive" in workflow
    assert "gh release create" in workflow
    assert "gh release upload" in workflow
    assert "BiliLive-YOKONEX.exe" in workflow
    assert "Bililive-YOKONEX-" in workflow
