@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   TestHub Docker 一键启动（本机构建）
echo ============================================

if not exist ".env" (
  echo [提示] 未找到 .env，从模板复制...
  copy /Y .env.docker.example .env
  echo.
  echo 请编辑 .env 修改 DB_PASSWORD、SECRET_KEY、管理员密码后重新运行。
  echo 按任意键打开 .env ...
  pause >nul
  notepad .env
)

docker compose version >nul 2>&1
if errorlevel 1 (
  echo [错误] 未检测到 Docker，请先安装 Docker Desktop 并确保已启动。
  pause
  exit /b 1
)

echo.
echo 开始构建并启动（首次约 10~30 分钟，取决于网络）...
docker compose up -d --build

if errorlevel 1 (
  echo [错误] 启动失败，请查看上方日志。
  pause
  exit /b 1
)

echo.
echo ============================================
echo   启动完成
echo   访问: http://localhost
echo   API 文档: http://localhost/api/docs/
echo   管理后台: http://localhost/admin/
echo.
echo   查看日志: docker compose logs -f
echo   停止服务: docker compose down
echo ============================================
pause
