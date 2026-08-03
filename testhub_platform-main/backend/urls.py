from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import csrf_exempt
from django.views.static import serve
from django.http import FileResponse, HttpResponseNotFound, JsonResponse
from django.views import View
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
import os
import json

# 前端 index.html 路径
_FRONTEND_INDEX = os.path.join(getattr(settings, 'FRONTEND_DIST', ''), 'index.html')


def _serve_frontend_index(request):
    """SPA 回退视图：所有非 API 路由返回前端 index.html，由 Vue Router 处理。"""
    if os.path.exists(_FRONTEND_INDEX):
        return FileResponse(open(_FRONTEND_INDEX, 'rb'), content_type='text/html')
    return HttpResponseNotFound('<h1>Frontend not built</h1>')


@csrf_exempt
def _migrate_view(request):
    """数据库迁移管理视图 (仅用于 Vercel 部署后初始化)。"""
    action = request.GET.get('action', 'check')

    try:
        if action == 'check':
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            return JsonResponse({'status': 'ok', 'message': '数据库连接正常'})

        elif action == 'migrate':
            from django.core.management import call_command
            import io

            # 先尝试创建迁移
            out = io.StringIO()
            try:
                call_command('makemigrations', '--check', '--dry-run', verbosity=0, stdout=out)
            except Exception:
                pass  # 没有新迁移可创建

            # 执行迁移
            out = io.StringIO()
            call_command('migrate', '--run-syncdb', '--skip-checks', '--noinput', verbosity=2, stdout=out)
            output = out.getvalue()
            return JsonResponse({'status': 'ok', 'message': '数据库迁移成功', 'output': output[:2000]})

        elif action == 'createsuperuser':
            from django.contrib.auth import get_user_model
            User = get_user_model()
            username = request.GET.get('username', 'admin')
            password = request.GET.get('password', 'admin123')
            email = request.GET.get('email', 'admin@test.com')

            if User.objects.filter(username=username).exists():
                return JsonResponse({'status': 'warn', 'message': f'用户 {username} 已存在'})

            User.objects.create_superuser(username=username, password=password, email=email)
            return JsonResponse({'status': 'ok', 'message': f'超级用户 {username} 创建成功'})

        elif action == 'init':
            """一键初始化: 迁移 + 创建管理员"""
            from django.core.management import call_command
            from django.contrib.auth import get_user_model
            import io

            results = []

            # Step 1: 迁移
            try:
                out = io.StringIO()
                call_command('migrate', '--run-syncdb', '--skip-checks', '--noinput', verbosity=1, stdout=out)
                results.append('迁移成功')
            except Exception as e:
                return JsonResponse({'status': 'error', 'message': f'迁移失败: {str(e)}'}, status=500)

            # Step 2: 创建管理员
            try:
                User = get_user_model()
                if not User.objects.filter(username='admin').exists():
                    User.objects.create_superuser(username='admin', password='admin123', email='admin@test.com')
                    results.append('管理员 admin 创建成功')
                else:
                    results.append('管理员 admin 已存在')
            except Exception as e:
                results.append(f'创建管理员失败: {str(e)}')

            return JsonResponse({'status': 'ok', 'message': '; '.join(results)})

        else:
            return JsonResponse({'status': 'error', 'message': f'未知操作: {action}'}, status=400)

    except Exception as e:
        import traceback
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }, status=500)


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
    path('api/migrate', _migrate_view, name='migrate'),
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
    def _serve_frontend_file(request, file_path):
        """服务前端静态文件 (wasm 等)。"""
        full_path = os.path.join(settings.FRONTEND_DIST, file_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            return FileResponse(open(full_path, 'rb'))
        return HttpResponseNotFound(f'File not found: {file_path}')

    urlpatterns += [
        path('assets/<path:path>', serve, {'document_root': os.path.join(settings.FRONTEND_DIST, 'assets')}),
        re_path(r'^(?P<file_path>.*\.wasm)$', _serve_frontend_file),
    ]

# SPA 回退：所有非 API/admin/static/media 路由返回前端 index.html
# 必须放在最后，确保 API 路由优先匹配
if getattr(settings, 'FRONTEND_DIST', ''):
    urlpatterns += [
        re_path(r'^(?!api/|admin/|media/|static/|static_files/|app-automation-templates/|app-automation-reports/).*$',
                _serve_frontend_index,
                name='frontend_spa_fallback'),
    ]