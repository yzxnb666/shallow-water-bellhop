@echo off
setlocal
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] python not found. Activate the environment first:
    echo         conda activate underwater
    exit /b 1
)
python "%~dp0scripts\shallow_water_bellhop.py" %*
