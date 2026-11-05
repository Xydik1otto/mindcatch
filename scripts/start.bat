@echo off
REM Mindcatch launcher for non-programmers: venv + deps + server + browser.
REM Finds a free port automatically and opens the app in the default browser.
setlocal enabledelayedexpansion
cd /d "%~dp0.."

where python >nul 2>nul
if errorlevel 1 (
  echo [Mindcatch] Python not found. Install it from https://www.python.org/downloads/
  echo and check "Add python.exe to PATH" during installation.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [Mindcatch] First run: creating isolated environment...
  python -m venv .venv
  ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
)

set PORT=8000
netstat -ano | findstr /r "TCP.*:8000 .*LISTENING" >nul 2>nul
if not errorlevel 1 set PORT=8013

echo [Mindcatch] Starting on http://localhost:%PORT% ...
start "" http://localhost:%PORT%
".venv\Scripts\python.exe" -m uvicorn app.main:app --port %PORT%
