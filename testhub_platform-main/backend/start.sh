#!/bin/bash
cd "$(dirname "$0")"

# 从 config.yaml 读取后端端口
BACKEND_PORT=$(grep "^BACKEND_PORT" ../config.yaml 2>/dev/null | awk -F': ' '{print $2}' | tr -d ' ')
BACKEND_PORT=${BACKEND_PORT:-8000}

# venv python 路径（绝对路径，避免后续 cd 后失效）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON="${ROOT_DIR}/venv/bin/python"

echo "============================================"
echo "  TestHub 聚合后台启动"
echo "  Uvicorn ASGI + Django-Q2 + Scheduler"
echo "  (HTTP + SSE + WebSocket)"
echo "  Backend Port: ${BACKEND_PORT}"
echo "============================================"

# 启动 Django-Q2 集群（后台）
(cd "${SCRIPT_DIR}" && "$PYTHON" manage.py qcluster) &
QCLUSTER_PID=$!
echo "Django-Q2 Cluster started (PID: ${QCLUSTER_PID})"

# 启动定时任务调度器（后台）
(cd "${SCRIPT_DIR}" && "$PYTHON" manage.py run_all_scheduled_tasks) &
SCHEDULER_PID=$!
echo "Scheduler started (PID: ${SCHEDULER_PID})"

# 启动 Uvicorn ASGI（前台）
trap "kill ${QCLUSTER_PID} ${SCHEDULER_PID} 2>/dev/null" EXIT
cd "${ROOT_DIR}"
"$PYTHON" start_backend.py --port "${BACKEND_PORT}"
