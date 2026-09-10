# -*- coding: utf-8 -*-
"""测试 RequestPerformanceLogAdmin 删除日志输出：
创建测试数据 → 模拟 request → 调用 direct_delete_selected → 检查日志tag是否出现
"""
import logging
import io

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '测试 RequestPerformanceLogAdmin 批量删除的日志输出（验证是否跳过确认页）'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=3, help='创建测试数据条数，默认3')

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model
        from django.test import RequestFactory
        from django.contrib import admin
        from apps.core.models import RequestPerformanceLog

        count = options['count']
        User = get_user_model()

        self.stdout.write(self.style.MIGRATE_HEADING('=== 开始测试 RequestPerformanceLogAdmin 删除日志 ==='))

        # ============================================================
        # 1. 设置内存日志捕获器，捕获 apps.core.admin 的 logger 输出
        # ============================================================
        admin_logger = logging.getLogger('apps.core.admin')
        original_level = admin_logger.level
        admin_logger.setLevel(logging.DEBUG)
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        admin_logger.addHandler(handler)
        try:
            # ============================================================
            # 2. 准备测试数据 & 模拟 request
            # ============================================================
            # 获取或创建一个超级用户用于模拟 request
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                user = User.objects.create_superuser(
                    username='test_admin_delete',
                    email='test_delete@example.com',
                    password='TestPass123!',
                )
                self.stdout.write(f'  ✅ 创建测试超级用户: {user.username}')
            else:
                self.stdout.write(f'  ✅ 使用现有超级用户: {user.username}')

            # 创建测试 RequestPerformanceLog 数据
            test_logs = []
            for i in range(count):
                log = RequestPerformanceLog.objects.create(
                    path=f'/api/test-delete-log-{i}/',
                    method='GET',
                    response_time=100 + i * 10,
                    status_code=200,
                    user=user,
                    ip_address='127.0.0.1',
                    user_agent='test-delete-cmd',
                )
                test_logs.append(log)
            self.stdout.write(f'  ✅ 创建 {len(test_logs)} 条测试日志, IDs={[l.id for l in test_logs]}')

            # 构造模拟的 Django HttpRequest（使用 RequestFactory）
            factory = RequestFactory()
            request = factory.post('/admin/core/requestperformancelog/')
            request.user = user
            # 给模拟 request 添加内存 messages 支持，避免 message_user 报错
            from django.contrib.messages.storage.fallback import FallbackStorage
            setattr(request, 'session', {})
            messages = FallbackStorage(request)
            setattr(request, '_messages', messages)

            # ============================================================
            # 3. 从 AdminSite 中取出已注册的 RequestPerformanceLogAdmin 实例
            # ============================================================
            model_admin = admin.site._registry.get(RequestPerformanceLog)
            if model_admin is None:
                self.stdout.write(self.style.ERROR('  ❌ RequestPerformanceLog 未注册到 AdminSite'))
                return
            self.stdout.write(f'  ✅ 获取到 Admin 实例: {model_admin.__class__.__name__}')

            # 先调用 get_actions 打日志，确认 action 注册状态
            actions = model_admin.get_actions(request)
            delete_action = actions.get('delete_selected')
            if delete_action:
                action_func = delete_action[0]
                self.stdout.write(
                    f'  ✅ delete_selected action 绑定函数: {action_func.__name__}'
                    f' (期望是 direct_delete_selected)'
                )
            else:
                self.stdout.write(self.style.WARNING('  ⚠️ delete_selected action 未找到'))

            # ============================================================
            # 4. 调用 direct_delete_selected（即期望走的"跳过确认页"分支）
            # ============================================================
            queryset = RequestPerformanceLog.objects.filter(
                id__in=[l.id for l in test_logs]
            )
            self.stdout.write(self.style.MIGRATE_HEADING('\n--- 调用 direct_delete_selected ---'))
            model_admin.direct_delete_selected(request, queryset)

            # 验证数据已删除
            remaining = RequestPerformanceLog.objects.filter(
                id__in=[l.id for l in test_logs]
            ).count()
            self.stdout.write(f'  删除后剩余记录数: {remaining} (期望 0)')

            # ============================================================
            # 5. 检查捕获到的日志内容
            # ============================================================
            handler.flush()
            captured = stream.getvalue()
            self.stdout.write(self.style.MIGRATE_HEADING('\n=== 捕获到的 apps.core.admin 日志 ==='))
            if captured.strip():
                for line in captured.strip().splitlines():
                    prefix = '📝 '
                    if '[批量删除-跳过确认页✅]' in line:
                        prefix = '✅✅✅ '
                    elif '[兜底触发⚠️]' in line:
                        prefix = '⚠️⚠️⚠️ '
                    elif '[get_actions]' in line:
                        prefix = '🔧 '
                    self.stdout.write(f'  {prefix}{line}')
            else:
                self.stdout.write(self.style.WARNING('  ⚠️ 没有捕获到任何日志（检查 logger 名称是否匹配）'))

            self.stdout.write(self.style.MIGRATE_HEADING('\n=== 结论 ==='))
            if '[批量删除-跳过确认页✅]' in captured:
                self.stdout.write(
                    self.style.SUCCESS(
                        '🎉 成功！日志中检测到 [批量删除-跳过确认页✅]，'
                        '证明 direct_delete_selected 被正确调用，确认页跳过逻辑有效。'
                    )
                )
            else:
                self.stdout.write(
                    self.style.ERROR(
                        '❌ 失败！日志中未检测到 [批量删除-跳过确认页✅]，'
                        '请检查 logger 名称或 action 绑定是否正确。'
                    )
                )
            if '[兜底触发⚠️]' in captured:
                self.stdout.write(
                    self.style.WARNING(
                        '⚠️  注意：检测到 [兜底触发⚠️]，说明 changelist_view 的兜底分支也被触发了。'
                    )
                )
            else:
                self.stdout.write('  ✅ 未触发兜底分支（符合预期，因为直接调用了自定义action）')
        finally:
            # 清理：移除 handler，恢复日志级别
            admin_logger.removeHandler(handler)
            admin_logger.setLevel(original_level)
            handler.close()

            # 清理测试用户（如果是我们刚创建的）
            if user.username == 'test_admin_delete':
                user.delete()
                self.stdout.write('\n  🧹 清理测试用户 test_admin_delete')
