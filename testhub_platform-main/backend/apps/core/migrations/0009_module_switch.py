# Generated manually: ModuleSwitch 功能模块开关模型 + 预置模块种子数据

from django.db import migrations, models
import django.db.models.deletion


# 预置 8 个功能模块开关（与前端 layout 侧边栏菜单、Home 首页卡片一一对应）
DEFAULT_MODULES = [
    {'key': 'ai-generation', 'name': 'AI 用例生成', 'description': 'AI 用例生成 / 用例管理', 'location': 'all', 'sort_order': 1},
    {'key': 'api-testing', 'name': '接口测试', 'description': 'API 接口测试', 'location': 'all', 'sort_order': 2},
    {'key': 'ui-automation', 'name': 'UI 自动化测试', 'description': 'UI 自动化测试', 'location': 'all', 'sort_order': 3},
    {'key': 'app-automation', 'name': 'APP 自动化测试', 'description': 'APP 自动化测试', 'location': 'all', 'sort_order': 4},
    {'key': 'ai-intelligent-mode', 'name': 'AI 智能模式', 'description': 'AI 智能模式', 'location': 'all', 'sort_order': 5},
    {'key': 'configuration', 'name': '配置中心', 'description': '配置中心', 'location': 'all', 'sort_order': 6},
    {'key': 'data-factory', 'name': '数据工厂', 'description': '数据工厂（仅首页入口）', 'location': 'home', 'sort_order': 7},
    {'key': 'assistant', 'name': 'AI 评测师', 'description': 'AI 评测师 / 助手（仅首页入口）', 'location': 'home', 'sort_order': 8},
]


def seed_module_switches(apps, schema_editor):
    ModuleSwitch = apps.get_model('core', 'ModuleSwitch')
    for item in DEFAULT_MODULES:
        ModuleSwitch.objects.update_or_create(
            key=item['key'],
            defaults={
                'name': item['name'],
                'description': item['description'],
                'location': item['location'],
                'sort_order': item['sort_order'],
                'is_enabled': True,
                'is_builtin': True,
            },
        )


def unseed_module_switches(apps, schema_editor):
    ModuleSwitch = apps.get_model('core', 'ModuleSwitch')
    ModuleSwitch.objects.filter(key__in=[item['key'] for item in DEFAULT_MODULES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_update_playwright_codegen_skill'),
    ]

    operations = [
        migrations.CreateModel(
            name='ModuleSwitch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(help_text='唯一标识，如 ai-generation / api-testing / data-factory', max_length=50, unique=True, verbose_name='模块标识')),
                ('name', models.CharField(max_length=100, verbose_name='模块名称')),
                ('description', models.CharField(blank=True, max_length=255, verbose_name='模块描述')),
                ('location', models.CharField(choices=[('all', '全局（菜单+首页）'), ('sidebar', '侧边栏菜单'), ('home', '首页入口')], default='all', max_length=20, verbose_name='显示位置')),
                ('sort_order', models.IntegerField(default=0, verbose_name='排序')),
                ('is_enabled', models.BooleanField(default=True, verbose_name='是否启用')),
                ('is_builtin', models.BooleanField(default=True, help_text='内置模块不可删除，避免误删导致入口丢失', verbose_name='是否内置')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
            ],
            options={
                'verbose_name': '功能模块开关',
                'verbose_name_plural': '功能模块开关',
                'db_table': 'core_module_switches',
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='moduleswitch',
            index=models.Index(fields=['is_enabled'], name='core_module__is_enab_6e5f4e_idx'),
        ),
        migrations.AddIndex(
            model_name='moduleswitch',
            index=models.Index(fields=['location'], name='core_module__locatio_5bf6a7_idx'),
        ),
        migrations.RunPython(seed_module_switches, unseed_module_switches),
    ]
