@echo off
REM Codex — quick refresh (skips long Punk Records + SBS image scrapes).
cd /d "%~dp0\.."
py refresh.py --quick --parallel 2
echo.
echo --- done. Press any key to close. ---
pause >nul
