@echo off
setlocal
cd /d "%~dp0"
title J.A.R.V.I.S Desktop AI
if not exist ".venv\Scripts\python.exe" (
  echo Please run install.bat first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" app.py
if errorlevel 1 (
  echo.
  echo J.A.R.V.I.S stopped with an error. Copy the message above to troubleshoot.
  pause
)
