from django.apps import AppConfig


class UiAutomationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ui_automation'
    verbose_name = 'UI自动化测试'

    def ready(self):
        # 保证「添加/编辑元素」时定位策略下拉框有数据。
        # Docker 由 entrypoint.sh 显式执行 init_locator_strategies；
        # 本地启动（start.bat / IDE 等）未执行该命令，故在此兜底自动初始化。
        try:
            from apps.ui_automation.models import LocatorStrategy
            from apps.core.management.commands.init_locator_strategies import DEFAULT_LOCATOR_STRATEGIES

            # 按 name 幂等写入，避免多进程/重复启动产生重复策略（下拉会显示两遍）
            for item in DEFAULT_LOCATOR_STRATEGIES:
                LocatorStrategy.objects.get_or_create(
                    name=item['name'],
                    defaults={'description': item['description']},
                )
        except Exception:
            # 数据库表尚未就绪（例如首次 migrate 阶段），待迁移完成后正常启动时再初始化
            pass