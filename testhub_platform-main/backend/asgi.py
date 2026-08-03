"""
ASGI config for backend project.
支持 Daphne (WebSocket) 和 runserver (仅 HTTP) 两种模式
"""

import os
import sys
import logging
from pathlib import Path

# 将项目根目录（backend/ 的父目录）加入 sys.path，
# 确保 Vercel 等部署环境（CWD != 项目根目录）下 'backend' 包可被正确导入
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

django_asgi_app = get_asgi_application()

logger = logging.getLogger(__name__)

try:
    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter
    from apps.app_automation import routing as app_automation_routing
    from apps.ui_automation import routing as ui_automation_routing

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                app_automation_routing.websocket_urlpatterns
                + ui_automation_routing.websocket_urlpatterns
            )
        ),
    })
    logger.info("ASGI 已启用 WebSocket 支持 (需通过 Daphne 启动)")
except ImportError:
    application = django_asgi_app
    logger.warning("channels 未安装，WebSocket 不可用，仅支持 HTTP")
except Exception as e:
    application = django_asgi_app
    logger.warning(f"WebSocket 初始化失败: {e}，降级为仅 HTTP 模式")