from rest_framework import serializers

from apps.core.models import UnifiedNotificationConfig
from apps.scheduler.models import ScheduleConfig


class ScheduleConfigSerializer(serializers.ModelSerializer):
    """定时任务调度配置序列化器"""

    notification_configs = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=UnifiedNotificationConfig.objects.all(),
        required=False,
    )

    class Meta:
        model = ScheduleConfig
        fields = '__all__'
