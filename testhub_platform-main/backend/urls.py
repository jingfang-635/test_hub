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
            from django.db import connection
            from django.db.migrations.loader import MigrationLoader
            import io

            out = io.StringIO()

            # 检查 django_migrations 是否有记录
            has_migration_records = False
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM django_migrations")
                    count = cursor.fetchone()[0]
                    has_migration_records = count > 0
            except Exception:
                pass  # 表不存在, 视为无记录

            try:
                if not has_migration_records:
                    # 表已通过 schema_editor 创建, 但 django_migrations 为空
                    # 直接手动插入迁移记录, 绕过 migrate 命令（migrate --fake 仍会同步无迁移app导致表已存在冲突）
                    loader = MigrationLoader(connection, ignore_no_migrations=True)
                    graph = loader.graph

                    inserted = 0
                    with connection.cursor() as cursor:
                        # 先创建 django_migrations 表（如果不存在）
                        try:
                            cursor.execute("""
                                CREATE TABLE IF NOT EXISTS django_migrations (
                                    id bigint AUTO_INCREMENT PRIMARY KEY,
                                    app varchar(255) NOT NULL,
                                    name varchar(255) NOT NULL,
                                    applied datetime(6) NOT NULL,
                                    UNIQUE(app, name)
                                )
                            """)
                        except Exception:
                            pass  # 可能已存在或MySQL语法不同

                        for node in graph.leaf_nodes():
                            # 遍历所有迁移节点, 插入记录
                            for migration in loader.disk_migrations.values():
                                try:
                                    from django.utils import timezone
                                    cursor.execute(
                                        "INSERT IGNORE INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                                        [migration.app_label, migration.name, timezone.now()]
                                    )
                                    inserted += cursor.rowcount
                                except Exception:
                                    pass

                    out.write(f'\n[手动插入 {inserted} 条迁移记录到 django_migrations]\n')
                    out.write('[表已通过 init 创建, 跳过 migrate 命令]\n')
                else:
                    # 有迁移记录, 执行正常增量迁移
                    out.write('[执行增量迁移]\n')
                    call_command('migrate', '--skip-checks', '--noinput', verbosity=1, stdout=out)

                output = out.getvalue()
                return JsonResponse({'status': 'ok', 'message': '数据库迁移成功', 'output': output[:2000]})
            except Exception as e:
                output = out.getvalue()
                return JsonResponse({'status': 'error', 'message': f'迁移失败: {str(e)}', 'output': output[:1000]}, status=500)

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
            """分批建表: 每次 batch 只创建少量表, 确保不超时"""
            from django.apps import apps
            from django.db import connection
            from django.contrib.auth import get_user_model
            import logging

            logger = logging.getLogger(__name__)
            batch = request.GET.get('batch', None)

            # 收集所有建表 SQL (collect_sql 不访问数据库, 纯内存操作)
            all_models = list(apps.get_models())
            with connection.schema_editor(collect_sql=True) as se:
                for model in all_models:
                    se.create_model(model)
            all_sql = se.collected_sql

            batch_size = 5
            total_batches = (len(all_sql) + batch_size - 1) // batch_size

            # 无 batch 参数: 返回分批信息
            if batch is None:
                return JsonResponse({
                    'status': 'ok',
                    'message': f'共 {len(all_sql)} 条建表 SQL, 分 {total_batches} 批执行',
                    'total_sql': len(all_sql),
                    'total_batches': total_batches,
                    'next': f'/api/migrate?action=init&batch=1'
                })

            batch_idx = int(batch) - 1
            if batch_idx < 0 or batch_idx >= total_batches:
                return JsonResponse({
                    'status': 'error',
                    'message': f'batch 范围: 1..{total_batches}'
                }, status=400)

            start = batch_idx * batch_size
            end = start + batch_size
            batch_sql = all_sql[start:end]

            # 执行当前批次的 SQL
            executed = 0
            skipped = 0
            errors = 0

            with connection.cursor() as cursor:
                cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
                for sql in batch_sql:
                    try:
                        cursor.execute(sql)
                        executed += 1
                    except Exception as e:
                        err_msg = str(e).lower()
                        if 'already exists' in err_msg or '1050' in err_msg:
                            skipped += 1
                        else:
                            errors += 1
                            logger.warning(f'SQL 执行失败: {str(e)[:200]}')
                cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

            is_last = (batch_idx + 1 >= total_batches)

            # 最后一批: 创建 django_migrations 表 + 管理员
            extra_results = []
            if is_last:
                try:
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            CREATE TABLE IF NOT EXISTS django_migrations (
                                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                                app VARCHAR(255) NOT NULL,
                                name VARCHAR(255) NOT NULL,
                                applied DATETIME NOT NULL
                            )
                        """)
                    extra_results.append('迁移记录表已就绪')
                except Exception as e:
                    logger.warning(f'django_migrations 表创建警告: {e}')

                try:
                    User = get_user_model()
                    if not User.objects.filter(username='admin').exists():
                        User.objects.create_superuser(username='admin', password='admin123', email='admin@test.com')
                        extra_results.append('管理员 admin 创建成功')
                    else:
                        extra_results.append('管理员 admin 已存在')
                except Exception as e:
                    extra_results.append(f'创建管理员失败: {str(e)}')
                    logger.error(f'创建管理员失败: {e}')

            next_batch = batch_idx + 2 if not is_last else None
            result_msg = f'批次 {batch}/{total_batches}: 执行 {executed}, 跳过 {skipped}, 失败 {errors}'
            if extra_results:
                result_msg += '; ' + '; '.join(extra_results)

            return JsonResponse({
                'status': 'ok',
                'message': result_msg,
                'next': f'/api/migrate?action=init&batch={next_batch}' if next_batch else None,
                'is_complete': is_last
            })

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