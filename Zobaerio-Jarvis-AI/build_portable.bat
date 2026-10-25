@echo off
setlocal
cd /d "%~dp0"
title Build J.A.R.V.I.S Windows Portable Package

where py >nul 2>nul
if errorlevel 1 (
  echo Python Launcher was not found. Install Python 3.12 x64 first.
  exit /b 1
)
py -3.12 --version >nul 2>nul
if errorlevel 1 (
  echo Python 3.12 x64 is required to build this package.
  exit /b 1
)

if exist ".packaging-venv\Scripts\python.exe" (
  ".packaging-venv\Scripts\python.exe" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3,12) else 1)" >nul 2>nul
  if errorlevel 1 (
    echo Removing a packaging environment from a different Python version...
    rmdir /s /q ".packaging-venv"
  )
)
if not exist ".packaging-venv\Scripts\python.exe" (
  echo [1/7] Creating an isolated packaging environment...
  py -3.12 -m venv .packaging-venv
  if errorlevel 1 goto failed
)

echo [2/7] Updating packaging tools...
".packaging-venv\Scripts\python.exe" -m pip install --upgrade pip wheel
if errorlevel 1 goto failed

echo [3/7] Installing runtime and packaging dependencies...
".packaging-venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".packaging-venv\Scripts\python.exe" -m pip install "PyInstaller>=6.10,<7"
if errorlevel 1 goto failed

echo [4/7] Generating the branded Windows icon...
".packaging-venv\Scripts\python.exe" -m jarvis.branding
if errorlevel 1 goto failed
if not exist "build" mkdir "build"
copy /Y "%APPDATA%\Zobaerio\Jarvis\jarvis.ico" "build\jarvis.ico" >nul
if errorlevel 1 (
  echo Could not find the generated J.A.R.V.I.S icon in %%APPDATA%%.
  goto failed
)

echo [5/7] Building the standalone application folder...
if exist "dist\JARVIS" rmdir /s /q "dist\JARVIS"
".packaging-venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean "JARVIS.spec"
if errorlevel 1 goto failed
if not exist "dist\JARVIS\JARVIS.exe" (
  echo PyInstaller did not create dist\JARVIS\JARVIS.exe.
  goto failed
)

echo [6/7] Writing portable package version metadata...
".packaging-venv\Scripts\python.exe" -c "import json, platform; from pathlib import Path; from jarvis.version import APP_NAME, APP_VERSION; data={'app_name': APP_NAME, 'app_version': APP_VERSION, 'package_type': 'unsigned-portable-folder', 'python_version': platform.python_version(), 'architecture': platform.machine()}; Path('dist/JARVIS/version.json').write_text(json.dumps(data, indent=2) + chr(10), encoding='utf-8')"
if errorlevel 1 goto failed

echo [7/7] Creating the portable ZIP...
".packaging-venv\Scripts\python.exe" -c "from pathlib import Path; p=Path('dist/JARVIS-Windows-Portable.zip'); p.unlink(missing_ok=True)"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Compress-Archive -Path 'dist\JARVIS' -DestinationPath 'dist\JARVIS-Windows-Portable.zip' -Force"
if errorlevel 1 goto failed

echo.
echo Build succeeded:
echo   dist\JARVIS\JARVIS.exe
echo   dist\JARVIS-Windows-Portable.zip
echo.
echo This package is unsigned. Review the release notes before distributing it.
exit /b 0

:failed
echo.
echo Portable package build failed. Review the error above.
echo Please review the error above.
exit /b 1
