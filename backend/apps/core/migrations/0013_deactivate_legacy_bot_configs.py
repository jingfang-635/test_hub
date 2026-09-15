# 下线企微/钉钉机器人配置（仅保留飞书）。
#
# 背景：UnifiedNotificationConfig 的 config_type 已移除 webhook_wechat / webhook_dingtalk，
# 前端与发送逻辑也不再支持这两种机器人。但历史数据可能仍存在这两类配置。
#
# 处理方式：不做物理删除 —— TaskNotificationSetting / UiTaskNotificationSetting 等
# 通过外键引用这些配置，删除会把引用置空；这里改为标记 is_active=False，使其彻底失效，
# 同时保留数据以便回溯。

from django.db import migrations

LEGACY_CONFIG_TYPES = ['webhook_wechat', 'webhook_dingtalk']


def deactivate_legacy_configs(apps, schema_editor):
    UnifiedNotificationConfig = apps.get_model('core', 'UnifiedNotificationConfig')
    updated = UnifiedNotificationConfig.objects.filter(
        config_type__in=LEGACY_CONFIG_TYPES
    ).update(is_active=False)
    if updated:
        print(f'  已停用 {updated} 条企微/钉钉通知配置（配置类型已下线）')


def noop_reverse(apps, schema_editor):
    """回滚时不恢复启用状态，避免误启用已下线的机器人配置。"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_email_config'),
    ]

    operations = [
        migrations.RunPython(deactivate_legacy_configs, noop_reverse),
    ]
