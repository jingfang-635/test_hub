"""
Vercel Serverless Function 入口
将所有请求路由到 Django ASGI application
"""
import sys
import os
from pathlib import Path

# 把 testhub_platform-main 添加到 sys.path
# api/index.py -> 项目根 -> testhub_platform-main
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent / 'testhub_platform-main')
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# 设置 Django settings 模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

# 导入 Django ASGI app
# backend.asgi 在导入时会自动调用 get_asgi_application() 完成 Django setup
from backend.asgi import application

# Vercel Python runtime 期望导出 `app`
app = application
