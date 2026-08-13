# Generated manually for CodegenConversion pipeline

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ui_automation', '0005_uiproject_hub_project'),
    ]

    operations = [
        migrations.CreateModel(
            name='CodegenConversion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scenario', models.CharField(max_length=200, verbose_name='场景名')),
                ('language', models.CharField(
                    choices=[('python', 'Python'), ('javascript', 'JavaScript')],
                    default='python', max_length=20, verbose_name='语言'
                )),
                ('target_url', models.CharField(blank=True, default='', max_length=1000, verbose_name='目标URL')),
                ('recorded_name', models.CharField(blank=True, default='', max_length=255, verbose_name='录制文件名')),
                ('recorded_content', models.TextField(verbose_name='录制脚本内容')),
                ('parse_result', models.JSONField(blank=True, default=dict, verbose_name='解析结果')),
                ('plan_md', models.TextField(blank=True, default='', verbose_name='用例计划Markdown')),
                ('plan_status', models.CharField(
                    choices=[('draft', '待确认'), ('confirmed', '已确认')],
                    default='draft', max_length=20, verbose_name='计划状态'
                )),
                ('user_cases_md', models.TextField(blank=True, default='', verbose_name='用户提供用例')),
                ('generated_files', models.JSONField(blank=True, default=list, verbose_name='生成文件列表')),
                ('generated_script_ids', models.JSONField(blank=True, default=list, verbose_name='生成脚本ID')),
                ('generated_page_object_ids', models.JSONField(blank=True, default=list, verbose_name='生成页面对象ID')),
                ('status', models.CharField(
                    choices=[
                        ('parsed', '已解析'),
                        ('plan_ready', '计划已生成'),
                        ('confirmed', '计划已确认'),
                        ('generated', '脚本已生成'),
                        ('failed', '失败'),
                    ],
                    default='parsed', max_length=20, verbose_name='流水线状态'
                )),
                ('error', models.TextField(blank=True, default='', verbose_name='错误信息')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('project', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='codegen_conversions',
                    to='ui_automation.uiproject',
                    verbose_name='所属项目',
                )),
                ('source_script', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='codegen_conversions',
                    to='ui_automation.testscript',
                    verbose_name='来源原始脚本',
                )),
                ('user', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='codegen_conversions',
                    to=settings.AUTH_USER_MODEL,
                    verbose_name='创建人',
                )),
            ],
            options={
                'verbose_name': 'Codegen转换流水线',
                'verbose_name_plural': 'Codegen转换流水线',
                'db_table': 'ui_codegen_conversions',
                'ordering': ['-created_at'],
            },
        ),
    ]
