@echo off
chcp 65001 >nul
cd /d "%~dp0"
title TestHub Stop

REM ============================================
REM   TestHub 停止服务
REM   停止：后端 / 前端 / Django-Q2 集群 / 定时任务调度器
REM   不停止：MySQL / Redis（如需停止请手动关闭）
REM ============================================

set PYTHON=%~dp0venv\Scripts\python.exe
if not exist "%PYTHON%" set PYTHON=python

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

"%PYTHON%" "%~dp0start_all.py" --stop %*

pause
