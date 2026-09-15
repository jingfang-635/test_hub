@echo off
chcp 65001 >nul
cd /d "%~dp0"
title TestHub Backend

REM ============================================
REM   TestHub 后端启动（单窗口版）
REM   Django-Q2 集群 + 定时任务调度器 + Uvicorn
REM   全部收敛到当前窗口，Ctrl+C 一键全停
REM   详细日志：..\logs\start\<服务名>.log
REM ============================================

REM Python 路径（绝对路径，不受 cd 影响）
set PYTHON=%~dp0..\venv\Scripts\python.exe
if not exist "%PYTHON%" set PYTHON=python

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

REM 不管理 MySQL / Redis、不启动前端：只跑后端相关服务
"%PYTHON%" "%~dp0..\start_all.py" --no-infra --no-frontend %*

if "%errorlevel%"=="0" exit
if "%errorlevel%"=="130" exit

echo.
echo [启动器异常退出] errorlevel=%errorlevel%
echo 请查看上方错误信息，或 ..\logs\start\ 下的服务日志。
echo.
pause
