"""role 由单值改为多值列表（一个配置可承担多个角色）。

与 0015 的 scenario 迁移同理：MySQL 无法把 varchar 中的 'writer' 直接 CAST 成 JSON，
因此分三步：拓宽列为 LONGTEXT -> 归一化为 JSON 数组文本 -> AlterField 转 JSON。
"""
import json

from django.db import migrations, models


def _normalize(value):
    """把历史单值/逗号串统一归一化为角色列表。"""
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


def _convert_column(apps, schema_editor, column, reverse=False):
    model = apps.get_model('requirement_analysis', 'AIModelConfig')
    table = model._meta.db_table
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

    # 3) 写回：正向存 JSON 文本，反向存逗号串（兼容 varchar）
    with connection.cursor() as cursor:
        for pk, raw in rows:
            values = _normalize(raw)
            new_value = ','.join(values) if reverse else json.dumps(values, ensure_ascii=False)
            cursor.execute(
                f'UPDATE {quote(table)} SET {quote(column)} = %s WHERE id = %s',
                [new_value, pk],
            )


def forwards(apps, schema_editor):
    _convert_column(apps, schema_editor, 'role')


def backwards(apps, schema_editor):
    _convert_column(apps, schema_editor, 'role', reverse=True)


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0015_scenario_multi_value'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name='aimodelconfig',
            name='role',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='角色列表，一个配置可承担多个角色',
                verbose_name='角色',
            ),
        ),
    ]
