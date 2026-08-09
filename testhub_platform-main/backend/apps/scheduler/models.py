from django.db import models


class ScheduleConfig(models.Model):
    """定时任务调度配置模型 - 统一管理 API/UI/APP 自动化定时任务"""

    MODULE_CHOICES = [
        ('API', 'API测试'),
        ('UI', 'UI自动化'),
        ('APP', 'APP自动化'),
    ]

    TASK_TYPE_CHOICES = [
        ('API_TEST_SUITE', 'API测试套件'),
        ('API_REQUEST', 'API请求'),
        ('UI_TEST_SUITE', 'UI测试套件'),
        ('UI_TEST_CASE', 'UI测试用例'),
        ('APP_TEST_SUITE', 'APP测试套件'),
        ('APP_TEST_CASE', 'APP测试用例'),
    ]

    STATUS_CHOICES = [
        ('ACTIVE', '活跃'),
        ('PAUSED', '已暂停'),
    ]

    schedule = models.OneToOneField(
        'django_q.Schedule',
        on_delete=models.CASCADE,
        related_name='config',
        verbose_name='Django-Q调度任务',
    )
    module = models.CharField(max_length=20, choices=MODULE_CHOICES, verbose_name='所属模块')
    task_type = models.CharField(max_length=30, choices=TASK_TYPE_CHOICES, verbose_name='任务类型')
    project_id = models.IntegerField(null=True, blank=True, verbose_name='项目ID')
    target_id = models.IntegerField(null=True, blank=True, verbose_name='目标ID')
    environment_id = models.IntegerField(null=True, blank=True, verbose_name='环境ID')
    task_config = models.JSONField(default=dict, blank=True, verbose_name='任务配置')
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default='ACTIVE', verbose_name='状态'
    )
    notify_on_success = models.BooleanField(default=False, verbose_name='成功时通知')
    notify_on_failure = models.BooleanField(default=True, verbose_name='失败时通知')
    notify_on_email = models.BooleanField(default=False, verbose_name='邮件通知')
    notify_on_webhook = models.BooleanField(default=False, verbose_name='Webhook通知')
    notification_configs = models.ManyToManyField(
        'core.UnifiedNotificationConfig', blank=True, verbose_name='通知配置'
    )
    notification_template = models.ForeignKey(
        'core.NotificationTemplate',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='schedule_configs',
        verbose_name='通知模板',
    )
    last_run_time = models.DateTimeField(null=True, blank=True, verbose_name='最后运行时间')
    success_count = models.IntegerField(default=0, verbose_name='成功次数')
    failure_count = models.IntegerField(default=0, verbose_name='失败次数')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'scheduler_schedule_config'
        verbose_name = '定时任务调度配置'
        verbose_name_plural = '定时任务调度配置'
        ordering = ['-created_at']

    def __str__(self):
        name = getattr(self, 'name', None) or self.schedule.name
        return f"{name} [{self.get_module_display()}]"

    def pause(self):
        """暂停定时任务：置为已暂停并清空下次运行时间"""
        self.status = 'PAUSED'
        self.schedule.next_run = None
        self.schedule.save()
        self.save()

    def resume(self):
        """恢复定时任务：置为活跃并将下次运行时间设为当前时间"""
        from django.utils import timezone
        self.status = 'ACTIVE'
        self.schedule.next_run = timezone.now()
        self.schedule.save()
        self.save()

    def execute_now(self):
        """立即执行定时任务，返回 async_task 的 task_id"""
        from apps.scheduler.task_executor import execute_task
        return execute_task(self.schedule_id)
