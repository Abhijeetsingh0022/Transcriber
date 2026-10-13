# PowerShell 1-Click Master Launcher for Transcriber Workstation
# Supports Full Studio Mode (Port 3000 + 8000) and Standalone Mode (Port 8000)

Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "         TRANSCRIBER AI WORKSTATION - POWERSHELL LAUNCHER          " -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host ""

$rootPath = $PSScriptRoot
$backendPath = Join-Path $rootPath "backend"
$frontendPath = Join-Path $rootPath "frontend"

# 1. Check Python
$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pyCmd) {
    Write-Host "[ERROR] Python was not found in your PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/downloads/" -ForegroundColor Yellow
    Exit 1
}

# 2. Check Node.js
$hasNode = $true
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) { $hasNode = $false }

# 3. Check Backend Setup
$venvBat = Join-Path $backendPath ".venv\Scripts\activate.bat"
if (-not (Test-Path $venvBat)) {
    Write-Host "[INFO] First-time setup detected. Configuring Python environment..." -ForegroundColor Cyan
    & (Join-Path $backendPath "setup.ps1")
}

# 4. Check Frontend Setup
if ($hasNode) {
    $nodeModules = Join-Path $frontendPath "node_modules"
    if (-not (Test-Path $nodeModules)) {
        Write-Host "[INFO] Installing frontend dependencies..." -ForegroundColor Cyan
        Push-Location $frontendPath
        & npm install
        Pop-Location
    }
}

# 5. Launch Option
Write-Host ""
Write-Host "Select Launch Mode:" -ForegroundColor Yellow
Write-Host "  [1] Full Studio Mode (Next.js :3000 + FastAPI :8000) [RECOMMENDED]"
Write-Host "  [2] Standalone Mode  (Unified Server on http://localhost:8000)"
Write-Host "  [3] Run Hardware Diagnostics (CPU & GPU Benchmark)"
Write-Host "  [4] Stop Any Running Transcriber Servers"
Write-Host ""

$choice = Read-Host "Choose option [1-4] (Default 1)"
if (-not $choice) { $choice = "1" }

if ($choice -eq "2") {
    Write-Host "[INFO] Starting Standalone Server on http://localhost:8000 ..." -ForegroundColor Green
    Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd /d `"$backendPath`" && call .venv\Scripts\activate.bat && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:8000"
}
elseif ($choice -eq "3") {
    $venvPy = Join-Path $backendPath ".venv\Scripts\python.exe"
    $diagScript = Join-Path $backendPath "verify_gpu.py"
    & $venvPy $diagScript
}
elseif ($choice -eq "4") {
    & (Join-Path $rootPath "stop_windows.bat")
}
else {
    Write-Host "[1/2] Starting Backend API Server (http://localhost:8000) ..." -ForegroundColor Green
    Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd /d `"$backendPath`" && call .venv\Scripts\activate.bat && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

    if ($hasNode) {
        Write-Host "[2/2] Starting Next.js Studio Frontend (http://localhost:3000) ..." -ForegroundColor Green
        Start-Process -FilePath "cmd.exe" -ArgumentList "/k cd /d `"$frontendPath`" && npm run dev"
        Start-Sleep -Seconds 3
        Start-Process "http://localhost:3000"
    } else {
        Start-Sleep -Seconds 3
        Start-Process "http://localhost:8000"
    }

    Write-Host ""
    Write-Host "Transcriber Studio is launching!" -ForegroundColor Cyan
    Write-Host "To stop servers later, run: .\stop_windows.bat" -ForegroundColor Yellow
}
