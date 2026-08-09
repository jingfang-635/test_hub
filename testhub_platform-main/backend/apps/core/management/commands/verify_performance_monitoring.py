# -*- coding: utf-8 -*-
"""验证性能监控系统：生成测试日志、运行聚合、查看统计结果"""
import random

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = '验证性能监控系统：生成测试日志 -> 运行聚合 -> 查看统计结果'

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=20, help='生成测试日志条数')
        parser.add_argument(
            '--clean',
            action='store_true',
            help='验证后清理本次生成的测试日志（统计结果保留）',
        )

    def handle(self, *args, **options):
        from datetime import datetime, time, timedelta
        from django.utils import timezone
        from apps.core.models import RequestPerformanceLog, PerformanceStatistics
        from apps.core.tasks import aggregate_realtime_performance_stats

        count = options['count']
        today = timezone.localtime(timezone.now()).date()
        marker = 'verify-perf-cmd'

        # 用本地时区 datetime 范围查询，规避 MySQL __date lookup 在 USE_TZ=True 下失效
        tz = timezone.get_current_timezone()
        day_start = datetime.combine(today, time.min, tzinfo=tz)
        day_end = day_start + timedelta(days=1)
        day_q = RequestPerformanceLog.objects.filter(created_at__gte=day_start, created_at__lt=day_end)

        before = day_q.count()
        self.stdout.write(f"当前今日性能日志数: {before}")

        # 1. 批量生成测试日志（含正常/慢请求/错误请求）
        logs = []
        for i in range(count):
            status = random.choices([200, 404, 500], weights=[80, 15, 5])[0]
            rt = random.choices([50, 120, 300, 800, 1200, 2500], weights=[40, 25, 15, 10, 5, 5])[0]
            logs.append(RequestPerformanceLog(
                path=f'/api/test/verify/{i}',
                method=random.choice(['GET', 'POST']),
                response_time=rt,
                status_code=status,
                ip_address='127.0.0.1',
                user_agent=marker,
            ))
        RequestPerformanceLog.objects.bulk_create(logs)
        after = day_q.count()
        self.stdout.write(self.style.SUCCESS(f"已生成 {count} 条测试日志，当前共 {after} 条"))

        # 2. 运行实时聚合
        aggregate_realtime_performance_stats()
        self.stdout.write(self.style.SUCCESS("已执行实时聚合任务 aggregate_realtime_performance_stats"))

        # 3. 输出统计结果
        try:
            stat = PerformanceStatistics.objects.get(date=today)
            self.stdout.write(self.style.SUCCESS("=== 今日性能统计 ==="))
            self.stdout.write(f"日期: {stat.date}")
            self.stdout.write(f"总请求数: {stat.total_requests}")
            self.stdout.write(f"平均响应时间: {stat.avg_response_time}ms")
            self.stdout.write(f"最大响应时间: {stat.max_response_time}ms")
            self.stdout.write(f"最小响应时间: {stat.min_response_time}ms")
            self.stdout.write(f"错误请求数(4xx/5xx): {stat.error_count}")
            self.stdout.write(f"慢请求数(>1s): {stat.slow_requests}")
            if stat.total_requests:
                self.stdout.write(f"错误率: {stat.error_count / stat.total_requests * 100:.2f}%")
                self.stdout.write(f"慢请求率: {stat.slow_requests / stat.total_requests * 100:.2f}%")
        except PerformanceStatistics.DoesNotExist:
            self.stdout.write(self.style.ERROR("聚合后未找到今日统计记录，请检查聚合任务日志"))

        # 4. 清理本次生成的测试日志
        if options['clean']:
            deleted, _ = RequestPerformanceLog.objects.filter(user_agent=marker).delete()
            self.stdout.write(self.style.WARNING(f"已清理 {deleted} 条测试日志（统计记录保留）"))
