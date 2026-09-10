from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.scheduler.models import ScheduleConfig
from apps.scheduler.serializers import ScheduleConfigSerializer


class ScheduleConfigViewSet(viewsets.ModelViewSet):
    """定时任务调度配置视图集"""
    queryset = ScheduleConfig.objects.select_related('schedule', 'notification_template').all()
    serializer_class = ScheduleConfigSerializer

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """暂停定时任务"""
        obj = self.get_object()
        obj.pause()
        return Response({'status': 'paused', 'message': '任务已暂停'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """恢复定时任务"""
        obj = self.get_object()
        obj.resume()
        return Response({'status': 'active', 'message': '任务已恢复'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def execute_now(self, request, pk=None):
        """立即执行定时任务"""
        obj = self.get_object()
        task_id = obj.execute_now()
        return Response({'task_id': task_id, 'message': '任务已开始执行'}, status=status.HTTP_200_OK)
