# Generated manually: repair schema drift
#
# 背景：部分数据库的 django_migrations 把 0003/0004 等记录为「已应用」，
# 但实际表/字段并未创建（历史迁移被删或因导入/恢复导致状态与结构不一致）。
# 这里按当前模型状态做幂等补齐，缺失才创建，已存在则跳过。
# 与 ui_automation/0012 的修复思路一致。

from django.db import migrations


def _existing_tables(connection):
    return set(connection.introspection.table_names())


def _existing_columns(connection, table):
    with connection.cursor() as cursor:
        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
        return {row[0] for row in cursor.fetchall()}


def repair_schema(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = _existing_tables(connection)

    # 1) 先补建缺失的表（notification_templates 需先于其外键存在）
    for model_name in ('NotificationTemplate', 'PerformanceStatistics', 'RequestPerformanceLog'):
        model = apps.get_model('core', model_name)
        if model._meta.db_table not in existing_tables:
            schema_editor.create_model(model)
            existing_tables.add(model._meta.db_table)

    # 2) 再补 unified_notification_configs 缺失字段
    UnifiedNotificationConfig = apps.get_model('core', 'UnifiedNotificationConfig')
    table = UnifiedNotificationConfig._meta.db_table
    if table in existing_tables:
        db_columns = _existing_columns(connection, table)
        for field in UnifiedNotificationConfig._meta.local_fields:
            if field.column not in db_columns:
                schema_editor.add_field(UnifiedNotificationConfig, field)
                db_columns.add(field.column)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_rename_core_mcp_se_is_enab_idx_core_mcp_se_is_enab_982cda_idx_and_more'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunPython(repair_schema, noop_reverse),
            ],
        ),
    ]
