from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('requirement_analysis', '0010_knowledgedocument_vector_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='knowledgebasellmconfig',
            name='tika_server_url',
            field=models.URLField(
                default='http://localhost:9987',
                help_text='用于解析 PDF、Word 等文档的 Tika Server 地址',
                max_length=500,
                verbose_name='Tika 服务地址',
            ),
        ),
        migrations.RemoveField(
            model_name='knowledgebasellmconfig',
            name='vision_api_key',
        ),
        migrations.RemoveField(
            model_name='knowledgebasellmconfig',
            name='vision_base_url',
        ),
        migrations.RemoveField(
            model_name='knowledgebasellmconfig',
            name='vision_model_name',
        ),
        migrations.RemoveField(
            model_name='knowledgebasellmconfig',
            name='vision_provider',
        ),
    ]
