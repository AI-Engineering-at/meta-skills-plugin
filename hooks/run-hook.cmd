@echo off
REM Windows wrapper for bash hooks
set "SCRIPT_DIR=%~dp0"
bash "%SCRIPT_DIR%%1.sh" 2>nul
if errorlevel 1 (
    python3 -c "pass" 2>nul
)
