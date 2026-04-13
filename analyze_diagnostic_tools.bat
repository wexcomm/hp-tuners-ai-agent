@echo off
REM Analyze Diagnostic Tools
REM Scans for and analyzes J2534 diagnostic software

cd /d "%~dp0\skills\j2534_passthru\device_configs\generic"
python diagnostic_tool_analyzer.py --scan-all
pause
