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
    assert "pyinstaller" in workflow
    assert "PyInstaller" in workflow
    assert 'Start-Process `' in workflow
    assert workflow.count("pip install pyinstaller") == 1
    assert "Copy-Item" in workflow
    assert "Compress-Archive" in workflow
    assert "python --version" in workflow
    assert "Get-Command python" in workflow
    assert "upload-artifact" in workflow
    assert "if: failure()" in workflow
    assert "gh release create" in workflow
    assert "gh release upload" in workflow
    assert "BiliLive-YOKONEX.exe" in workflow
    assert "Bililive-YOKONEX-" in workflow


def test_release_workflow_powershell_run_blocks_use_ascii_error_messages() -> None:
    workflow = (
        Path(__file__).resolve().parent.parent / ".github" / "workflows" / "release.yml"
    ).read_text(encoding="utf-8")

    assert 'Start-Process `' in workflow
    assert '-FilePath "python"' in workflow
    assert "-RedirectStandardOutput $stdoutLog" in workflow
    assert "-RedirectStandardError $stderrLog" in workflow
    assert "$pyInstallerExitCode = $pyInstallerProcess.ExitCode" in workflow
    assert 'throw "PyInstaller build failed with exit code: $pyInstallerExitCode"' in workflow
    assert 'throw "Missing EXE output: $exePath"' in workflow
    assert 'throw "PyInstaller 构建失败' not in workflow
    assert 'throw "构建输出缺少 EXE' not in workflow
