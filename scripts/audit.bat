@echo off
REM Codex — sanity check (read-only). Safe to run anytime.
cd /d "%~dp0\.."
py audit.py
echo.
echo --- done. Press any key to close. ---
pause >nul
