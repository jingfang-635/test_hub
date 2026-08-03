from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt
from django.views.static import serve
from django.http import FileResponse, HttpResponseNotFound
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
import os

# 前端 index.html 路径
_FRONTEND_INDEX = os.path.join(getattr(settings, 'FRONTEND_DIST', ''), 'index.html')


def _serve_frontend_index(request):
    """SPA 回退视图：所有非 API 路由返回前端 index.html，由 Vue Router 处理。"""
    if os.path.exists(_FRONTEND_INDEX):
        return FileResponse(open(_FRONTEND_INDEX, 'rb'), content_type='text/html')
    return HttpResponseNotFound('<h1>Frontend not built</h1>')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    
    path('api/auth/', include('apps.users.urls')),
    path('api/projects/', include('apps.projects.urls')),
    path('api/testcases/', include('apps.testcases.urls')),
    path('api/testsuites/', include('apps.testsuites.urls')),
    path('api/executions/', include('apps.executions.urls')),
    path('api/reports/', include('apps.reports.urls')),
    path('api/reviews/', include('apps.reviews.urls')),
    path('api/versions/', include('apps.versions.urls')),
    path('api/assistant/', include('apps.assistant.urls')),
    path('api/users/', include('apps.users.urls')),
    path('api/requirement-analysis/', include('apps.requirement_analysis.urls')),
    path('api/ui-automation/', include('apps.ui_automation.urls')),
    path('api/app-automation/', include('apps.app_automation.urls')),  # APP自动化测试
    path('api/', include('apps.api_testing.urls')),
    path('api/core/', include('apps.core.urls')),
    path('api/data-factory/', include('apps.data_factory.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_FILES_URL, document_root=settings.STATIC_FILES_ROOT)

# APP自动化 Template 目录静态访问
urlpatterns += [
    path('app-automation-templates/<path:path>', 
         serve, 
         {'document_root': os.path.join(settings.BASE_DIR, 'apps', 'app_automation', 'Template')}),
]

# APP自动化 Allure 报告访问
urlpatterns += [
    path('app-automation-reports/<path:path>', 
         serve, 
         {'document_root': os.path.join(settings.MEDIA_ROOT, 'app-automation', 'allure-reports')}),
]

# 前端静态资源路由 (Vite 构建产物: /assets/*, *.wasm)
if getattr(settings, 'FRONTEND_DIST', ''):
    urlpatterns += [
        path('assets/<path:path>', serve, {'document_root': os.path.join(settings.FRONTEND_DIST, 'assets')}),
        re_path(r'^.*\.wasm$', serve, {'document_root': settings.FRONTEND_DIST}),
    ]

# SPA 回退：所有非 API/admin/static/media 路由返回前端 index.html
# 必须放在最后，确保 API 路由优先匹配
if getattr(settings, 'FRONTEND_DIST', ''):
    urlpatterns += [
        re_path(r'^(?!api/|admin/|media/|static/|static_files/|app-automation-templates/|app-automation-reports/).*$',
                _serve_frontend_index,
                name='frontend_spa_fallback'),
    ]