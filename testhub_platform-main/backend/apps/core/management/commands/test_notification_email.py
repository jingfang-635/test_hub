# -*- coding: utf-8 -*-
"""测试通知模板系统的邮件发送功能"""
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = '测试通知模板系统的邮件发送功能（渲染变量 + 实际发送）'

    def add_arguments(self, parser):
        parser.add_argument('--to', nargs='+', required=True, help='收件人邮箱（可多个）')
        parser.add_argument('--template-id', type=int, help='通知模板ID')
        parser.add_argument('--template-name', type=str, help='通知模板名称')
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只渲染模板不实际发送邮件',
        )

    def _get_template(self, options):
        from apps.core.models import NotificationTemplate

        if options['template_id']:
            return NotificationTemplate.objects.get(id=options['template_id'])
        if options['template_name']:
            return NotificationTemplate.objects.get(name=options['template_name'])
        # 默认使用 is_default 模板
        tpl = NotificationTemplate.objects.filter(is_default=True, is_active=True).first()
        if tpl:
            return tpl
        # 无模板则临时创建一个（不落库，避免污染数据）
        tpl = NotificationTemplate(
            name='临时测试模板',
            template_type='text',
            subject='TestHub 测试通知 - {{task_name}}',
            content='任务 {{task_name}} 执行{{status_text}}，用时 {{runtime}}',
        )
        self.stdout.write(self.style.WARNING("未指定模板且无默认模板，使用内存临时模板"))
        return tpl

    def handle(self, *args, **options):
        from apps.core.notification_service import send_email_notification

        template = self._get_template(options)
        self.stdout.write(self.style.SUCCESS(f"使用模板: {template.name} (id={getattr(template, 'id', None)})"))

        context = {
            'task_name': '示例测试任务',
            'status_text': '成功',
            'runtime': '12.5s',
            'title': '示例测试',
            'tester': 'admin',
            'total_cases': 10,
            'passed_cases': 9,
            'failed_cases': 1,
            'error_cases': 0,
            'skipped_cases': 0,
            'begin_time': '2026-08-06 22:00:00',
            'execution_time': '2026-08-06 22:00:12',
            'task_type': 'API测试套件',
        }

        content = template.render(context)
        subject = template.render_subject(context) or template.name
        self.stdout.write(self.style.SUCCESS(f"渲染主题: {subject}"))
        self.stdout.write(self.style.SUCCESS("渲染内容:"))
        self.stdout.write(content)
        self.stdout.write("")

        if options['dry_run']:
            self.stdout.write(self.style.WARNING("--dry-run 模式，未实际发送邮件"))
            return

        ok = send_email_notification(template, context, options['to'])
        if ok:
            self.stdout.write(self.style.SUCCESS(f"邮件已发送至: {options['to']}"))
        else:
            raise CommandError("邮件发送失败，请检查 settings.EMAIL_* 配置与 SMTP 连通性")
