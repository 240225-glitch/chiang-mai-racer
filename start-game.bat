@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on PATH.
  echo Install Python, or serve this folder with any static file server.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "if (-not (Get-NetTCPConnection -LocalPort 8080 -State Listen -ErrorAction SilentlyContinue)) { Start-Process -FilePath python -ArgumentList '-m','http.server','8080','--bind','127.0.0.1' -WorkingDirectory (Get-Location).Path -WindowStyle Hidden; Start-Sleep -Seconds 1 }"

start "" "http://127.0.0.1:8080/"
endlocal
