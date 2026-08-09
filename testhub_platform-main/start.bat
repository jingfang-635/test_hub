@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM Read ports from config.yaml
set BACKEND_PORT=
for /f "tokens=2 delims=: " %%p in ('findstr /b "BACKEND_PORT" config.yaml 2^>nul') do set BACKEND_PORT=%%p
if "%BACKEND_PORT%"=="" set BACKEND_PORT=8000

set FRONTEND_PORT=
for /f "tokens=2 delims=: " %%p in ('findstr /b "FRONTEND_PORT" config.yaml 2^>nul') do set FRONTEND_PORT=%%p
if "%FRONTEND_PORT%"=="" set FRONTEND_PORT=3000

REM Python path (no venv activation needed)
set PYTHON=%~dp0venv\Scripts\python.exe

echo ============================================
echo   TestHub One-Click Start
echo   Frontend Port: %FRONTEND_PORT%
echo   Backend Port: %BACKEND_PORT%
echo   Uvicorn ASGI + Django-Q2 + Scheduler
echo   (HTTP + SSE + WebSocket on one port)
echo ============================================

REM 1. Start frontend (separate window)
start "TestHub-Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

REM 2. Start backend services
REM    a) Django-Q2 cluster (separate window)
start "TestHub-QCluster" cmd /k "cd /d %~dp0backend && %PYTHON% manage.py qcluster"

REM    b) Scheduler (separate window)
start "TestHub-Scheduler" cmd /k "cd /d %~dp0backend && %PYTHON% manage.py run_all_scheduled_tasks"

REM    c) Uvicorn ASGI server (current window) — HTTP/SSE/WebSocket
cd /d %~dp0
%PYTHON% start_backend.py --port %BACKEND_PORT%
pause
