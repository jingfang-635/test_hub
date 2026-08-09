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
        from django.db import connection
        from django.db.migrations.loader import MigrationLoader
        from django.utils import timezone
        from django.apps import apps

        def _is_initial(migration):
            # migration_plan 返回 (Migration, backwards) 元组，这里兼容两种形态
            if isinstance(migration, (tuple, list)):
                migration = migration[0]
            return bool(getattr(migration, 'initial', False) or 'initial' in getattr(migration, 'name', ''))

        if action == 'check':
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            return JsonResponse({'status': 'ok', 'message': '数据库连接正常'})

        # ================== diagnose：对比模型与真实数据库，列出缺失列/未应用迁移 ==================
        elif action == 'diagnose':
            # 1. 现有表与列
            real_tables = {}
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                table_names = [row[0] for row in cursor.fetchall()]
                for t in table_names:
                    try:
                        cursor.execute(f"SHOW COLUMNS FROM `{t}`")
                        real_tables[t] = [row[0] for row in cursor.fetchall()]
                    except Exception:
                        real_tables[t] = []

            # 2. Django 模型期望的表与列
            expected = {}
            for model in apps.get_models():
                db_table = model._meta.db_table
                expected[db_table] = sorted([f.column for f in model._meta.concrete_fields])

            # 3. 缺失列
            missing_cols = {}
            for db_table, cols in expected.items():
                real_cols = set(real_tables.get(db_table, []))
                missing = [c for c in cols if c not in real_cols]
                if missing:
                    missing_cols[db_table] = missing

            # 4. 迁移记录 vs 磁盘
            loader = MigrationLoader(connection, ignore_no_migrations=True)
            applied = set()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT app, name FROM django_migrations")
                    applied = {(row[0], row[1]) for row in cursor.fetchall()}
            except Exception:
                pass

            unapplied_non_initial = []
            for key, migration in loader.disk_migrations.items():
                if not _is_initial(migration) and (migration.app_label, migration.name) not in applied:
                    unapplied_non_initial.append(f"{migration.app_label}.{migration.name}")

            return JsonResponse({
                'status': 'ok',
                'missing_columns_count': sum(len(v) for v in missing_cols.values()),
                'missing_columns': missing_cols,
                'unapplied_non_initial_migrations_count': len(unapplied_non_initial),
                'unapplied_non_initial_migrations': sorted(unapplied_non_initial),
            })

        # ================== fix：直接用 schema_editor 添加缺失列（绕过迁移系统） ==================
        elif action == 'fix':
            loader = MigrationLoader(connection, ignore_no_migrations=True)
            # 1. 诊断缺失列
            real_tables = {}
            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                table_names = [row[0] for row in cursor.fetchall()]
                for t in table_names:
                    try:
                        cursor.execute(f"SHOW COLUMNS FROM `{t}`")
                        real_tables[t] = [row[0] for row in cursor.fetchall()]
                    except Exception:
                        real_tables[t] = []

            # 2. 找出缺失列并直接添加
            added = 0
            skipped = 0
            failed = 0
            fail_details = []
            applied_migrations = set()
            all_missing = {}

            for model in apps.get_models():
                db_table = model._meta.db_table
                if db_table not in real_tables:
                    continue  # 表不存在，skip（init 负责建表）

                real_cols = set(real_tables[db_table])
                missing_fields = []

                for field in model._meta.concrete_fields:
                    if field.column and field.column not in real_cols:
                        missing_fields.append(field)

                if not missing_fields:
                    continue

                all_missing[db_table] = [f.column for f in missing_fields]

                # 用 schema_editor 逐个添加缺失字段
                for field in missing_fields:
                    try:
                        with connection.schema_editor(atomic=True) as schema_editor:
                            schema_editor.add_field(model, field)
                        added += 1
                    except Exception as e:
                        msg = str(e).lower()
                        if 'duplicate' in msg or 'already exists' in msg or '1060' in msg:
                            skipped += 1
                        else:
                            failed += 1
                            if len(fail_details) < 10:
                                fail_details.append({
                                    'table': db_table, 'column': field.column, 'error': str(e)[:200]
                                })

                # 3. 标记对应的非 initial 迁移为已应用
                app_label = model._meta.app_label
                for mig_name, migration in loader.disk_migrations.items():
                    if migration.app_label != app_label:
                        continue
                    if _is_initial(migration):
                        continue
                    for operation in migration.operations:
                        op_name = getattr(operation, 'name', None)
                        if op_name in [f.name for f in missing_fields]:
                            try:
                                with connection.cursor() as cursor:
                                    cursor.execute(
                                        "INSERT IGNORE INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                                        [app_label, migration.name, timezone.now()]
                                    )
                                applied_migrations.add(migration.name)
                            except Exception:
                                pass
                            break

            if not all_missing:
                return JsonResponse({'status': 'ok', 'message': '所有列已同步，无需修复'})

            msg = f"添加 {added}, 跳过 {skipped}, 失败 {failed}"
            if applied_migrations:
                msg += f"; 标记迁移: {', '.join(sorted(applied_migrations))}"

            return JsonResponse({
                'status': 'ok' if failed == 0 else 'warn',
                'message': msg,
                'added': added,
                'skipped': skipped,
                'failed': failed,
                'fail_details': fail_details,
                'total_missing_columns': sum(len(v) for v in all_missing.values()),
                'missing_columns': all_missing,
                'applied_migrations': sorted(applied_migrations),
            })

        # ================== migrate / repair：细粒度逐条执行，支持 batch ==================
        elif action in ('migrate', 'repair'):
            results = []

            # 1. 确保 django_migrations 表存在
            with connection.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS django_migrations (
                        id bigint AUTO_INCREMENT PRIMARY KEY,
                        app varchar(255) NOT NULL,
                        name varchar(255) NOT NULL,
                        applied datetime(6) NOT NULL,
                        UNIQUE(app, name)
                    )
                """)

            # 2. 已记录的迁移
            applied = set()
            with connection.cursor() as cursor:
                cursor.execute("SELECT app, name FROM django_migrations")
                applied = {(row[0], row[1]) for row in cursor.fetchall()}

            loader = MigrationLoader(connection, ignore_no_migrations=True)

            # 3. 预插入 initial 迁移（建表类）
            inserted_initial = 0
            with connection.cursor() as cursor:
                for migration in loader.disk_migrations.values():
                    key = (migration.app_label, migration.name)
                    if _is_initial(migration) and key not in applied:
                        try:
                            cursor.execute(
                                "INSERT IGNORE INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                                [migration.app_label, migration.name, timezone.now()]
                            )
                            inserted_initial += cursor.rowcount
                        except Exception:
                            pass
            if inserted_initial:
                results.append(f"预插入 {inserted_initial} 条 initial 迁移")

            # 4. repair：清理非 initial 错误记录
            cleaned = 0
            if action == 'repair':
                with connection.cursor() as cursor:
                    for migration in loader.disk_migrations.values():
                        if not _is_initial(migration):
                            key = (migration.app_label, migration.name)
                            if key in applied:
                                cursor.execute(
                                    "DELETE FROM django_migrations WHERE app=%s AND name=%s",
                                    [migration.app_label, migration.name]
                                )
                                cleaned += cursor.rowcount
                                applied.discard(key)
                if cleaned:
                    results.append(f"repair: 清理 {cleaned} 条错误标记的非 initial 迁移")

            # 5. 收集待执行的非 initial 迁移（按 loader 依赖顺序）
            pending = []  # [(migration, key)]
            seen_keys = set()
            # loader.graph.root_nodes + 依赖拓扑排序可通过 MigrationExecutor 获得
            from django.db.migrations.executor import MigrationExecutor
            executor = MigrationExecutor(connection)
            # 未应用的迁移（initial 已补齐，但 non-initial 是真未执行）
            # migration_plan -> [(Migration, backwards), ...]
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            for item in plan:
                migration = item[0] if isinstance(item, (tuple, list)) else item
                backwards = item[1] if isinstance(item, (tuple, list)) and len(item) > 1 else False
                if backwards:
                    continue
                if not _is_initial(migration):
                    key = (migration.app_label, migration.name)
                    if key not in applied and key not in seen_keys:
                        seen_keys.add(key)
                        pending.append(migration)

            # 6. 批处理执行 pending
            try:
                batch_param = request.GET.get('batch', None)
                page_size = int(request.GET.get('size', '30'))
            except (ValueError, TypeError):
                batch_param = None
                page_size = 30

            total_pending = len(pending)
            total_batches = max(1, (total_pending + page_size - 1) // page_size)

            # 无 batch 且总量超过一页：返回分批信息，由用户决定是否批量执行
            if batch_param is None and total_pending > page_size:
                # 先尝试快速执行一小批前 10 个（多为 AddField，很快），再返回进度
                batch_idx = 0
            elif batch_param is None:
                batch_idx = 0
            else:
                try:
                    batch_idx = max(0, int(batch_param) - 1)
                except (ValueError, TypeError):
                    batch_idx = 0

            start = batch_idx * page_size
            end = min(start + page_size, total_pending)
            batch_items = pending[start:end]

            executed_ok = 0
            executed_fail = 0
            executed_skip = 0
            fail_details = []

            for migration in batch_items:
                key = (migration.app_label, migration.name)
                try:
                    # 重建 executor 获取最新 applied 状态
                    executor = MigrationExecutor(connection)
                    # from_state = 当前所有已应用迁移的状态（不含本 migration）
                    from_state = executor.loader.project_state()
                    # 直接调用 migration.apply，Django 内部处理 schema 变更
                    with connection.schema_editor(atomic=True) as schema_editor:
                        migration.apply(
                            app_label=migration.app_label,
                            schema_editor=schema_editor,
                            from_state=from_state,
                        )
                    # executor 会自动记录到 django_migrations（通过 apply 内部的 record_applied）
                    # 但为了保险，手动也标记一下
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "INSERT IGNORE INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                            [migration.app_label, migration.name, timezone.now()]
                        )
                    executed_ok += 1
                except Exception as e:
                    msg = str(e).lower()
                    if ('duplicate' in msg and 'column' in msg) or \
                       ('already exists' in msg and ('column' in msg or 'key' in msg or 'table' in msg)) or \
                       '1060' in msg or '1061' in msg or '1050' in msg:
                        # 字段/索引/表已存在，跳过并手动标记为 applied
                        with connection.cursor() as cursor:
                            cursor.execute(
                                "INSERT IGNORE INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                                [migration.app_label, migration.name, timezone.now()]
                            )
                        executed_skip += 1
                    else:
                        executed_fail += 1
                        if len(fail_details) < 10:
                            fail_details.append({
                                'migration': f"{migration.app_label}.{migration.name}",
                                'error': str(e)[:200]
                            })

            is_last = (batch_idx + 1 >= total_batches)
            next_batch = (batch_idx + 2) if not is_last else None

            message = (
                f"本批次: 成功 {executed_ok}, 跳过 {executed_skip}, 失败 {executed_fail}; "
                f"待执行总数 {total_pending}, 进度 {min(end, total_pending)}/{total_pending}"
            )
            if results:
                message = '; '.join(results) + '; ' + message

            return JsonResponse({
                'status': 'ok' if executed_fail == 0 else 'warn',
                'message': message,
                'inserted_initial': inserted_initial,
                'cleaned': cleaned if action == 'repair' else None,
                'total_pending': total_pending,
                'total_batches': total_batches,
                'current_batch': (batch_idx + 1),
                'page_size': page_size,
                'progress': f"{min(end, total_pending)}/{total_pending}",
                'executed_ok': executed_ok,
                'executed_skip': executed_skip,
                'executed_fail': executed_fail,
                'fail_details': fail_details,
                'next': (f'/api/migrate?action={action}&batch={next_batch}&size={page_size}') if next_batch else None,
                'is_complete': is_last,
            })

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
    path('api/scheduler/', include('apps.scheduler.urls')),  # 统一定时任务调度
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