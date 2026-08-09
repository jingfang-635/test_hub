"""
Vercel 迁移脚本（与 backend/urls.py _migrate_view 保持一致的备用入口）
访问：
  https://<domain>/api/migrate?action=check      检查连接
  https://<domain>/api/migrate?action=diagnose   诊断：列缺失/未应用迁移
  https://<domain>/api/migrate?action=repair     推荐：先清理再逐条执行迁移，支持 batch=N&size=N
  https://<domain>/api/migrate?action=migrate    仅执行迁移（不清理）
  https://<domain>/api/migrate?action=createsuperuser  创建管理员
"""
import sys
import os
import json
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent / 'testhub_platform-main')
_BACKEND_DIR = str(Path(_PROJECT_ROOT) / 'backend')
for _p in (_PROJECT_ROOT, _BACKEND_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone
from django.apps import apps


def _is_initial(migration):
    # migration_plan 返回 (Migration, backwards) 元组，这里兼容两种形态
    if isinstance(migration, (tuple, list)):
        migration = migration[0]
    return bool(getattr(migration, 'initial', False) or 'initial' in getattr(migration, 'name', ''))


def _response(data, status=200):
    return {
        'statusCode': status,
        'headers': {'Content-Type': 'application/json; charset=utf-8'},
        'body': json.dumps(data, ensure_ascii=False, default=str)
    }


def handler(event, context):
    query = event.get('queryStringParameters', {}) or {}
    action = query.get('action', 'check')

    try:
        if action == 'check':
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            return _response({'status': 'ok', 'message': '数据库连接正常'})

        # ========== diagnose：诊断缺失列/未应用迁移 ==========
        if action == 'diagnose':
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

            expected = {}
            for model in apps.get_models():
                db_table = model._meta.db_table
                expected[db_table] = sorted([f.column for f in model._meta.concrete_fields])

            missing_cols = {}
            for db_table, cols in expected.items():
                real_cols = set(real_tables.get(db_table, []))
                missing = [c for c in cols if c not in real_cols]
                if missing:
                    missing_cols[db_table] = missing

            loader = MigrationLoader(connection, ignore_no_migrations=True)
            applied = set()
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT app, name FROM django_migrations")
                    applied = {(row[0], row[1]) for row in cursor.fetchall()}
            except Exception:
                pass

            unapplied_non_initial = []
            for migration in loader.disk_migrations.values():
                if not _is_initial(migration) and (migration.app_label, migration.name) not in applied:
                    unapplied_non_initial.append(f"{migration.app_label}.{migration.name}")

            return _response({
                'status': 'ok',
                'missing_columns_count': sum(len(v) for v in missing_cols.values()),
                'missing_columns': missing_cols,
                'unapplied_non_initial_migrations_count': len(unapplied_non_initial),
                'unapplied_non_initial_migrations': sorted(unapplied_non_initial),
            })

        # ========== fix：直接用 schema_editor 添加缺失列（绕过迁移系统） ==========
        if action == 'fix':
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
                    continue

                real_cols = set(real_tables[db_table])
                missing_fields = []

                for field in model._meta.concrete_fields:
                    if field.column and field.column not in real_cols:
                        missing_fields.append(field)

                if not missing_fields:
                    continue

                all_missing[db_table] = [f.column for f in missing_fields]

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
                return _response({'status': 'ok', 'message': '所有列已同步，无需修复'})

            msg = f"添加 {added}, 跳过 {skipped}, 失败 {failed}"
            if applied_migrations:
                msg += f"; 标记迁移: {', '.join(sorted(applied_migrations))}"

            return _response({
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

        # ========== migrate / repair：细粒度逐条执行，支持 batch ==========
        if action in ('migrate', 'repair'):
            results = []

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

            applied = set()
            with connection.cursor() as cursor:
                cursor.execute("SELECT app, name FROM django_migrations")
                applied = {(row[0], row[1]) for row in cursor.fetchall()}

            loader = MigrationLoader(connection, ignore_no_migrations=True)

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

            executor = MigrationExecutor(connection)
            # migration_plan -> [(Migration, backwards), ...]
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            pending = []
            seen_keys = set()
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

            try:
                batch_param = query.get('batch', None)
                page_size = int(query.get('size', '30'))
            except (ValueError, TypeError):
                batch_param = None
                page_size = 30

            total_pending = len(pending)
            total_batches = max(1, (total_pending + page_size - 1) // page_size)

            if batch_param is None:
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

            return _response({
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

        if action == 'createsuperuser':
            User = get_user_model()
            username = query.get('username', 'admin')
            password = query.get('password', 'admin123')
            email = query.get('email', 'admin@test.com')

            if User.objects.filter(username=username).exists():
                return _response({'status': 'warn', 'message': f'用户 {username} 已存在'})

            User.objects.create_superuser(username=username, password=password, email=email)
            return _response({'status': 'ok', 'message': f'超级用户 {username} 创建成功'})

        if action == 'check':
            pass

        return _response({'status': 'error', 'message': f'未知操作: {action}'}, 400)

    except Exception as e:
        import traceback
        return _response({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }, 500)
