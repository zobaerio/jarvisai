@echo off
setlocal
cd /d "%~dp0"
title Restore J.A.R.V.I.S Desktop AI v1.2.1
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $root=$PSScriptRoot; $names=@(); 1..14 | ForEach-Object { $names += ('jarvis-v1.2.1.part{0:D2}.b64' -f $_) }; $names += 'jarvis-v1.2.1.part15.b64'; $names += 'jarvis-v1.2.1.part15b.b64'; $names += 'jarvis-v1.2.1.part16.b64'; $encoded=''; foreach($name in $names){ $path=Join-Path (Join-Path $root 'bundle') $name; if(-not (Test-Path -LiteralPath $path)){ throw ('Missing archive part: '+$name) }; $encoded += (Get-Content -LiteralPath $path -Raw).Trim() }; if($encoded.Length -ne 122808){ throw ('Archive data length mismatch: expected 122808, found '+$encoded.Length) }; $zip=Join-Path $root 'JARVIS-Windows11-v1.2.1.zip'; [IO.File]::WriteAllBytes($zip,[Convert]::FromBase64String($encoded)); $hash=(Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant(); if($hash -ne '766aeb1fdffbd981e91742169f146de9091096468e199d3726f7313524b695d6'){ throw ('ZIP checksum mismatch. Expected 766aeb1fdffbd981e91742169f146de9091096468e199d3726f7313524b695d6 but got '+$hash) }; $dest=Join-Path $root 'restored'; if(Test-Path -LiteralPath $dest){ Remove-Item -LiteralPath $dest -Recurse -Force }; Expand-Archive -LiteralPath $zip -DestinationPath $dest -Force; Write-Host 'Restored and checksum verified:' $zip; Write-Host 'Project folder:' (Join-Path $dest 'Zobaerio-Jarvis-AI')"
if errorlevel 1 (
  echo.
  echo Restore failed. Ensure you downloaded the whole GitHub repository ZIP and did not omit archive parts.
  pause
  exit /b 1
)
echo.
echo Package restored. Open restoredZobaerio-Jarvis-AI and follow README_BN.md.
pause
