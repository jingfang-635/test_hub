from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('testcases', '0004_priority_to_p0p1p2p3'),
    ]

    operations = [
        migrations.AddField(
            model_name='testcase',
            name='case_type',
            field=models.CharField(
                choices=[('manual', '手工'), ('ui', 'UI'), ('api', '接口')],
                default='manual',
                max_length=20,
                verbose_name='用例类型',
            ),
        ),
    ]