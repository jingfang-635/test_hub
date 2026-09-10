#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
使用 Uvicorn 启动 Django ASGI 应用。

同一端口同时提供：
- HTTP（REST API）
- SSE（如用例生成流式输出）
- WebSocket（执行进度 / 设备远程投屏控制）

用法（项目根目录）:
  python start_backend.py
  python start_backend.py --port 8000
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def _read_backend_port(default: int = 8000) -> int:
    config_path = ROOT / 'config.yaml'
    if not config_path.exists():
        return default
    try:
        text = config_path.read_text(encoding='utf-8')
        match = re.search(r'^BACKEND_PORT:\s*(\d+)\s*$', text, re.MULTILINE)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return default


def main() -> None:
    parser = argparse.ArgumentParser(description='Start TestHub backend with Uvicorn (HTTP/SSE/WebSocket)')
    parser.add_argument('--host', default='0.0.0.0', help='Bind host (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=None, help='Bind port (default: config.yaml BACKEND_PORT)')
    parser.add_argument('--reload', action='store_true', help='Enable auto-reload (dev only)')
    args = parser.parse_args()

    port = args.port or _read_backend_port(8000)

    # 保证可导入 backend.* 与 backend/config_loader、apps
    backend_dir = ROOT / 'backend'
    for path in (ROOT, backend_dir):
        path_str = str(path)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)
    os.chdir(ROOT)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
    # browser-use 会尝试读取/创建系统级配置目录（~/.config/browseruse），
    # 在受限沙箱/无该目录权限的环境下会失败，这里重定向到项目内目录。
    os.environ.setdefault('BROWSER_USE_CONFIG_DIR', str(ROOT / '.browseruse'))

    try:
        import uvicorn
    except ImportError:
        print('未安装 uvicorn，请执行: pip install uvicorn[standard]')
        sys.exit(1)

    print('=' * 56)
    print('  TestHub Backend (Uvicorn ASGI)')
    print(f'  http://{args.host}:{port}')
    print('  Protocols: HTTP + SSE + WebSocket')
    print('=' * 56)

    uvicorn.run(
        'backend.asgi:application',
        host=args.host,
        port=port,
        reload=args.reload,
        log_level='info',
        ws='websockets',
    )


if __name__ == '__main__':
    main()
