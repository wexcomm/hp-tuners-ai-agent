@echo off
REM Live Tuning Bridge Launcher for Windows

echo ========================================
echo   Live Tuning Bridge for VCM Suite
echo ========================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Check if watchdog is installed
python -c "import watchdog" >nul 2>&1
if errorlevel 1 (
    echo Installing required dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install dependencies
        pause
        exit /b 1
    )
)

REM Show instructions first
echo.
python src/live_tuning_bridge.py --instructions

echo.
echo ========================================
echo Press any key to start the bridge...
echo ========================================
pause >nul

REM Start the bridge
cls
python src/live_tuning_bridge.py

if errorlevel 1 (
    echo.
    echo Bridge exited with error
    pause
)
