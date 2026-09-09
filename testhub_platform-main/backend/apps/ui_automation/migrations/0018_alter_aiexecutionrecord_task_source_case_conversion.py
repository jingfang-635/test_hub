from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ui_automation', '0017_aiexecutionrecord_source_file'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aiexecutionrecord',
            name='task_source',
            field=models.CharField(max_length=20, verbose_name='任务来源'),
        ),
    ]
