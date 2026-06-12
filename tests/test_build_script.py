from __future__ import annotations

from pathlib import Path


def test_build_script_includes_bilibili_client_hidden_imports() -> None:
    script = (Path(__file__).resolve().parent.parent / "build_exe.ps1").read_text(encoding="utf-8")

    assert "bilibili_api.clients.HTTPXClient" in script
    assert "bilibili_api.clients.AioHTTPClient" in script
    assert ".build-venv" in script
    assert '$env:PYTHONNOUSERSITE = "1"' in script
    assert 'Start-Process `' in script
    assert '-FilePath $buildPython' in script
    assert "-RedirectStandardOutput $stdoutLog" in script
    assert "-RedirectStandardError $stderrLog" in script
    assert "$pyInstallerExitCode = $pyInstallerProcess.ExitCode" in script
    assert 'throw "PyInstaller build failed with exit code: $pyInstallerExitCode"' in script
    assert 'Copy-Item "config/gift_command_mappings.json"' in script
    assert 'Copy-Item "config/bluetooth_settings.json"' not in script
    assert '$requiredPackageFiles = @(' in script
    assert 'throw "Missing packaged file: $requiredFile"' in script
    assert 'Push-Location (Join-Path $projectRoot "frontend")' in script
    assert '& $npmCommand ci' in script
    assert '& $npmCommand run build' in script
    assert '--add-data", "frontend/dist;frontend/dist"' in script
