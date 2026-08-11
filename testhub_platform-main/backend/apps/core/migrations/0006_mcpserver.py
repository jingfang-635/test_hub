from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0005_skill'),
    ]

    operations = [
        migrations.CreateModel(
            name='MCPServer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='服务器名称')),
                ('description', models.TextField(blank=True, verbose_name='描述')),
                ('transport', models.CharField(
                    choices=[('stdio', 'stdio'), ('sse', 'SSE'), ('http', 'HTTP')],
                    default='stdio',
                    max_length=20,
                    verbose_name='传输方式',
                )),
                ('command', models.CharField(
                    blank=True,
                    help_text='stdio 模式：可执行文件，如 npx / python',
                    max_length=255,
                    verbose_name='启动命令',
                )),
                ('args', models.JSONField(blank=True, default=list, verbose_name='启动参数')),
                ('env', models.JSONField(blank=True, default=dict, verbose_name='环境变量')),
                ('url', models.URLField(blank=True, help_text='sse / http 模式使用', verbose_name='服务器 URL')),
                ('is_enabled', models.BooleanField(default=True, verbose_name='是否启用')),
                ('connection_status', models.CharField(
                    choices=[
                        ('unknown', '未知'),
                        ('connected', '已连接'),
                        ('disconnected', '未连接'),
                        ('error', '错误'),
                    ],
                    default='unknown',
                    max_length=20,
                    verbose_name='连接状态',
                )),
                ('tools', models.JSONField(blank=True, default=list, verbose_name='已发现工具')),
                ('last_error', models.TextField(blank=True, verbose_name='最近错误')),
                ('last_tested_at', models.DateTimeField(blank=True, null=True, verbose_name='最近测试时间')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('created_by', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='created_mcp_servers',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='创建者',
                )),
            ],
            options={
                'verbose_name': 'MCP 服务器',
                'verbose_name_plural': 'MCP 服务器',
                'db_table': 'core_mcp_servers',
                'ordering': ['name'],
                'indexes': [
                    models.Index(fields=['is_enabled'], name='core_mcp_se_is_enab_idx'),
                    models.Index(fields=['connection_status'], name='core_mcp_se_connect_idx'),
                ],
            },
        ),
    ]
