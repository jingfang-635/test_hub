"""
Vercel 迁移脚本
访问 https://www.xjftest.xyz/api/migrate?action=migrate 触发数据库迁移
访问 https://www.xjftest.xyz/api/migrate?action=createsuperuser 创建管理员
访问 https://www.xjftest.xyz/api/migrate?action=check 检查数据库连接
"""
import sys
import os
import json
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent / 'testhub_platform-main')
# apps 已移入 backend/，需同时把 backend 目录加入 sys.path，使 `from apps.xxx` 可导入
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
from django.utils import timezone


def handler(event, context):
    """Vercel Serverless Function handler."""
    query = event.get('queryStringParameters', {}) or {}
    action = query.get('action', 'migrate')

    try:
        if action in ('migrate', 'repair'):
            # 表已通过 init 批次创建, 这里仅补齐 initial 迁移记录并执行增量迁移
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

            # 2. 获取已记录的迁移
            applied = set()
            with connection.cursor() as cursor:
                cursor.execute("SELECT app, name FROM django_migrations")
                applied = {(row[0], row[1]) for row in cursor.fetchall()}

            # 3. 预插入 initial 迁移记录（建表类迁移，表已通过 init 创建）
            #    非 initial 迁移（字段变更等）不预插入，让步骤4的 migrate 真正执行
            loader = MigrationLoader(connection, ignore_no_migrations=True)
            inserted = 0
            with connection.cursor() as cursor:
                for migration in loader.disk_migrations.values():
                    key = (migration.app_label, migration.name)
                    is_initial = getattr(migration, 'initial', False) or 'initial' in migration.name
                    if is_initial and key not in applied:
                        try:
                            cursor.execute(
                                "INSERT IGNORE INTO django_migrations (app, name, applied) VALUES (%s, %s, %s)",
                                [migration.app_label, migration.name, timezone.now()]
                            )
                            inserted += cursor.rowcount
                        except Exception:
                            pass

            # repair 模式: 清理之前可能错误预插入的非 initial 迁移记录
            cleaned = 0
            if action == 'repair':
                with connection.cursor() as cursor:
                    for migration in loader.disk_migrations.values():
                        is_initial = getattr(migration, 'initial', False) or 'initial' in migration.name
                        if not is_initial:
                            key = (migration.app_label, migration.name)
                            if key in applied:
                                cursor.execute(
                                    "DELETE FROM django_migrations WHERE app=%s AND name=%s",
                                    [migration.app_label, migration.name]
                                )
                                cleaned += cursor.rowcount

            # 4. 执行增量迁移（非 initial 迁移会被真正执行）
            call_command('migrate', '--skip-checks', '--noinput', verbosity=1)
            return _response({
                'status': 'ok',
                'message': '数据库迁移成功',
                'inserted': inserted,
                'cleaned': cleaned if action == 'repair' else None
            })

        elif action == 'createsuperuser':
            User = get_user_model()
            username = query.get('username', 'admin')
            password = query.get('password', 'admin123')
            email = query.get('email', 'admin@test.com')

            if User.objects.filter(username=username).exists():
                return _response({'status': 'warn', 'message': f'用户 {username} 已存在'})

            User.objects.create_superuser(username=username, password=password, email=email)
            return _response({'status': 'ok', 'message': f'超级用户 {username} 创建成功'})

        elif action == 'check':
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            return _response({'status': 'ok', 'message': '数据库连接正常'})

        else:
            return _response({'status': 'error', 'message': f'未知操作: {action}'}, 400)

    except Exception as e:
        return _response({'status': 'error', 'message': str(e)}, 500)


def _response(data, status=200):
    return {
        'statusCode': status,
        'headers': {'Content-Type': 'application/json; charset=utf-8'},
        'body': json.dumps(data, ensure_ascii=False)
    }
