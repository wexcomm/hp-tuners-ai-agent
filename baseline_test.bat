@echo off
echo ============================================================
echo  BASELINE TEST - Before Code Fixes
echo ============================================================
echo.
echo This will test current functionality to establish a baseline.
echo.
pause

cd /d "%~dp0"

echo.
echo [TEST 1] Python Environment
echo ------------------------------------------------------------
python --version
echo.

echo [TEST 2] Import Core Modules
echo ------------------------------------------------------------
python -c "from skills.hpt_converter import HPTConverter; print('HPTConverter: OK')" 2>&1
python -c "from skills.j2534_passthru import J2534PassThru; print('J2534PassThru: OK')" 2>&1
python -c "from src.live_tuning_bridge import LiveTuningBridge; print('LiveTuningBridge: OK')" 2>&1
echo.

echo [TEST 3] TOPDON RLink Detection
echo ------------------------------------------------------------
python -c "from skills.j2534_passthru.device_configs.topdon_rlink import TopdonRLinkX3Device; d=TopdonRLinkX3Device(); print('DLL:', d.find_dll() or 'NOT FOUND')" 2>&1
echo.

echo [TEST 4] Checksum Validator
echo ------------------------------------------------------------
python -c "from skills.hpt_converter import ChecksumValidator; v=ChecksumValidator('GM_E37'); print('Validator: OK')" 2>&1
echo.

echo [TEST 5] HPT Builder (Critical - may show duplicate method issue)
echo ------------------------------------------------------------
python -c "from skills.hpt_converter import HPTBuilder; b=HPTBuilder('GM_E37', 'TEST'); print('Builder: OK')" 2>&1
echo.

echo [TEST 6] File Conversions
echo ------------------------------------------------------------
python -c "
from skills.hpt_converter import HPTConverter
c = HPTConverter()
print('Platforms:', c.get_supported_platforms())
" 2>&1
echo.

echo ============================================================
echo  BASELINE TEST COMPLETE
echo ============================================================
echo.
echo Save this output! We'll compare after fixes.
pause
