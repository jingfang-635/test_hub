# -*- coding: utf-8 -*-
"""注册性能监控聚合的 Django-Q2 定时任务（幂等）"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.models import Schedule


class Command(BaseCommand):
    help = '注册性能监控聚合的 Django-Q2 定时任务（每日聚合 + 每30分钟实时聚合）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='先删除已存在的同名 Schedule 再重新创建',
        )

    def handle(self, *args, **options):
        reset = options['reset']
        now = timezone.now()
        tomorrow_0005 = (now + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)

        schedules = [
            {
                'name': '每日性能统计聚合',
                'func': 'apps.core.tasks.aggregate_daily_performance_stats',
                'schedule_type': 'D',  # Daily
                'next_run': tomorrow_0005,
                'repeats': -1,
            },
            {
                'name': '实时性能统计聚合',
                'func': 'apps.core.tasks.aggregate_realtime_performance_stats',
                'schedule_type': 'I',  # Interval
                'minutes': 30,
                'next_run': now,
                'repeats': -1,
            },
        ]

        for cfg in schedules:
            existing = Schedule.objects.filter(name=cfg['name'])
            if existing.exists():
                if reset:
                    existing.delete()
                    self.stdout.write(self.style.WARNING(f"已删除旧任务: {cfg['name']}"))
                else:
                    obj = existing.first()
                    self.stdout.write(self.style.WARNING(
                        f"任务已存在，跳过: {cfg['name']} (id={obj.id}, next_run={obj.next_run})"
                    ))
                    continue
            Schedule.objects.create(**cfg)
            self.stdout.write(self.style.SUCCESS(
                f"已创建任务: {cfg['name']} -> {cfg['func']} (type={cfg['schedule_type']})"
            ))

        self.stdout.write(self.style.SUCCESS("性能聚合定时任务配置完成"))
