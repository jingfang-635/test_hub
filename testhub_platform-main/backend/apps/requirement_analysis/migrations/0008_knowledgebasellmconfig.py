from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('requirement_analysis', '0007_knowledgebase_knowledgedocument'),
    ]

    operations = [
        migrations.CreateModel(
            name='KnowledgeBaseLLMConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('embedding_api_key', models.CharField(blank=True, default='', max_length=500, verbose_name='Embedding API Key')),
                ('embedding_base_url', models.URLField(default='https://dashscope.aliyuncs.com/compatible-mode/v1', max_length=500, verbose_name='Embedding Base URL')),
                ('embedding_model_name', models.CharField(default='text-embedding-v3', max_length=100, verbose_name='Embedding 模型名称')),
                ('refiner_api_key', models.CharField(blank=True, default='', max_length=500, verbose_name='Refiner API Key')),
                ('refiner_base_url', models.URLField(default='https://dashscope.aliyuncs.com/compatible-mode/v1', max_length=500, verbose_name='Refiner Base URL')),
                ('refiner_model_name', models.CharField(default='qwen-plus', max_length=100, verbose_name='Refiner 模型名称')),
                ('refiner_max_tokens', models.IntegerField(default=8192, verbose_name='Refiner 最大Token数')),
                ('refiner_temperature', models.FloatField(default=0.3, verbose_name='Refiner 温度')),
                ('vision_provider', models.CharField(choices=[('zhipu', '智谱（文件解析API）'), ('openai_compatible', 'OpenAI兼容（视觉模型）')], default='openai_compatible', max_length=30, verbose_name='Vision 服务商')),
                ('vision_api_key', models.CharField(blank=True, default='', max_length=500, verbose_name='Vision API Key')),
                ('vision_base_url', models.URLField(blank=True, default='https://open.bigmodel.cn/api/paas/v4', max_length=500, verbose_name='Vision Base URL')),
                ('vision_model_name', models.CharField(blank=True, default='glm-4.6v', max_length=100, verbose_name='Vision 模型名称')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='knowledge_llm_configs', to=settings.AUTH_USER_MODEL, verbose_name='创建者')),
            ],
            options={
                'verbose_name': '知识库大模型配置',
                'verbose_name_plural': '知识库大模型配置',
                'db_table': 'knowledge_base_llm_configs',
                'ordering': ['-updated_at'],
            },
        ),
    ]
