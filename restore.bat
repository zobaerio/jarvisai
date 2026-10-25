@echo off
setlocal
cd /d "%~dp0"
title Restore J.A.R.V.I.S Desktop AI Package
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $dir=Join-Path $PSScriptRoot 'bundle'; $parts=Get-ChildItem -LiteralPath $dir -Filter 'jarvis-*.b64' | Sort-Object Name; if(-not $parts){throw 'Bundle parts not found.'}; $encoded=(($parts | ForEach-Object { (Get-Content -LiteralPath $_.FullName -Raw).Trim() }) -join ''); $zip=Join-Path $PSScriptRoot 'JARVIS-Windows11-v1.2.0.zip'; [IO.File]::WriteAllBytes($zip,[Convert]::FromBase64String($encoded)); $dest=Join-Path $PSScriptRoot 'restored'; if(Test-Path $dest){Remove-Item $dest -Recurse -Force}; Expand-Archive -LiteralPath $zip -DestinationPath $dest -Force; Write-Host 'Restored successfully:' $zip; Write-Host 'Project folder:' (Join-Path $dest 'Zobaerio-Jarvis-AI')"
if errorlevel 1 (
 echo Restore failed. Please check that every bundle part is present.
 pause
 exit /b 1
)
echo.
echo Done. Open restoredZobaerio-Jarvis-AI and run install.bat.
pause
