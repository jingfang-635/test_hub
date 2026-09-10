from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


BUILTIN_SKILLS = [
    {
        'name': 'api-testcase-generator',
        'description': '根据接口文档（OpenAPI/Swagger/文本描述）自动生成结构化 API 测试用例，覆盖正常流、异常流与边界条件。',
        'tags': ['api', 'testing', 'generator'],
        'content': '# API Testcase Generator\n\n根据接口定义生成可执行的 API 测试用例。\n',
        'files': {
            'references/openapi-tips.md': '# OpenAPI Tips\n解析 paths / schemas 时优先关注必填字段与枚举值。\n',
            'scripts/normalize_case.py': '# normalize generated cases\n',
        },
        'is_builtin': True,
        'is_enabled': True,
    },
    {
        'name': 'test-case-review',
        'description': '对已有测试用例进行质量评审：检查覆盖度、断言完整性、步骤可执行性，并给出改进建议。',
        'tags': ['testing', 'qa', 'review'],
        'content': '# Test Case Review\n\n评审测试用例质量并输出问题清单。\n',
        'files': {
            'references/review-checklist.md': '# Review Checklist\n- 前置条件是否清晰\n- 步骤是否可复现\n- 期望结果是否可验证\n',
        },
        'is_builtin': True,
        'is_enabled': True,
    },
    {
        'name': 'ui-page-object-generator',
        'description': '基于页面结构或截图描述生成 Page Object 代码骨架，统一元素定位与业务操作封装。',
        'tags': ['ui', 'page-object', 'automation'],
        'content': '# UI Page Object Generator\n\n生成可维护的 Page Object。\n',
        'files': {
            'references/locator-strategy.md': '# Locator Strategy\n优先 data-testid / role，避免脆弱 XPath。\n',
            'scripts/scaffold_po.py': '# scaffold page object\n',
        },
        'is_builtin': True,
        'is_enabled': True,
    },
    {
        'name': 'requirement-analyzer',
        'description': '解析需求文档，提炼功能点、业务规则与验收标准，为用例生成提供结构化输入。',
        'tags': ['requirement', 'analysis'],
        'content': '# Requirement Analyzer\n\n从需求文档中提取可测试点。\n',
        'files': {
            'references/acceptance-criteria.md': '# Acceptance Criteria\n使用 Given/When/Then 描述验收标准。\n',
        },
        'is_builtin': True,
        'is_enabled': True,
    },
    {
        'name': 'boundary-value-designer',
        'description': '针对输入字段自动设计边界值与等价类测试数据，补齐易遗漏的极端场景。',
        'tags': ['data', 'boundary', 'qa'],
        'content': '# Boundary Value Designer\n\n设计边界值测试数据。\n',
        'files': {},
        'is_builtin': True,
        'is_enabled': True,
    },
    {
        'name': 'allure-report-summarizer',
        'description': '汇总 Allure 报告中的失败用例与趋势，输出可读的测试结论与风险提示。',
        'tags': ['report', 'allure', 'summary'],
        'content': '# Allure Report Summarizer\n\n总结测试报告关键结论。\n',
        'files': {
            'references/summary-template.md': '# Summary Template\n通过率 / 失败 TopN / 建议。\n',
            'scripts/parse_summary.py': '# parse allure summary\n',
        },
        'is_builtin': True,
        'is_enabled': True,
    },
    {
        'name': 'api-contract-checker',
        'description': '对比接口契约与实际响应，检测字段缺失、类型不匹配与 Breaking Change。',
        'tags': ['api', 'contract', 'qa'],
        'content': '# API Contract Checker\n\n检查接口契约一致性。\n',
        'files': {
            'references/breaking-changes.md': '# Breaking Changes\n删除字段、变更必填、类型收窄等。\n',
        },
        'is_builtin': True,
        'is_enabled': True,
    },
    {
        'name': 'flaky-test-investigator',
        'description': '分析偶发失败用例日志与重试记录，定位不稳定根因并给出稳定化建议。',
        'tags': ['flaky', 'debug', 'automation'],
        'content': '# Flaky Test Investigator\n\n排查不稳定用例。\n',
        'files': {
            'references/common-causes.md': '# Common Causes\n时序依赖、环境抖动、硬编码等待。\n',
            'scripts/cluster_failures.py': '# cluster failure messages\n',
        },
        'is_builtin': True,
        'is_enabled': True,
    },
]


def seed_builtin_skills(apps, schema_editor):
    Skill = apps.get_model('core', 'Skill')
    for item in BUILTIN_SKILLS:
        Skill.objects.update_or_create(
            name=item['name'],
            defaults={
                'description': item['description'],
                'tags': item['tags'],
                'content': item['content'],
                'files': item['files'],
                'is_builtin': item['is_builtin'],
                'is_enabled': item['is_enabled'],
            },
        )


def unseed_builtin_skills(apps, schema_editor):
    Skill = apps.get_model('core', 'Skill')
    Skill.objects.filter(name__in=[s['name'] for s in BUILTIN_SKILLS], is_builtin=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0004_notificationtemplate_description_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Skill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='唯一标识，如 api-testcase-generator', max_length=100, unique=True, verbose_name='技能名称')),
                ('description', models.TextField(blank=True, verbose_name='技能描述')),
                ('tags', models.JSONField(blank=True, default=list, verbose_name='标签')),
                ('content', models.TextField(blank=True, verbose_name='SKILL.md 内容')),
                ('files', models.JSONField(blank=True, default=dict, help_text='相对路径 -> 文件内容，如 references/guide.md', verbose_name='附属文件')),
                ('is_enabled', models.BooleanField(default=True, verbose_name='是否启用')),
                ('is_builtin', models.BooleanField(default=False, verbose_name='是否内置')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_skills', to=settings.AUTH_USER_MODEL, verbose_name='创建者')),
            ],
            options={
                'verbose_name': 'Skill 技能',
                'verbose_name_plural': 'Skill 技能',
                'db_table': 'core_skills',
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='skill',
            index=models.Index(fields=['is_enabled'], name='core_skills_is_enab_7f2a1c_idx'),
        ),
        migrations.AddIndex(
            model_name='skill',
            index=models.Index(fields=['is_builtin'], name='core_skills_is_buil_9c4e2d_idx'),
        ),
        migrations.RunPython(seed_builtin_skills, unseed_builtin_skills),
    ]
