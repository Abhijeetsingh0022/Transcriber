# PowerShell Setup Script for Transcriber on Windows
# Optimized for NVIDIA GeForce RTX 2080 (CUDA 12.x, FP16 Tensor Cores, CTranslate2)

Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "     TRANSCRIBER WINDOWS SETUP - NVIDIA RTX 2080 GPU OPTIMIZATION   " -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python is not installed or not in your PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.10, 3.11, or 3.12 and ensure 'Add python.exe to PATH' is checked." -ForegroundColor Yellow
    Exit 1
}

$pyVer = & python --version 2>&1
Write-Host "[INFO] Detected Python: $pyVer" -ForegroundColor Green

# 2. Check NVIDIA GPU
$nvidiaSmi = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidiaSmi) {
    Write-Host "[INFO] NVIDIA Driver Telemetry:" -ForegroundColor Green
    & nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
} else {
    Write-Host "[WARNING] nvidia-smi not detected in PATH. Ensure NVIDIA GeForce drivers are installed." -ForegroundColor Yellow
}

# 3. Create Virtual Environment
$venvPath = Join-Path $PSScriptRoot ".venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "[INFO] Creating virtual environment in .venv..." -ForegroundColor Cyan
    & python -m venv $venvPath
} else {
    Write-Host "[INFO] Found existing virtual environment in .venv." -ForegroundColor Green
}

$venvPython = Join-Path $venvPath "Scripts\python.exe"
$venvPip = Join-Path $venvPath "Scripts\pip.exe"

# 4. Upgrade Pip
Write-Host "[INFO] Upgrading pip in virtual environment..." -ForegroundColor Cyan
& $venvPython -m pip install --upgrade pip

# 5. Install PyTorch with CUDA 12.4
Write-Host "[INFO] Installing PyTorch with CUDA 12.4 for Turing Tensor Cores..." -ForegroundColor Cyan
& $venvPip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

# 6. Install cuBLAS and cuDNN Windows wheels
Write-Host "[INFO] Installing cuBLAS and cuDNN Windows runtime libraries..." -ForegroundColor Cyan
& $venvPip install nvidia-cublas-cu12 nvidia-cudnn-cu12

# 7. Install requirements
$reqPath = Join-Path $PSScriptRoot "requirements-cuda.txt"
Write-Host "[INFO] Installing Transcriber backend dependencies..." -ForegroundColor Cyan
& $venvPip install -r $reqPath

# 8. Initialize Database
Write-Host "[INFO] Initializing SQLite database..." -ForegroundColor Cyan
& $venvPython -c "from db.database import init_db; init_db()"

# 9. Run Diagnostics
Write-Host ""
Write-Host "===================================================================" -ForegroundColor Cyan
Write-Host "                 RUNNING GPU DIAGNOSTIC AUDIT                       " -ForegroundColor Cyan
Write-Host "===================================================================" -ForegroundColor Cyan
$verifyScript = Join-Path $PSScriptRoot "verify_gpu.py"
& $venvPython $verifyScript

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "===================================================================" -ForegroundColor Green
    Write-Host "  SUCCESS: Transcriber is configured and optimized!                " -ForegroundColor Green
    Write-Host "  - ML Engine: CPU (AVX2/INT8 Vector Optimized with Core Reserve)   " -ForegroundColor Green
    Write-Host "  - NVIDIA GPU: Unburdened for Studio Video, Muxing & 60fps UI      " -ForegroundColor Green
    Write-Host "  (To force GPU ML inference instead, set: TRANSCRIBER_DEVICE=cuda)" -ForegroundColor Cyan
    Write-Host "  To launch the backend, run: .\run.bat                            " -ForegroundColor Green
    Write-Host "===================================================================" -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "[WARNING] One or more diagnostic checks reported an issue." -ForegroundColor Yellow
}
