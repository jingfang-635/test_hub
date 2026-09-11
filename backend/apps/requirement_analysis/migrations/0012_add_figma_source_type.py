# Generated manually for Figma source type

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0011_replace_vision_with_tika'),
    ]

    operations = [
        migrations.AlterField(
            model_name='testcasegenerationtask',
            name='source_type',
            field=models.CharField(
                choices=[
                    ('manual', '手动输入'),
                    ('upload', '文档上传'),
                    ('feishu', '飞书文档'),
                    ('figma', 'Figma设计稿'),
                ],
                default='manual',
                max_length=20,
                verbose_name='需求来源类型',
            ),
        ),
    ]
