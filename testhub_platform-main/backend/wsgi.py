"""
WSGI config for backend project.
"""

import os
import sys
from pathlib import Path

# 将项目根目录（backend/ 的父目录）加入 sys.path，
# 确保 Vercel 等部署环境（CWD != 项目根目录）下 'backend' 包可被正确导入
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

application = get_wsgi_application()