@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM Read backend port from config.yaml
set BACKEND_PORT=
for /f "tokens=2 delims=: " %%p in ('findstr /b "BACKEND_PORT" ..\config.yaml 2^>nul') do set BACKEND_PORT=%%p
if "%BACKEND_PORT%"=="" set BACKEND_PORT=8000

REM Python path (no venv activation needed)
set PYTHON=..\venv\Scripts\python.exe

echo ============================================
echo   TestHub Backend Start
echo   Django Server + Django-Q2 + Scheduler
echo   Backend Port: %BACKEND_PORT%
echo ============================================

REM Start Django-Q2 cluster (separate window)
start "TestHub-QCluster" cmd /k "%PYTHON% manage.py qcluster"

REM Start scheduler (separate window)
start "TestHub-Scheduler" cmd /k "%PYTHON% manage.py run_all_scheduled_tasks"

REM Start Django dev server (current window)
%PYTHON% manage.py runserver 0.0.0.0:%BACKEND_PORT%
pause
