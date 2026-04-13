@echo off
REM Analyze TOPDON RLink X3 Installation

cd /d "%~dp0\skills\j2534_passthru\device_configs"
python topdon_analyzer.py
pause
