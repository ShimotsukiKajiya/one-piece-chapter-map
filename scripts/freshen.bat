@echo off
REM Codex — invalidate stale wikitext caches (so next refresh re-fetches changes).
cd /d "%~dp0\.."
py freshen.py
echo.
echo --- done. Press any key to close. ---
pause >nul
