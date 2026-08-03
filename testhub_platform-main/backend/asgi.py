"""
ASGI config for backend project.
支持 Daphne (WebSocket) 和 runserver (仅 HTTP) 两种模式
"""

import os
import sys
import logging
import traceback
from pathlib import Path

# 在 Django setup 之前配置基础日志输出到 stdout，
# 确保 Vercel 部署环境能捕获到启动过程中的所有日志
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    stream=sys.stdout,
)
logger = logging.getLogger('asgi_startup')
logger.info('=' * 60)
logger.info('ASGI 启动开始')
logger.info('Python 版本: %s', sys.version)
logger.info('当前工作目录 (CWD): %s', os.getcwd())
logger.info('__file__: %s', __file__)

# 将项目根目录（backend/ 的父目录）加入 sys.path，
# 确保 Vercel 等部署环境（CWD != 项目根目录）下 'backend' 包可被正确导入
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
logger.info('计算得到的项目根目录: %s', _PROJECT_ROOT)
if _PROJECT_ROOT in sys.path:
    logger.info('项目根目录已在 sys.path 中 (位置: %d)', sys.path.index(_PROJECT_ROOT))
else:
    sys.path.insert(0, _PROJECT_ROOT)
    logger.info('已将项目根目录插入 sys.path[0]')

logger.info('当前 sys.path:')
for idx, path in enumerate(sys.path):
    logger.info('  sys.path[%d] = %s', idx, path)

# 设置 DJANGO_SETTINGS_MODULE
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
logger.info('DJANGO_SETTINGS_MODULE = %s', os.environ.get('DJANGO_SETTINGS_MODULE'))

# 导入 Django ASGI 工厂函数
try:
    from django.core.asgi import get_asgi_application
    logger.info('成功导入 django.core.asgi.get_asgi_application')
except ImportError as e:
    logger.error('导入 django.core.asgi 失败: %s', e)
    logger.error('请检查 Django 是否已安装，以及 PYTHONPATH 配置')
    raise

# 调用 get_asgi_application()，内部会触发 django.setup() 加载 settings 和 apps
# 这是 Vercel 部署中最常出错的环节（DB 连接、apps 导入等）
try:
    logger.info('开始调用 get_asgi_application()...')
    django_asgi_app = get_asgi_application()
    logger.info('get_asgi_application() 调用成功，Django setup 完成')
except Exception as e:
    logger.error('get_asgi_application() 调用失败: %s', e)
    logger.error('完整 traceback:\n%s', traceback.format_exc())
    raise

# 切换到项目专用 logger
logger = logging.getLogger(__name__)

# 尝试启用 WebSocket 支持（需要 channels、routing 等模块）
try:
    logger.info('尝试导入 channels 及 WebSocket routing...')
    from channels.auth import AuthMiddlewareStack
    from channels.routing import ProtocolTypeRouter, URLRouter
    logger.info('channels 模块导入成功')

    logger.info('导入 app_automation.routing...')
    from apps.app_automation import routing as app_automation_routing
    app_ws_count = len(app_automation_routing.websocket_urlpatterns)
    logger.info('app_automation routing 加载完成，WebSocket 路由数: %d', app_ws_count)

    logger.info('导入 ui_automation.routing...')
    from apps.ui_automation import routing as ui_automation_routing
    ui_ws_count = len(ui_automation_routing.websocket_urlpatterns)
    logger.info('ui_automation routing 加载完成，WebSocket 路由数: %d', ui_ws_count)

    application = ProtocolTypeRouter({
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(
                app_automation_routing.websocket_urlpatterns
                + ui_automation_routing.websocket_urlpatterns
            )
        ),
    })
    logger.info('=' * 60)
    logger.info('ASGI 已启用 WebSocket 支持 (需通过 Daphne 启动)')
    logger.info('  - HTTP 路由: django_asgi_app')
    logger.info('  - WebSocket 路由总数: %d', app_ws_count + ui_ws_count)
    logger.info('=' * 60)
except ImportError as e:
    application = django_asgi_app
    logger.warning('=' * 60)
    logger.warning('channels 未安装或 routing 导入失败，降级为仅 HTTP 模式')
    logger.warning('缺失的模块: %s', e)
    logger.warning('完整 traceback:\n%s', traceback.format_exc())
    logger.warning('=' * 60)
except Exception as e:
    application = django_asgi_app
    logger.warning('=' * 60)
    logger.warning('WebSocket 初始化失败，降级为仅 HTTP 模式')
    logger.warning('异常类型: %s', type(e).__name__)
    logger.warning('异常消息: %s', e)
    logger.warning('完整 traceback:\n%s', traceback.format_exc())
    logger.warning('=' * 60)
