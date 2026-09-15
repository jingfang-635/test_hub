# -*- coding: utf-8 -*-
"""注册性能监控聚合的 Django-Q2 定时任务（幂等）"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.models import Schedule


def default_schedules():
    """性能聚合定时任务定义（next_run 每次按当前时间计算，故用函数而非常量）。"""
    now = timezone.now()
    return [
        {
            'name': '每日性能统计聚合',
            'func': 'apps.core.tasks.aggregate_daily_performance_stats',
            'schedule_type': 'D',  # Daily
            'next_run': (now + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0),
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


def ensure_schedules(reset=False):
    """幂等确保性能聚合定时任务存在；返回 (created, skipped) 名称列表。"""
    created, skipped = [], []
    for cfg in default_schedules():
        existing = Schedule.objects.filter(name=cfg['name'])
        if existing.exists():
            if reset:
                existing.delete()
            else:
                skipped.append(cfg['name'])
                continue
        Schedule.objects.create(**cfg)
        created.append(cfg['name'])
    return created, skipped


class Command(BaseCommand):
    help = '注册性能监控聚合的 Django-Q2 定时任务（每日聚合 + 每30分钟实时聚合）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='先删除已存在的同名 Schedule 再重新创建',
        )
        parser.add_argument(
            '--backfill',
            type=int,
            default=0,
            metavar='DAYS',
            help='回填最近 N 天缺失的性能统计（修复定时任务未生效期间的历史数据）',
        )

    def handle(self, *args, **options):
        created, skipped = ensure_schedules(reset=options['reset'])

        for name in skipped:
            self.stdout.write(self.style.WARNING(f"任务已存在，跳过: {name}"))
        for name in created:
            self.stdout.write(self.style.SUCCESS(f"已创建任务: {name}"))

        backfill_days = options['backfill']
        if backfill_days:
            from apps.core.tasks import backfill_performance_stats

            count = backfill_performance_stats(backfill_days)
            self.stdout.write(self.style.SUCCESS(f"已回填 {count} 天性能统计（扫描最近 {backfill_days} 天）"))

        self.stdout.write(self.style.SUCCESS("性能聚合定时任务配置完成"))
