#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "============================================"
echo "  TestHub Docker 一键启动（本机构建）"
echo "============================================"

if [ ! -f .env ]; then
  echo "[提示] 未找到 .env，从模板复制..."
  cp .env.docker.example .env
  echo "请编辑 .env 修改 DB_PASSWORD、SECRET_KEY、管理员密码后重新运行。"
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[错误] 未检测到 Docker，请先安装 Docker 并确保已启动。"
  exit 1
fi

echo ""
echo "开始构建并启动（首次约 10~30 分钟，取决于网络）..."
docker compose up -d --build

echo ""
echo "============================================"
echo "  启动完成"
echo "  访问: http://localhost"
echo "  API 文档: http://localhost/api/docs/"
echo "  管理后台: http://localhost/admin/"
echo ""
echo "  查看日志: docker compose logs -f"
echo "  停止服务: docker compose down"
echo "============================================"
