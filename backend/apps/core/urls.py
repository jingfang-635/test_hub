"""
Core 应用路由
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
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
    path('', include(router.urls)),
]
