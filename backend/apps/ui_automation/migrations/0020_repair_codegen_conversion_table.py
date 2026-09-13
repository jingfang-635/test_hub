# Generated manually: repair schema drift
#
# 背景：django_migrations 记录了 0006_codegen_conversion，
# 但部分数据库实际缺少 ui_codegen_conversions 表。这里做幂等补齐。

from django.db import migrations


def repair_schema(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())

    model = apps.get_model('ui_automation', 'CodegenConversion')
    if model._meta.db_table not in existing_tables:
        schema_editor.create_model(model)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('ui_automation', '0019_testcase_hub_testcase'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunPython(repair_schema, noop_reverse),
            ],
        ),
    ]
