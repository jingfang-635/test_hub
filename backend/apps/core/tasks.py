# -*- coding: utf-8 -*-
"""
性能监控聚合任务（由 Django-Q2 Schedule 调度）
- aggregate_daily_performance_stats: 每日凌晨聚合前一天数据
- aggregate_realtime_performance_stats: 每30分钟聚合当天实时数据
"""
import logging
from datetime import datetime, time, timedelta
from django.utils import timezone
from django.db.models import Avg, Max, Min, Count, Q

logger = logging.getLogger(__name__)


def _aggregate(date):
    """聚合指定日期的性能数据（date 为本地时区日期）"""
    from apps.core.models import RequestPerformanceLog, PerformanceStatistics
    # 用本地时区 datetime 范围查询，规避 MySQL __date lookup 在 USE_TZ=True 下失效的问题
    tz = timezone.get_current_timezone()
    start = datetime.combine(date, time.min, tzinfo=tz)
    end = start + timedelta(days=1)
    logs = RequestPerformanceLog.objects.filter(created_at__gte=start, created_at__lt=end)
    if not logs.exists():
        logger.info(f"无 {date} 性能数据，跳过聚合")
        return None
    stats = logs.aggregate(
        total=Count('id'),
        avg=Avg('response_time'),
        max=Max('response_time'),
        min=Min('response_time'),
        errors=Count('id', filter=Q(status_code__gte=400)),
        slow=Count('id', filter=Q(response_time__gt=1000)),
    )
    obj, created = PerformanceStatistics.objects.update_or_create(
        date=date,
        defaults={
            'total_requests': stats['total'] or 0,
            'avg_response_time': round(stats['avg'] or 0, 2),
            'max_response_time': round(stats['max'] or 0, 2),
            'min_response_time': round(stats['min'] or 0, 2),
            'error_count': stats['errors'] or 0,
            'slow_requests': stats['slow'] or 0,
        }
    )
    logger.info(f"已聚合 {date} 性能数据: total={stats['total']}, avg={stats['avg']}, errors={stats['errors']}, slow={stats['slow']}")
    return obj


def aggregate_daily_performance_stats():
    """每日聚合前一天的性能数据（Django-Q2 定时任务）"""
    yesterday = (timezone.localtime(timezone.now()) - timedelta(days=1)).date()
    _aggregate(yesterday)


def aggregate_realtime_performance_stats():
    """实时聚合当天性能数据（每30分钟，Django-Q2 定时任务）"""
    today = timezone.localtime(timezone.now()).date()
    _aggregate(today)


def backfill_performance_stats(days=30):
    """回填最近 days 天缺失的性能统计（含今天）。

    用于修复定时任务未注册/未运行期间产生的历史数据缺口：
    只扫描 RequestPerformanceLog 中实际有数据的日期，逐日重建聚合。
    """
    tz = timezone.get_current_timezone()
    today = timezone.localtime(timezone.now()).date()
    start_date = today - timedelta(days=max(days - 1, 0))

    from apps.core.models import RequestPerformanceLog

    start = datetime.combine(start_date, time.min, tzinfo=tz)
    end = datetime.combine(today, time.min, tzinfo=tz) + timedelta(days=1)
    # MySQL 下按本地时区取日期，避免 __date lookup 在 USE_TZ=True 时失效
    dates = {
        timezone.localtime(dt).date()
        for dt in RequestPerformanceLog.objects.filter(
            created_at__gte=start, created_at__lt=end
        ).values_list('created_at', flat=True)
    }

    count = 0
    for date in sorted(dates):
        if _aggregate(date) is not None:
            count += 1
    logger.info(f"性能统计回填完成：扫描 {len(dates)} 个有数据的日期，写入 {count} 条统计")
    return count
