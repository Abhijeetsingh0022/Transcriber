@echo off
setlocal enabledelayedexpansion

echo ===================================================================
echo     TRANSCRIBER WINDOWS SETUP - NVIDIA RTX 2080 GPU OPTIMIZATION   
echo ===================================================================
echo.

:: 1. Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not found in system PATH!
    echo Please install Python 3.10, 3.11, or 3.12 from https://www.python.org/downloads/
    echo Remember to check the box: "Add python.exe to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo [INFO] Detected: %PYTHON_VER%

:: 2. Check NVIDIA GPU via nvidia-smi
where nvidia-smi >nul 2>nul
if %errorlevel% equ 0 (
    echo [INFO] Detected NVIDIA Hardware:
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
) else (
    echo [WARNING] nvidia-smi not found. Ensure NVIDIA GeForce Game Ready or Studio Drivers are installed.
)

:: 3. Setup Virtual Environment
if not exist ".venv" (
    echo [INFO] Creating Python virtual environment in .venv...
    python -m venv .venv
) else (
    echo [INFO] Found existing virtual environment in .venv.
)

echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat

:: 4. Upgrade pip
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

:: 5. Install PyTorch with CUDA 12.4
echo [INFO] Installing PyTorch with CUDA 12.4 support for Turing Tensor Cores...
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124

:: 6. Install NVIDIA cuBLAS and cuDNN wheels for CTranslate2 / Faster-Whisper on Windows
echo [INFO] Installing cuBLAS and cuDNN Windows runtime libraries...
pip install nvidia-cublas-cu12 nvidia-cudnn-cu12

:: 7. Install remaining dependencies
echo [INFO] Installing Transcriber backend dependencies...
pip install -r requirements-cuda.txt

:: 8. Initialize SQLite Database
echo [INFO] Initializing Transcriber SQLite Database...
python -c "from db.database import init_db; init_db()"

:: 9. Run GPU Verification Test
echo.
echo ===================================================================
echo                 RUNNING GPU DIAGNOSTIC AUDIT                       
echo ===================================================================
python verify_gpu.py

if %errorlevel% equ 0 (
    echo.
    echo ===================================================================
    echo  SUCCESS: Transcriber is configured and optimized!
    echo  - ML Inference: CPU (AVX2 / INT8 vector-optimized with core reservation)
    echo  - NVIDIA GPU:   Unburdened for Studio Video, Muxing, and 60fps UI
    echo  (To force GPU ML inference instead, set: TRANSCRIBER_DEVICE=cuda)
    echo  To launch the backend, double-click: run.bat
    echo ===================================================================
) else (
    echo.
    echo [WARNING] One or more diagnostic checks reported an issue. Review output above.
)

pause
