@echo off
REM Codex — full pipeline (scrape new data, clean, bake, audit). Local only.
cd /d "%~dp0\.."
py refresh.py --parallel 2
echo.
echo --- done. Press any key to close. ---
pause >nul
