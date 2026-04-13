@echo off
REM J2534 PassThru Launcher

cd /d "%~dp0\skills\j2534_passthru"
python __main__.py %*
