"""生成设置收敛为单例超时时间，并把「启用AI评审和改进」下沉到生成任务。

变更：
1. TestCaseGenerationTask 新增 enable_auto_review（按次选择，与任务一起固化）。
2. GenerationConfig 删除 name / default_output_mode / enable_auto_review / is_active，
   只保留 review_timeout 作为全局超时设置。

注意：老库中 generation_config 表可能残留 NOT NULL 且无默认值的 name 列，
直接 DROP 其它列会因缺少 name 值而失败，因此删除前先给历史行补上名称。
"""
from django.db import migrations, models


def ensure_name_filled(apps, schema_editor):
    """历史行可能 name 为空/无默认值，删除列前先补值，避免 DROP 时报错。"""
    connection = schema_editor.connection
    model = apps.get_model('requirement_analysis', 'GenerationConfig')
    table = model._meta.db_table
    if table not in set(connection.introspection.table_names()):
        return
    with connection.cursor() as cursor:
        cursor.execute(f"SHOW COLUMNS FROM `{table}`")
        columns = {row[0] for row in cursor.fetchall()}
        if 'name' in columns:
            cursor.execute(f"UPDATE `{table}` SET `name` = %s WHERE `name` IS NULL OR `name` = ''",
                           ['生成设置'])


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0016_role_multi_value'),
    ]

    operations = [
        migrations.AddField(
            model_name='testcasegenerationtask',
            name='enable_auto_review',
            field=models.BooleanField(
                default=True,
                help_text='生成完成后自动进行AI评审，并根据评审意见改进测试用例',
                verbose_name='启用AI评审和改进',
            ),
        ),
        migrations.RunPython(ensure_name_filled, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='generationconfig',
            name='name',
        ),
        migrations.RemoveField(
            model_name='generationconfig',
            name='default_output_mode',
        ),
        migrations.RemoveField(
            model_name='generationconfig',
            name='enable_auto_review',
        ),
        migrations.RemoveField(
            model_name='generationconfig',
            name='is_active',
        ),
        migrations.AlterModelOptions(
            name='generationconfig',
            options={'verbose_name': '生成设置', 'verbose_name_plural': '生成设置'},
        ),
    ]
