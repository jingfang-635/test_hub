@echo off
chcp 65001 >nul
cd /d "%~dp0"
title TestHub Launcher

REM ============================================
REM   TestHub One-Click Start（单窗口版）
REM   MySQL + Redis + 前端 + Q2 集群 + 调度器 + 后端
REM   全部收敛到当前窗口，Ctrl+C 一键全停
REM   详细日志：logs\start\<服务名>.log
REM ============================================

REM Python 路径（无需激活虚拟环境）
set PYTHON=%~dp0venv\Scripts\python.exe
if not exist "%PYTHON%" set PYTHON=python

set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

"%PYTHON%" "%~dp0start_all.py" %*

REM 正常退出（0）或用户 Ctrl+C（130）直接关窗；
REM 异常退出时保留窗口，方便查看错误原因。
if "%errorlevel%"=="0" exit
if "%errorlevel%"=="130" exit

echo.
echo [启动器异常退出] errorlevel=%errorlevel%
echo 请查看上方错误信息，或 logs\start\ 下的服务日志。
echo.
pause
