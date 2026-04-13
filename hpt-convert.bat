@echo off
REM HPT Converter Launcher

cd /d "%~dp0\skills\hpt_converter"
python __main__.py %*
