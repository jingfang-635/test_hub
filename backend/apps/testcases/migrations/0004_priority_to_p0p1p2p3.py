from django.db import migrations, models

# 旧值 -> 新值 映射
PRIORITY_MIGRATION_MAP = {
    'low': 'P3',
    'medium': 'P2',
    'high': 'P1',
    'critical': 'P0',
}


def forwards_func(apps, schema_editor):
    TestCase = apps.get_model('testcases', 'TestCase')
    for old, new in PRIORITY_MIGRATION_MAP.items():
        TestCase.objects.filter(priority=old).update(priority=new)


def reverse_func(apps, schema_editor):
    TestCase = apps.get_model('testcases', 'TestCase')
    for old, new in PRIORITY_MIGRATION_MAP.items():
        TestCase.objects.filter(priority=new).update(priority=old)


class Migration(migrations.Migration):

    dependencies = [
        ('testcases', '0003_testcase_l1_testcase_l2_testcase_l3'),
    ]

    operations = [
        migrations.RunPython(forwards_func, reverse_func),
        migrations.AlterField(
            model_name='testcase',
            name='priority',
            field=models.CharField(
                choices=[('P0', 'P0'), ('P1', 'P1'), ('P2', 'P2'), ('P3', 'P3')],
                default='P2',
                max_length=20,
                verbose_name='优先级',
            ),
        ),
    ]
