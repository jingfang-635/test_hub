# Generated manually: repair schema drift
#
# 背景：django_migrations 记录了 0003/0004/0005（以及已被删除的 0006），
# 但部分数据库实际缺少这些字段。这里按当前模型状态做幂等补齐。

from django.db import migrations


def repair_schema(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())

    for model_name in ('ApiProject', 'ApiRequest', 'TestSuiteRequest'):
        model = apps.get_model('api_testing', model_name)
        table = model._meta.db_table
        if table not in existing_tables:
            continue
        with connection.cursor() as cursor:
            cursor.execute(f"SHOW COLUMNS FROM `{table}`")
            db_columns = {row[0] for row in cursor.fetchall()}
        for field in model._meta.local_fields:
            if field.column not in db_columns:
                schema_editor.add_field(model, field)
                db_columns.add(field.column)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('api_testing', '0005_testsuiterequest_skip_condition_extractors'),
        ('projects', '0004_projectenvironment_login_credentials'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunPython(repair_schema, noop_reverse),
            ],
        ),
    ]
