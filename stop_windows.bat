@echo off
setlocal enabledelayedexpansion
title Stop Transcriber Servers

echo ===================================================================
echo              STOPPING TRANSCRIBER WINDOWS SERVERS                  
echo ===================================================================
echo.

echo [INFO] Terminating backend processes on port 8000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING 2^>nul') do (
    echo   Stopping process PID %%a ...
    taskkill /F /PID %%a >nul 2>&1
)

echo [INFO] Terminating frontend processes on port 3000...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING 2^>nul') do (
    echo   Stopping process PID %%a ...
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo ===================================================================
echo  [SUCCESS] All Transcriber processes stopped. Ports freed!
echo ===================================================================
echo.
timeout /t 2 >nul
