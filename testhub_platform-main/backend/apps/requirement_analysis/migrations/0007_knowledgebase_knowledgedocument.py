from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('projects', '0002_initial'),
        ('requirement_analysis', '0006_alter_feishuuserauth_scope'),
    ]

    operations = [
        migrations.CreateModel(
            name='KnowledgeBase',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200, verbose_name='知识库名称')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('is_active', models.BooleanField(default=True, verbose_name='是否启用')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('created_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name='knowledge_bases', to=settings.AUTH_USER_MODEL, verbose_name='创建者'
                )),
                ('project', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name='knowledge_bases', to='projects.project', verbose_name='关联项目'
                )),
            ],
            options={
                'verbose_name': '知识库',
                'verbose_name_plural': '知识库',
                'db_table': 'knowledge_bases',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='KnowledgeDocument',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200, verbose_name='文档标题')),
                ('file', models.FileField(upload_to='knowledge_docs/%Y/%m/', verbose_name='文档文件')),
                ('document_type', models.CharField(
                    choices=[
                        ('pdf', 'PDF文档'),
                        ('docx', 'Word文档'),
                        ('txt', '文本文档'),
                        ('md', 'Markdown文档'),
                    ],
                    max_length=10,
                    verbose_name='文档类型'
                )),
                ('status', models.CharField(
                    choices=[
                        ('uploaded', '已上传'),
                        ('processing', '处理中'),
                        ('ready', '已就绪'),
                        ('failed', '处理失败'),
                    ],
                    default='uploaded',
                    max_length=20,
                    verbose_name='状态'
                )),
                ('file_size', models.PositiveIntegerField(blank=True, null=True, verbose_name='文件大小(bytes)')),
                ('extracted_text', models.TextField(blank=True, verbose_name='提取的文本内容')),
                ('error_message', models.TextField(blank=True, verbose_name='错误信息')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('knowledge_base', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='documents', to='requirement_analysis.knowledgebase', verbose_name='所属知识库'
                )),
                ('uploaded_by', models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                    related_name='uploaded_knowledge_documents', to=settings.AUTH_USER_MODEL, verbose_name='上传者'
                )),
            ],
            options={
                'verbose_name': '知识库文档',
                'verbose_name_plural': '知识库文档',
                'db_table': 'knowledge_documents',
                'ordering': ['-created_at'],
            },
        ),
    ]
