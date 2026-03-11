@echo off
chcp 65001 >nul
cd /d "%~dp0"

:: Try .exe first (production), then fall back to Python (development)
if exist "dist\Thikr.exe" (
    start "" "dist\Thikr.exe"
) else if exist "Thikr.exe" (
    start "" "Thikr.exe"
) else (
    start "" pythonw thikr.py
)
exit
