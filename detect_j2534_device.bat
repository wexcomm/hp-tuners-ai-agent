@echo off
REM Universal J2534 Device Detector
REM Automatically finds any J2534 PassThru device on your system

cd /d "%~dp0\skills\j2534_passthru\device_configs\generic"
python universal_detector.py
pause
