@echo off
REM Codex — full refresh + commit + push to GitHub (publishes to live site).
cd /d "%~dp0\.."
py refresh.py --parallel 2 --push
echo.
echo --- done. Press any key to close. ---
pause >nul
