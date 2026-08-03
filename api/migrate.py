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
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

import django
django.setup()

from django.core.management import call_command
from django.contrib.auth import get_user_model


def handler(event, context):
    """Vercel Serverless Function handler."""
    query = event.get('queryStringParameters', {}) or {}
    action = query.get('action', 'migrate')

    try:
        if action == 'migrate':
            call_command('migrate', '--run-syncdb', verbosity=1)
            return _response({'status': 'ok', 'message': '数据库迁移成功'})

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
