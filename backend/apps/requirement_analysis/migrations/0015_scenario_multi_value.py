"""scenario 由单值改为多值列表（一个配置可服务多个场景）。

MySQL 无法把 varchar 中的 'testcase_generation' 直接 CAST 成 JSON，
因此分三步：拓宽列为 LONGTEXT -> 归一化为 JSON 数组文本 -> AlterField 转 JSON。
"""
import json

from django.db import migrations, models


def _normalize(value):
    """把历史单值/逗号串统一归一化为场景列表。"""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if v]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        # 已经是 JSON 数组文本（重复执行/其他环境）
        if text.startswith('['):
            try:
                parsed = json.loads(text)
            except (ValueError, TypeError):
                pass
            else:
                if isinstance(parsed, list):
                    return [str(v) for v in parsed if v]
                return [str(parsed)]
        # 兼容早期前端误提交的逗号分隔串
        return [part.strip() for part in text.split(',') if part.strip()]
    return [str(value)]


def forwards(apps, schema_editor):
    model = apps.get_model('requirement_analysis', 'AIModelConfig')
    table = model._meta.db_table
    column = 'scenario'
    connection = schema_editor.connection
    quote = schema_editor.quote_name

    # 1) 放宽列长度，避免多值 JSON 文本被 varchar(30) 截断
    if connection.vendor == 'mysql':
        with connection.cursor() as cursor:
            cursor.execute(
                f'ALTER TABLE {quote(table)} MODIFY {quote(column)} LONGTEXT NULL'
            )

    # 2) 读出并归一化
    with connection.cursor() as cursor:
        cursor.execute(f'SELECT id, {quote(column)} FROM {quote(table)}')
        rows = cursor.fetchall()

    with connection.cursor() as cursor:
        for pk, raw in rows:
            cursor.execute(
                f'UPDATE {quote(table)} SET {quote(column)} = %s WHERE id = %s',
                [json.dumps(_normalize(raw), ensure_ascii=False), pk],
            )


def backwards(apps, schema_editor):
    """回滚：多个场景用逗号连接（供 varchar 兼容，仅保留可读文本）。"""
    model = apps.get_model('requirement_analysis', 'AIModelConfig')
    table = model._meta.db_table
    column = 'scenario'
    connection = schema_editor.connection
    quote = schema_editor.quote_name

    if connection.vendor == 'mysql':
        with connection.cursor() as cursor:
            cursor.execute(
                f'ALTER TABLE {quote(table)} MODIFY {quote(column)} LONGTEXT NULL'
            )

    with connection.cursor() as cursor:
        cursor.execute(f'SELECT id, {quote(column)} FROM {quote(table)}')
        rows = cursor.fetchall()

    with connection.cursor() as cursor:
        for pk, raw in rows:
            cursor.execute(
                f'UPDATE {quote(table)} SET {quote(column)} = %s WHERE id = %s',
                [','.join(_normalize(raw)), pk],
            )


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0014_add_scenario_to_ai_model_config'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='aimodelconfig',
            name='ai_model_co_scenari_1ae966_idx',
        ),
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name='aimodelconfig',
            name='scenario',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='用途场景列表，一个配置可服务多个场景',
                verbose_name='用途场景',
            ),
        ),
    ]
