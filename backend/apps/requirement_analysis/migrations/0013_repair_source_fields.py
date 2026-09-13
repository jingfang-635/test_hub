# Generated manually: repair schema drift
#
# 背景：django_migrations 记录了 0003（source_type/source_url），
# 但部分数据库实际缺少这两个字段。这里做幂等补齐。

from django.db import migrations


def repair_schema(apps, schema_editor):
    connection = schema_editor.connection
    existing_tables = set(connection.introspection.table_names())

    model = apps.get_model('requirement_analysis', 'TestCaseGenerationTask')
    table = model._meta.db_table
    if table not in existing_tables:
        return
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
        ('requirement_analysis', '0012_add_figma_source_type'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[],
            database_operations=[
                migrations.RunPython(repair_schema, noop_reverse),
            ],
        ),
    ]
