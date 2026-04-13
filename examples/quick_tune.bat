@echo off
REM Quick Tune Generator for Windows
REM Usage: quick_tune.bat [VIN] [OCTANE]

echo ========================================
echo   Quick Tune Generator
echo ========================================
echo.

REM Default values
set VIN=%1
set OCTANE=%2

if "%VIN%"=="" (
    echo Usage: quick_tune.bat [VIN] [OCTANE]
    echo Example: quick_tune.bat 2G1WB5E37D1157819 93
    echo.
    set /p VIN="Enter VIN: "
)

if "%OCTANE%"=="" (
    set /p OCTANE="Enter octane (87/89/91/93) [93]: "
    if "%OCTANE%"=="" set OCTANE=93
)

echo.
echo Generating Stage 1 tune for %VIN% with %OCTANE% octane...
echo.

python src/live_tuning_bridge.py --quick %VIN% --octane %OCTANE%

if errorlevel 1 (
    echo.
    echo ERROR: Failed to generate tune
    pause
    exit /b 1
)

echo.
echo ========================================
echo Tune generation complete!
echo.
echo Next steps:
echo 1. Open VCM Editor
echo 2. Load your stock tune
echo 3. Copy values from generated CSV files
echo 4. Paste into appropriate tables
echo 5. Save and flash
echo ========================================
pause
