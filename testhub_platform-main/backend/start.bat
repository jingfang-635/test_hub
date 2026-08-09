@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM Read backend port from config.yaml
set BACKEND_PORT=
for /f "tokens=2 delims=: " %%p in ('findstr /b "BACKEND_PORT" ..\config.yaml 2^>nul') do set BACKEND_PORT=%%p
if "%BACKEND_PORT%"=="" set BACKEND_PORT=8000

REM Python path (absolute, survives cd)
set PYTHON=%~dp0..\venv\Scripts\python.exe
set ROOT=%~dp0..

echo ============================================
echo   TestHub Backend Start
echo   Uvicorn ASGI + Django-Q2 + Scheduler
echo   (HTTP + SSE + WebSocket)
echo   Backend Port: %BACKEND_PORT%
echo ============================================

REM Start Django-Q2 cluster (separate window)
start "TestHub-QCluster" cmd /k "cd /d %~dp0 && %PYTHON% manage.py qcluster"

REM Start scheduler (separate window)
start "TestHub-Scheduler" cmd /k "cd /d %~dp0 && %PYTHON% manage.py run_all_scheduled_tasks"

REM Start Uvicorn ASGI (current window)
cd /d "%ROOT%"
%PYTHON% start_backend.py --port %BACKEND_PORT%
pause
