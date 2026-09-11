# Generated manually for HOURLY/DAILY/WEEKLY/MONTHLY/YEARLY trigger types

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ui_automation', '0003_add_page_filter_to_testcasestep'),
    ]

    operations = [
        migrations.AlterField(
            model_name='uischeduledtask',
            name='trigger_type',
            field=models.CharField(
                choices=[
                    ('CRON', 'Cron表达式'),
                    ('INTERVAL', '固定间隔'),
                    ('ONCE', '单次执行'),
                    ('HOURLY', '每小时'),
                    ('DAILY', '每天'),
                    ('WEEKLY', '每周'),
                    ('MONTHLY', '每月'),
                    ('YEARLY', '每年'),
                ],
                max_length=20,
                verbose_name='触发器类型',
            ),
        ),
    ]
