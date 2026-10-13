@echo off
setlocal

echo ===================================================================
echo   STARTING TRANSCRIBER BACKEND (WINDOWS CPU-WISE OPTIMIZED)         
echo   ML Engine: CPU (AVX2/INT8) | GPU: Free for Studio Video & UI      
echo ===================================================================

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup.bat first to configure Python and install CUDA dependencies.
    echo.
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo [INFO] Environment active. Launching FastAPI server on http://localhost:8000 ...
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
