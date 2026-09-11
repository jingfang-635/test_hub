from django.contrib import admin

from apps.scheduler.models import ScheduleConfig


@admin.register(ScheduleConfig)
class ScheduleConfigAdmin(admin.ModelAdmin):
    list_display = ('module', 'task_type', 'status', 'last_run_time', 'success_count', 'failure_count')
    list_filter = ['module', 'status']
    readonly_fields = ['last_run_time', 'success_count', 'failure_count', 'created_at']
