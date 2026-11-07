@echo off
TITLE Nusuk Master HQ Dashboard
echo =======================================================
echo 🕋 Starting Nusuk Master HQ Dashboard (Windows)...
echo =======================================================

where adb >nul 2>nul
if %errorlevel% neq 0 (
    echo ⚠️ Warning: 'adb' command was not found in your PATH.
    echo    Please ensure Android SDK Platform Tools is added to your PATH.
    echo.
)

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ Error: Python is not found. Please install Python 3.8+ and check "Add Python to PATH".
    pause
    exit /b 1
)

echo 🔍 Checking connected Android devices...
adb devices

echo.
echo 🚀 Launching Master HQ Web Dashboard on http://localhost:5050 ...
echo 👉 Press Ctrl+C to stop.
echo =======================================================

start http://localhost:5050
python dashboard_server.py
pause
