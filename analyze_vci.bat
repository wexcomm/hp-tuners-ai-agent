@echo off
REM Analyze Ford VCI Manager Installation

cd /d "%~dp0\skills\j2534_passthru\device_configs"
python vci_analyzer.py
pause
