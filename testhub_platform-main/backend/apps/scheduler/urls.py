from rest_framework.routers import DefaultRouter

from apps.scheduler.views import ScheduleConfigViewSet

router = DefaultRouter()
router.register(r'schedule_configs', ScheduleConfigViewSet, basename='scheduleconfig')

urlpatterns = router.urls
