@echo off
setlocal enabledelayedexpansion
title Transcriber Workstation Launcher

cd /d "%~dp0"

echo ===================================================================
echo             TRANSCRIBER AI WORKSTATION - WINDOWS LAUNCHER          
echo ===================================================================
echo.

:: 1. Check Python or py launcher
set PY_CMD=python
where python >nul 2>nul
if %errorlevel% neq 0 (
    where py >nul 2>nul
    if %errorlevel% equ 0 (
        set PY_CMD=py -3
    ) else (
        echo [ERROR] Python was not found in your system PATH!
        echo Please install Python 3.10, 3.11, or 3.12 from:
        echo   https://www.python.org/downloads/
        echo IMPORTANT: Make sure to check the box "Add python.exe to PATH" during install.
        echo.
        pause
        exit /b 1
    )
)

:: 2. Check Node.js
set HAS_NODE=1
where node >nul 2>nul
if %errorlevel% neq 0 (
    set HAS_NODE=0
)
where npm >nul 2>nul
if %errorlevel% neq 0 (
    set HAS_NODE=0
)

:: 3. Check Backend Setup
if not exist "backend\.venv\Scripts\activate.bat" (
    echo [INFO] First-time setup detected. Setting up Python environment...
    echo.
    call backend\setup.bat
    if %errorlevel% neq 0 (
        echo [ERROR] Backend setup encountered an issue. Review logs above.
        pause
        exit /b 1
    )
)

:: 4. Check Frontend Setup
if %HAS_NODE% equ 1 (
    if not exist "frontend\node_modules" (
        echo [INFO] Installing frontend dependencies (Next.js 16 / React 19)...
        cd frontend
        call npm install
        cd ..
    )
)

:: 5. Menu / Quick Start
echo.
echo Select Launch Mode:
echo   [1] Full Studio Mode (Next.js Frontend on :3000 + Backend on :8000) [RECOMMENDED]
echo   [2] Standalone Mode  (Unified Server on http://localhost:8000 - No Node.js required)
echo   [3] Run Hardware Diagnostics (CPU & GPU Benchmark)
echo   [4] Stop / Kill Any Running Transcriber Servers
echo   [5] Exit
echo.

set CHOICE=1
choice /C 12345 /T 4 /D 1 /M "Choose an option (Auto-starting [1] in 4 seconds):"
set SEL=%errorlevel%

if %SEL% equ 1 goto :LAUNCH_FULL
if %SEL% equ 2 goto :LAUNCH_STANDALONE
if %SEL% equ 3 goto :RUN_DIAG
if %SEL% equ 4 goto :STOP_SERVERS
if %SEL% equ 5 exit /b 0

:LAUNCH_FULL
if %HAS_NODE% equ 0 (
    echo.
    echo [WARNING] Node.js is not installed or not in PATH.
    echo Defaulting to Standalone Mode on http://localhost:8000 ...
    timeout /t 2 >nul
    goto :LAUNCH_STANDALONE
)

echo.
echo ===================================================================
echo [1/3] Starting Backend API Server (http://localhost:8000) ...
start "Transcriber Backend API" cmd /k "cd /d "%~dp0backend" && call .venv\Scripts\activate.bat && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/3] Starting Next.js Studio Frontend (http://localhost:3000) ...
start "Transcriber Studio Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo [3/3] Waiting for servers to initialize...
timeout /t 3 >nul

echo [INFO] Opening Transcriber Studio in your default browser...
start http://localhost:3000

echo.
echo ===================================================================
echo  Transcriber Studio is LIVE!
echo  - Studio Web App: http://localhost:3000
echo  - API & Docs:     http://localhost:8000/docs
echo  To cleanly shut down servers later, double-click: stop_windows.bat
echo ===================================================================
echo.
pause
exit /b 0

:LAUNCH_STANDALONE
echo.
echo ===================================================================
echo [1/2] Starting Standalone Transcriber Server (http://localhost:8000) ...
start "Transcriber Standalone Server" cmd /k "cd /d "%~dp0backend" && call .venv\Scripts\activate.bat && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/2] Waiting for server to initialize...
timeout /t 3 >nul

echo [INFO] Opening Transcriber Studio in your default browser...
start http://localhost:8000

echo.
echo ===================================================================
echo  Transcriber Standalone is LIVE on http://localhost:8000 !
echo  To cleanly shut down server later, double-click: stop_windows.bat
echo ===================================================================
echo.
pause
exit /b 0

:RUN_DIAG
cd /d "%~dp0backend"
call .venv\Scripts\activate.bat
python verify_gpu.py
pause
exit /b 0

:STOP_SERVERS
call stop_windows.bat
exit /b 0
