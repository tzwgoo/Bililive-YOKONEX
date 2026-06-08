$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $projectRoot
$env:PYTHONNOUSERSITE = "1"

$buildEnvRoot = Join-Path $projectRoot ".build-venv"
$buildPython = Join-Path $buildEnvRoot "Scripts\python.exe"

if (-not (Test-Path $buildPython)) {
    python -m venv $buildEnvRoot
}

& $buildPython -m pip install --upgrade pip setuptools wheel
& $buildPython -m pip install pyinstaller
& $buildPython -m pip install -r requirements.txt

$npmCommand = (Get-Command npm.cmd -ErrorAction Stop).Source

Push-Location (Join-Path $projectRoot "frontend")
try {
    & $npmCommand ci
    & $npmCommand run build
} finally {
    Pop-Location
}

$frontendDistIndex = Join-Path $projectRoot "frontend/dist/index.html"
if (-not (Test-Path $frontendDistIndex)) {
    throw "Missing frontend dist output: $frontendDistIndex"
}

$distRoot = Join-Path $projectRoot "dist"
$packageRoot = Join-Path $distRoot "BiliLive-YOKONEX"
$buildLogDir = Join-Path $projectRoot "build_logs"
$stdoutLog = Join-Path $buildLogDir "pyinstaller.stdout.log"
$stderrLog = Join-Path $buildLogDir "pyinstaller.stderr.log"
$combinedLog = Join-Path $buildLogDir "pyinstaller.log"

New-Item -ItemType Directory -Force -Path $buildLogDir | Out-Null

if (Test-Path $packageRoot) {
    Remove-Item -Recurse -Force $packageRoot
}

$pyInstallerArgs = @(
    "-m",
    "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onedir",
    "--name", "BiliLive-YOKONEX",
    "--exclude-module", "PyQt5",
    "--exclude-module", "PyQt6",
    "--exclude-module", "PySide2",
    "--exclude-module", "PySide6",
    "--exclude-module", "matplotlib",
    "--exclude-module", "IPython",
    "--exclude-module", "jupyter_client",
    "--exclude-module", "jupyter_core",
    "--exclude-module", "jupyter_server",
    "--exclude-module", "gevent",
    "--exclude-module", "sqlalchemy",
    "--exclude-module", "zmq",
    "--exclude-module", "numpy",
    "--exclude-module", "scipy",
    "--exclude-module", "pandas",
    "--exclude-module", "tkinter",
    "--hidden-import", "bleak.backends.winrt.client",
    "--hidden-import", "bleak.backends.winrt.scanner",
    "--hidden-import", "bilibili_api.clients.HTTPXClient",
    "--hidden-import", "bilibili_api.clients.AioHTTPClient",
    "--add-data", "app/templates;app/templates",
    "--add-data", "app/static;app/static",
    "--add-data", "frontend/dist;frontend/dist",
    "run_app.py"
)

$pyInstallerProcess = Start-Process `
    -FilePath $buildPython `
    -ArgumentList $pyInstallerArgs `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -NoNewWindow `
    -PassThru `
    -Wait

if (Test-Path $combinedLog) {
    Remove-Item $combinedLog -Force
}
if (Test-Path $stdoutLog) {
    Get-Content $stdoutLog | Tee-Object -FilePath $combinedLog -Append
}
if (Test-Path $stderrLog) {
    Get-Content $stderrLog | Tee-Object -FilePath $combinedLog -Append
}

$pyInstallerExitCode = $pyInstallerProcess.ExitCode

if ($pyInstallerExitCode -ne 0) {
    throw "PyInstaller build failed with exit code: $pyInstallerExitCode"
}

New-Item -ItemType Directory -Force -Path (Join-Path $packageRoot "config") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $packageRoot "docs") | Out-Null
Copy-Item ".env.example" (Join-Path $packageRoot ".env.example") -Force
Copy-Item "config/gift_command_mappings.json" (Join-Path $packageRoot "config/gift_command_mappings.json") -Force
Copy-Item "config/gift_command_mappings.example.json" (Join-Path $packageRoot "config/gift_command_mappings.example.json") -Force
Copy-Item (Join-Path $projectRoot "docs\*.md") (Join-Path $packageRoot "docs") -Force

$exePath = Join-Path $packageRoot "BiliLive-YOKONEX.exe"
if (-not (Test-Path $exePath)) {
    throw "Missing EXE output: $exePath"
}

Write-Host ""
Write-Host "构建完成：" -ForegroundColor Green
Write-Host $packageRoot
Write-Host ""
Write-Host "启动文件：" -ForegroundColor Green
Write-Host $exePath
