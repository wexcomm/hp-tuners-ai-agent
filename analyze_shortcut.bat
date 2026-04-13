@echo off
REM Analyze Specific Diagnostic Tool from Shortcut

cd /d "%~dp0\skills\j2534_passthru\device_configs\generic"

if "%~1"=="" (
    echo Usage: analyze_shortcut.bat "path\to\shortcut.lnk"
    echo.
    echo Example:
    echo   analyze_shortcut.bat "C:\Users\%%USERNAME%%\OneDrive\Desktop\Generic Diagnostic Tool - Shortcut.lnk"
    pause
    exit /b 1
)

python diagnostic_tool_analyzer.py --tool-path "%~1"
pause
