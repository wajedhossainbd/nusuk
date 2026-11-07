#!/bin/bash
# ========================================================
# Nusuk Master HQ - One-Click Launcher (macOS & Linux)
# ========================================================

echo ""
echo "======================================================="
echo "🕋 Starting Nusuk Master HQ Dashboard..."
echo "======================================================="

# Check ADB
if ! command -v adb &> /dev/null; then
    echo "⚠️ Warning: 'adb' command was not found in your PATH."
    echo "   Please install Android Platform Tools:"
    echo "   macOS:   brew install android-platform-tools"
    echo "   Ubuntu:  sudo apt install adb"
    echo ""
fi

# Detect Python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    if command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo "❌ Error: Python 3 is not installed. Please install Python 3.8+."
        exit 1
    fi
fi

# Check connected devices
echo "🔍 Checking connected Android devices via ADB..."
$PYTHON_CMD -c "
import subprocess
try:
    res = subprocess.run(['adb', 'devices'], capture_output=True, text=True)
    devices = [line for line in res.stdout.strip().splitlines()[1:] if 'device' in line]
    if devices:
        print(f'✅ Found {len(devices)} active Android device(s):')
        for d in devices:
            print(f'   📱 {d}')
    else:
        print('⚠️ No active Android device detected yet. You can connect your phone via USB or Wi-Fi anytime.')
except Exception as e:
    print(f'Note: {e}')
"

echo ""
echo "🚀 Launching Master HQ Web Dashboard on http://localhost:5050 ..."
echo "👉 Press Ctrl+C anytime to stop."
echo "======================================================="
echo ""

# Open browser automatically after 1.5s in background
(sleep 1.5 && (open "http://localhost:5050" 2>/dev/null || xdg-open "http://localhost:5050" 2>/dev/null)) &

# Start dashboard server
$PYTHON_CMD dashboard_server.py
