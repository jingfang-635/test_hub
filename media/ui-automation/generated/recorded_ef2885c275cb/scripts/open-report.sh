#!/usr/bin/env bash
# 启动带 CORS 的本地静态服务并打开 pytest-html 报告。
# 报告内 Trace 链接依赖该服务；需保持运行。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${REPORT_PORT:-9323}"
REPORT="${ROOT}/reports/report.html"

if [[ ! -f "$REPORT" ]]; then
  echo "未找到 ${REPORT}，请先运行: pytest"
  exit 1
fi

cd "$ROOT"
# 释放旧端口
if lsof -tiTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  lsof -tiTCP:"$PORT" -sTCP:LISTEN | xargs kill 2>/dev/null || true
  sleep 0.3
fi

echo "Serving ${ROOT} at http://127.0.0.1:${PORT} (CORS enabled)"
echo "Report: http://127.0.0.1:${PORT}/reports/report.html"
echo "在报告中点击「Open Trace Viewer」；若浏览器提示 Local Network Access，请允许。"

python3 "${ROOT}/scripts/serve_report.py" --port "$PORT" --root "$ROOT" \
  >/tmp/playwright-codegen-report-server.log 2>&1 &
SERVER_PID=$!
trap 'kill "$SERVER_PID" 2>/dev/null || true' EXIT

sleep 0.5
if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "服务启动失败，见 /tmp/playwright-codegen-report-server.log"
  cat /tmp/playwright-codegen-report-server.log || true
  exit 1
fi

# 冒烟：trace 目录可访问
if [[ -d "${ROOT}/test-results" ]]; then
  curl -s -o /dev/null -w "test-results HTTP %{http_code}\n" \
    -H "Origin: https://trace.playwright.dev" \
    "http://127.0.0.1:${PORT}/test-results/" || true
fi

if command -v open >/dev/null 2>&1; then
  open "http://127.0.0.1:${PORT}/reports/report.html"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://127.0.0.1:${PORT}/reports/report.html"
else
  echo "请手动打开: http://127.0.0.1:${PORT}/reports/report.html"
fi

wait "$SERVER_PID"
