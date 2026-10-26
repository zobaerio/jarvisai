@echo off
setlocal
cd /d "%~dp0"
title Install ORVIX AI Desktop Assistant

echo ====================================================
echo   ORVIX AI Desktop Assistant - Windows 11 Setup
echo ====================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher was not found.
  echo Install Python 3.12 x64 from https://www.python.org/downloads/release/python-31210/
  echo During setup, select "Add python.exe to PATH".
  pause
  exit /b 1
)

py -3.12 --version >nul 2>nul
if errorlevel 1 (
  echo Python 3.12 was not found. This project uses Python 3.12 for better compatibility.
  echo Install Python 3.12 x64 from https://www.python.org/downloads/release/python-31210/
  echo Close and reopen VS Code/Terminal after installation, then run install.bat again.
  pause
  exit /b 1
)

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)" >nul 2>nul
  if errorlevel 1 (
    echo Existing .venv is not Python 3.12. Rebuilding this project-managed environment...
    rmdir /s /q ".venv"
  )
)

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Creating a Python 3.12 private environment...
  py -3.12 -m venv .venv
  if errorlevel 1 goto failed
) else (
  echo [1/5] Using existing Python 3.12 environment...
)

echo [2/5] Updating pip and wheel...
".venv\Scripts\python.exe" -m pip install --upgrade pip wheel
if errorlevel 1 goto failed

echo [3/5] Installing voice and app dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo Dependency install did not complete.
  echo If the error mentions PyAudio, confirm you installed Python 3.12 x64, not Python 3.14 or 32-bit Python.
  goto failed
)

echo [4/5] Checking Python files...
".venv\Scripts\python.exe" -m compileall -q app.py jarvis tests
if errorlevel 1 goto failed

echo [5/6] Creating the ORVIX AI logo and Windows app icon...
".venv\Scripts\python.exe" -m jarvis.branding
if errorlevel 1 goto failed

echo [6/6] Creating a Desktop shortcut with the app icon (if Windows allows it)...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([IO.Path]::Combine([Environment]::GetFolderPath('Desktop'),'ORVIX AI Desktop.lnk')); $s.TargetPath=(Join-Path (Get-Location).Path 'run.bat'); $s.WorkingDirectory=(Get-Location).Path; $i=Join-Path $env:APPDATA 'Zobaerio\Jarvis\jarvis.ico'; if(Test-Path $i){$s.IconLocation=$i}; $s.Save()" >nul 2>nul

echo.
echo Setup complete. Double-click run.bat or the Desktop shortcut to start ORVIX AI.
echo For advanced AI reasoning, configure an AI model from Settings after the app opens.
pause
exit /b 0

:failed
echo.
echo SETUP FAILED. Copy the full error text and share it for troubleshooting.
pause
exit /b 1
