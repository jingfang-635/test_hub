# Generated to align the Element model with the actual ui_elements.order column.
# 说明：历史环境里 ui_elements 表已存在 `order int NOT NULL` 列，但 Django 模型此前未声明该字段，
# 导致严格模式(STRICT_TRANS_TABLES)下 Element.objects.create() 报 1364 错误。
# 本迁移通过 SeparatedDatabaseAndState 保证幂等：已有列则跳过 DDL，仅在模型状态中登记该字段。

from django.db import migrations, models


def _has_order_column(schema_editor) -> bool:
    connection = schema_editor.connection
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'ui_elements' AND COLUMN_NAME = 'order'"
        )
        return cursor.fetchone()[0] > 0


def add_order_column(apps, schema_editor):
    if not _has_order_column(schema_editor):
        schema_editor.execute(
            "ALTER TABLE ui_elements ADD COLUMN `order` integer NOT NULL DEFAULT 0"
        )


def remove_order_column(apps, schema_editor):
    if _has_order_column(schema_editor):
        schema_editor.execute("ALTER TABLE ui_elements DROP COLUMN `order`")


class Migration(migrations.Migration):

    dependencies = [
        ('ui_automation', '0006_codegen_conversion'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='element',
                    name='order',
                    field=models.IntegerField(default=0, verbose_name='排序'),
                ),
            ],
            database_operations=[
                migrations.RunPython(add_order_column, remove_order_column),
            ],
        ),
    ]
