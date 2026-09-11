# Generated manually for Feishu source tracing

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0002_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='testcasegenerationtask',
            name='source_type',
            field=models.CharField(
                choices=[
                    ('manual', '手动输入'),
                    ('upload', '文档上传'),
                    ('feishu', '飞书文档'),
                ],
                default='manual',
                max_length=20,
                verbose_name='需求来源类型',
            ),
        ),
        migrations.AddField(
            model_name='testcasegenerationtask',
            name='source_url',
            field=models.URLField(
                blank=True,
                default='',
                max_length=1000,
                verbose_name='需求来源链接',
            ),
        ),
    ]
