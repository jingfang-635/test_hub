from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = '核心模块'

    def ready(self):
        # 改 config.yaml 时触发 runserver 自动重载，否则 FEISHU_* 等配置不会生效
        try:
            from django.utils.autoreload import autoreload_started
            from config_loader import _YAML_PATH

            def _watch_config_yaml(sender, **kwargs):
                if _YAML_PATH.exists():
                    sender.extra_files.add(_YAML_PATH)

            autoreload_started.connect(_watch_config_yaml, weak=False)
        except Exception:
            pass
