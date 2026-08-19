@echo off
echo Starting Hercules KPI Application...
cd /d "%~dp0"

REM Set MOCK_SAP_MODE to true to use demo server, false for production SAP
set MOCK_SAP_MODE=true

echo MOCK_SAP_MODE is set to: %MOCK_SAP_MODE%
start "" "app\app.exe"
echo Waiting for application to start...
timeout /t 5 /nobreak >nul
echo Opening Hercules KPI in browser...
start "" "http://127.0.0.1:5000"
echo Hercules KPI is now running!
echo You can close this window.
pause
