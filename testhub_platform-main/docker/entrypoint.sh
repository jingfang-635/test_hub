#!/bin/sh
set -e

cd /app

# 容器内默认连接 compose 服务名（可被 .env 覆盖）
DB_HOST="${DB_HOST:-mysql}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_NAME="${DB_NAME:-testhub}"

wait_for_mysql() {
  echo "[entrypoint] 等待 MySQL (${DB_HOST}:${DB_PORT})..."
  i=0
  while [ "$i" -lt 60 ]; do
    if python - <<'PY' 2>/dev/null; then
import os
import pymysql

conn = pymysql.connect(
    host=os.environ["DB_HOST"],
    port=int(os.environ.get("DB_PORT", "3306")),
    user=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    database=os.environ["DB_NAME"],
    connect_timeout=3,
)
conn.close()
PY
      echo "[entrypoint] MySQL 已就绪"
      return 0
    fi
    i=$((i + 1))
    sleep 2
  done
  echo "[entrypoint] MySQL 连接超时"
  exit 1
}

run_migrate_and_init() {
  echo "[entrypoint] 执行数据库迁移..."
  python backend/manage.py migrate --noinput

  echo "[entrypoint] 初始化 UI 定位策略..."
  python backend/manage.py init_locator_strategies || true

  echo "[entrypoint] 初始化 APP 组件库..."
  python backend/manage.py load_component_pack || true

  echo "[entrypoint] 收集静态文件..."
  python backend/manage.py collectstatic --noinput || true

  if [ -n "${DJANGO_SUPERUSER_USERNAME:-}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]; then
    echo "[entrypoint] 创建管理员账号（若不存在）..."
    python backend/manage.py createsuperuser --noinput 2>/dev/null || true
  fi
}

wait_for_backend() {
  echo "[entrypoint] 等待后端 API..."
  i=0
  while [ "$i" -lt 90 ]; do
    if curl -sf "http://backend:8000/api/docs/" >/dev/null 2>&1; then
      echo "[entrypoint] 后端已就绪"
      return 0
    fi
    i=$((i + 1))
    sleep 2
  done
  echo "[entrypoint] 后端启动超时"
  exit 1
}

export DB_HOST DB_PORT DB_USER DB_PASSWORD DB_NAME

case "${1:-web}" in
  web)
    wait_for_mysql
    run_migrate_and_init
    echo "[entrypoint] 启动 Uvicorn ASGI..."
    exec python start_backend.py --host 0.0.0.0 --port 8000
    ;;
  qcluster)
    wait_for_backend
    echo "[entrypoint] 启动 Django-Q2 任务队列..."
    exec python backend/manage.py qcluster
    ;;
  scheduler)
    wait_for_backend
    echo "[entrypoint] 启动定时任务调度器..."
    exec python backend/manage.py run_all_scheduled_tasks
    ;;
  migrate)
    wait_for_mysql
    run_migrate_and_init
    ;;
  *)
    exec "$@"
    ;;
esac
