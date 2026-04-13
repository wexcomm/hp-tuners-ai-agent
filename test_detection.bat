@echo off
REM Test J2534 Device Detection
echo ============================================================
echo  J2534 DEVICE DETECTION TEST
echo ============================================================
echo.
echo This will test detection of your TOPDON RLink X3 and any
echo other J2534 devices on your system.
echo.
pause
echo.
echo [TEST 1] Universal Device Detector
echo ------------------------------------------------------------
cd /d "%~dp0\skills\j2534_passthru\device_configs\generic"
python universal_detector.py
echo.
echo.
echo [TEST 2] TOPDON RLink X3 Specific
echo ------------------------------------------------------------
cd /d "%~dp0\skills\j2534_passthru\device_configs"
python -c "from topdon_rlink import TopdonRLinkX3Device; d=TopdonRLinkX3Device(); info=d.get_device_info(); print('Device:', info['name']); print('DLL Found:', info['dll_found']); print('DLL Path:', info['dll_path']); print('Connected:', info['connected'])"
echo.
echo.
echo [TEST 3] Check Python Imports
echo ------------------------------------------------------------
cd /d "%~dp0"
python -c "from skills.j2534_passthru import J2534PassThru; print('J2534PassThru: OK')"
python -c "from skills.j2534_passthru.device_configs.topdon_rlink import TopdonRLinkX3Device; print('TOPDON Module: OK')"
python -c "from skills.j2534_passthru.device_configs.generic import detect_any_device; print('Universal Detector: OK')"
echo.
echo ============================================================
echo  TEST COMPLETE
echo ============================================================
pause
