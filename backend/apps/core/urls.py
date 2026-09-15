"""
Core 应用路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    EmailConfigView,
    EmailConfigTestView,
    UnifiedNotificationConfigViewSet,
    NotificationTemplateViewSet,
    RequestPerformanceLogViewSet,
    PerformanceStatisticsViewSet,
    SkillViewSet,
    MCPServerViewSet,
    ModuleSwitchViewSet,
)

router = DefaultRouter()
router.register(r'notification-configs', UnifiedNotificationConfigViewSet, basename='unified-notification-config')
router.register(r'notification-templates', NotificationTemplateViewSet, basename='notification-template')
router.register(r'request-performance-logs', RequestPerformanceLogViewSet, basename='request-performance-log')
router.register(r'performance-statistics', PerformanceStatisticsViewSet, basename='performance-statistics')
router.register(r'skills', SkillViewSet, basename='skill')
router.register(r'mcp-servers', MCPServerViewSet, basename='mcp-server')
router.register(r'module-switches', ModuleSwitchViewSet, basename='module-switch')

urlpatterns = [
    # 邮箱配置（单例）：显式注册以支持 GET / PUT / POST 同一 URL
    path('email-config/', EmailConfigView.as_view(), name='email-config'),
    path('email-config/test/', EmailConfigTestView.as_view(), name='email-config-test'),
    path('', include(router.urls)),
]
