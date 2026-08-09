#!/bin/bash
cd "$(dirname "$0")"

# 从 config.yaml 读取后端端口
BACKEND_PORT=$(grep "^BACKEND_PORT" ../config.yaml 2>/dev/null | awk -F': ' '{print $2}' | tr -d ' ')
BACKEND_PORT=${BACKEND_PORT:-8000}

# venv python 路径（无需激活虚拟环境，直接调用 venv 内的 python）
PYTHON="../venv/bin/python"

echo "============================================"
echo "  TestHub 聚合后台启动"
echo "  Django Server + Django-Q2 + Scheduler"
echo "  Backend Port: ${BACKEND_PORT}"
echo "============================================"

# 启动 Django-Q2 集群（后台）
"$PYTHON" manage.py qcluster &
QCLUSTER_PID=$!
echo "Django-Q2 Cluster started (PID: ${QCLUSTER_PID})"

# 启动定时任务调度器（后台）
"$PYTHON" manage.py run_all_scheduled_tasks &
SCHEDULER_PID=$!
echo "Scheduler started (PID: ${SCHEDULER_PID})"

# 启动 Django 开发服务器（前台）
trap "kill ${QCLUSTER_PID} ${SCHEDULER_PID} 2>/dev/null" EXIT
"$PYTHON" manage.py runserver 0.0.0.0:${BACKEND_PORT}
