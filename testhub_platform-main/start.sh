#!/bin/bash
cd "$(dirname "$0")"

# 从 config.yaml 读取端口配置
BACKEND_PORT=$(grep "^BACKEND_PORT" config.yaml 2>/dev/null | awk -F': ' '{print $2}' | tr -d ' ')
BACKEND_PORT=${BACKEND_PORT:-8000}

FRONTEND_PORT=$(grep "^FRONTEND_PORT" config.yaml 2>/dev/null | awk -F': ' '{print $2}' | tr -d ' ')
FRONTEND_PORT=${FRONTEND_PORT:-3000}

# venv python 路径（无需激活虚拟环境，直接调用 venv 内的 python）
PYTHON="$(dirname "$0")/venv/bin/python"

echo "============================================"
echo "  TestHub 一键启动"
echo "  前端端口: ${FRONTEND_PORT}"
echo "  后端端口: ${BACKEND_PORT}"
echo "  Django Server + Django-Q2 + Scheduler"
echo "============================================"

# 1. 启动前端（后台）
(cd frontend && npm run dev) &
FRONTEND_PID=$!
echo "Frontend started (PID: ${FRONTEND_PID})"

# 2. 启动聚合后台
#    a) Django-Q2 集群（后台）
(cd backend && "$PYTHON" manage.py qcluster) &
QCLUSTER_PID=$!
echo "Django-Q2 Cluster started (PID: ${QCLUSTER_PID})"

#    b) 定时任务调度器（后台）
(cd backend && "$PYTHON" manage.py run_all_scheduled_tasks) &
SCHEDULER_PID=$!
echo "Scheduler started (PID: ${SCHEDULER_PID})"

#    c) Django 开发服务器（前台）
trap "kill ${FRONTEND_PID} ${QCLUSTER_PID} ${SCHEDULER_PID} 2>/dev/null" EXIT
(cd backend && "$PYTHON" manage.py runserver 0.0.0.0:${BACKEND_PORT})
