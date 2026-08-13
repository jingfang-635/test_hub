#!/usr/bin/env bash
# 启动 Playwright codegen 录制。
# 用法: ./scripts/start-codegen.sh "<URL>" "<scenario>" [python|typescript] [--save-storage|--load-storage]
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

URL="${1:-}"
SCENARIO="${2:-}"
LANG="${3:-python}"
STORAGE_FLAG="${4:-}"

if [[ -z "$URL" || -z "$SCENARIO" ]]; then
  echo "用法: $0 \"<URL>\" \"<scenario>\" [python|typescript] [--save-storage|--load-storage]"
  exit 1
fi

mkdir -p tests/recorded tests/fixtures
echo "$LANG" > .codegen-lang

STORAGE_ARGS=()
case "$STORAGE_FLAG" in
  --save-storage)
    STORAGE_ARGS=(--save-storage=tests/fixtures/auth.json)
    ;;
  --load-storage)
    STORAGE_ARGS=(--load-storage=tests/fixtures/auth.json)
    ;;
  "")
    ;;
  *)
    echo "未知参数: $STORAGE_FLAG（仅支持 --save-storage / --load-storage）"
    exit 1
    ;;
esac

if [[ "$LANG" == "typescript" || "$LANG" == "ts" ]]; then
  OUT="tests/recorded/${SCENARIO}.spec.ts"
  TARGET="javascript"
else
  OUT="tests/recorded/${SCENARIO}.py"
  TARGET="python-pytest"
  LANG="python"
  echo "python" > .codegen-lang
fi

echo "Codegen → ${OUT} (target=${TARGET})"
echo "请在打开的浏览器中完成流程；结束后回复「录制完成」。"
if ((${#STORAGE_ARGS[@]})); then
  exec npx playwright codegen "$URL" -o "$OUT" --target "$TARGET" "${STORAGE_ARGS[@]}"
else
  exec npx playwright codegen "$URL" -o "$OUT" --target "$TARGET"
fi
