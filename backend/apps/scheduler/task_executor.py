"""
scheduler 统一调度任务执行器
- get_task_function: 任务类型 -> 任务函数路径
- execute_task: 立即异步执行某个 ScheduleConfig 对应的任务
- create_scheduled_task: 统一创建 django_q.Schedule + ScheduleConfig 的入口
"""
from django.utils import timezone
from django_q.models import Schedule
from django_q.tasks import async_task

from apps.scheduler.models import ScheduleConfig


# 任务类型 -> 任务函数的 dotted import 路径
TASK_FUNCTION_MAPPING = {
    'API_TEST_SUITE': 'apps.api_testing.tasks.execute_api_test_suite',
    'API_REQUEST': 'apps.api_testing.tasks.execute_api_request',
    'UI_TEST_SUITE': 'apps.ui_automation.tasks.execute_ui_test_suite',
    'UI_TEST_CASE': 'apps.ui_automation.tasks.execute_ui_test_case',
    'APP_TEST_SUITE': 'apps.app_automation.tasks.execute_app_suite_task',
    'APP_TEST_CASE': 'apps.app_automation.tasks.execute_app_test_task',
}


def get_task_function(task_type):
    """根据任务类型返回对应的任务函数路径字符串"""
    if task_type not in TASK_FUNCTION_MAPPING:
        raise ValueError(f"未知的任务类型: {task_type}")
    return TASK_FUNCTION_MAPPING[task_type]


def execute_task(schedule_id):
    """
    根据 schedule_id 获取 ScheduleConfig，通过 async_task 异步执行对应任务，
    并更新 last_run_time 与 success_count/failure_count（异常时 failure_count += 1）。
    返回 async_task 的 task_id。
    """
    config = ScheduleConfig.objects.get(schedule_id=schedule_id)
    func_path = get_task_function(config.task_type)
    config.last_run_time = timezone.now()

    try:
        task_id = async_task(func_path, **(config.task_config or {}))
        config.success_count += 1
        config.save(update_fields=['last_run_time', 'success_count'])
        return task_id
    except Exception:
        config.failure_count += 1
        config.save(update_fields=['last_run_time', 'failure_count'])
        raise


def create_scheduled_task(name, module, task_type, schedule_type, target_id=None,
                          project_id=None, environment_id=None, task_config=None,
                          cron=None, minutes=None, notification_template=None, **kwargs):
    """
    统一创建定时任务入口：
    1. 调用 get_task_function 获取任务函数路径；
    2. 用 django_q Schedule.objects.create 创建 Schedule（根据 schedule_type 设置 cron 或 minutes）；
    3. 创建 ScheduleConfig；
    返回 (schedule, config)。
    """
    func_path = get_task_function(task_type)
    task_config = task_config or {}

    schedule_kwargs = {
        'name': name,
        'func': func_path,
        'schedule_type': schedule_type,
    }
    # CRON 类型设置 cron 表达式
    if schedule_type == 'C' and cron:
        schedule_kwargs['cron'] = cron
    # INTERVAL(MINUTES) 类型设置 minutes
    if schedule_type == 'I' and minutes is not None:
        schedule_kwargs['minutes'] = minutes
    # django_q Schedule.kwargs 为 TextField（ast.literal_eval 解析），
    # 用 dict 字面量字符串存储任务配置，使 cron 触发时任务能收到对应参数
    if task_config:
        schedule_kwargs['kwargs'] = str(task_config)

    schedule = Schedule.objects.create(**schedule_kwargs)

    config_kwargs = {
        'schedule': schedule,
        'module': module,
        'task_type': task_type,
        'project_id': project_id,
        'target_id': target_id,
        'environment_id': environment_id,
        'task_config': task_config,
    }
    # notification_template 既支持传入 ID，也支持传入模型实例
    if notification_template is not None:
        if isinstance(notification_template, int):
            config_kwargs['notification_template_id'] = notification_template
        else:
            config_kwargs['notification_template'] = notification_template

    config = ScheduleConfig.objects.create(**config_kwargs)
    return schedule, config
