$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot

python -m pip install pyinstaller

$distRoot = Join-Path $projectRoot "dist"
$packageRoot = Join-Path $distRoot "BiliLive-YOKONEX"

if (Test-Path $packageRoot) {
    Remove-Item -Recurse -Force $packageRoot
}

pyinstaller `
  --noconfirm `
  --clean `
  --onedir `
  --name "BiliLive-YOKONEX" `
  --exclude-module PyQt5 `
  --exclude-module PyQt6 `
  --exclude-module PySide2 `
  --exclude-module PySide6 `
  --exclude-module matplotlib `
  --exclude-module IPython `
  --exclude-module jupyter_client `
  --exclude-module jupyter_core `
  --exclude-module tkinter `
  --hidden-import "bilibili_api.clients.HTTPXClient" `
  --hidden-import "bilibili_api.clients.AioHTTPClient" `
  --hidden-import "bilibili_api.clients.CurlCFFIClient" `
  --add-data "app/templates;app/templates" `
  --add-data "app/static;app/static" `
  "run_app.py"

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller 构建失败，退出码: $LASTEXITCODE"
}

New-Item -ItemType Directory -Force -Path (Join-Path $packageRoot "config") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $packageRoot "docs") | Out-Null
Copy-Item ".env.example" (Join-Path $packageRoot ".env.example") -Force
Copy-Item "config/gift_command_mappings.json" (Join-Path $packageRoot "config/gift_command_mappings.json") -Force
Copy-Item "config/gift_command_mappings.example.json" (Join-Path $packageRoot "config/gift_command_mappings.example.json") -Force
Copy-Item (Join-Path $projectRoot "docs\*.md") (Join-Path $packageRoot "docs") -Force

$exePath = Join-Path $packageRoot "BiliLive-YOKONEX.exe"
if (-not (Test-Path $exePath)) {
    throw "构建输出缺少 EXE：$exePath"
}

Write-Host ""
Write-Host "构建完成：" -ForegroundColor Green
Write-Host $packageRoot
Write-Host ""
Write-Host "启动文件：" -ForegroundColor Green
Write-Host $exePath
