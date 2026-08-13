from django.db import migrations


PLAYWRIGHT_SKILLS = [
    {
        'name': 'playwright-codegen',
        'description': '启动 Playwright Codegen 录制 Web 操作，生成 python-pytest/JS 原始脚本，降低 Token 消耗的人工录制入口。',
        'tags': ['ui', 'playwright', 'codegen', 'recording'],
        'content': '''---
name: playwright-codegen
description: 基于 Playwright Codegen 进行人工录制，输出 tests/recorded 原始脚本。用于用户提供 URL 并要求录制 UI 流程、生成基础自动化脚本时。
---

# Playwright Codegen 录制

## 目标

先由人工完成页面操作录制，再交由 AI 基于录制结果生成可执行自动化脚本，降低大模型 Token 消耗。

## 执行流程

1. 检测 `node` / `npx` / `playwright`（或 `python -m playwright`）是否可用
2. 若未安装 Playwright，使用 `npx playwright` 或 `pip install playwright && playwright install` 补齐
3. 启动录制（默认 python-pytest）：

```bash
npx playwright codegen --target python-pytest --browser chromium -o tests/recorded/{name}.py {URL}
# 或
python -m playwright codegen --target python-pytest --browser chromium -o tests/recorded/{name}.py {URL}
```

4. 在打开的浏览器中完整操作业务场景；Inspector 实时生成步骤
5. 在 Inspector 点击停止 / 关闭浏览器结束录制
6. 确认输出文件已写入 `tests/recorded/`（平台侧对应 `media/ui-automation/recorded/`）
7. 回到对话，基于录制脚本继续「生成计划 → 生成代码」

## 输出

- 原始录制脚本：`tests/recorded/*.py|*.js`
- 优先稳健定位器：`getByRole` / `getByLabel` / `getByTestId`
- 可包含可见性、文本、输入值等断言

## 注意

- 复杂验证码场景改用有头模式人工介入
- 录制与执行、修复拆分为独立 Skill，避免单 Skill 职责过重
''',
        'files': {
            'references/codegen-checklist.md': (
                '# Codegen Checklist\n'
                '- URL 是否可访问\n'
                '- 是否覆盖增删改查主路径\n'
                '- 录制结束后确认 -o 文件非空\n'
                '- 下一步调用计划生成 / 代码生成 Skill\n'
            ),
        },
        'is_builtin': True,
        'is_enabled': True,
    },
    {
        'name': 'playwright-test-runner',
        'description': '执行 Playwright/pytest UI 用例并输出 HTML 报告与 Trace，与录制/生成 Skill 解耦。',
        'tags': ['ui', 'playwright', 'pytest', 'report'],
        'content': '''---
name: playwright-test-runner
description: 独立执行 Playwright UI 自动化脚本并输出报告。用于代码生成完成后需要跑测、查看 HTML/Trace 时。
---

# Playwright 用例执行

## 目标

代码生成完成后，不交由录制 Skill 顺带执行，而是由本 Skill 专门负责跑测与报告，避免职责过载。

## 推荐命令

```bash
# Python / pytest
pip install -r requirements.txt
playwright install chromium
pytest tests/specs/ -v --tracing=on

# 单文件 / 单用例
pytest tests/specs/test_login.py -v
pytest tests/specs/test_login.py::TestLogin::test_tc_001_login_success -v
```

## 报告

- 优先输出可点击 Trace 的 HTML 报告
- 默认无头执行；遇到验证码等复杂场景切换有头模式人工介入
- 登录态可复用 storageState / Authorization localStorage

## 目录约定

```
tests/
  conftest.py
  specs/
  pages/
  data/
  helpers/
  fixtures/auth.json
  plans/
  recorded/
```
''',
        'files': {
            'references/runbook.md': (
                '# Runbook\n'
                '- 先确认依赖与浏览器已安装\n'
                '- 失败时打开 Trace 逐步回放\n'
                '- 需要修复时再调用 playwright-test-fixer\n'
            ),
        },
        'is_builtin': True,
        'is_enabled': True,
    },
    {
        'name': 'playwright-test-fixer',
        'description': '根据失败日志与 Trace 给出 UI 自动化修复建议，经人工确认后再改代码。',
        'tags': ['ui', 'playwright', 'debug', 'fix'],
        'content': '''---
name: playwright-test-fixer
description: 分析 Playwright/pytest 失败信息与 Trace，提出修复建议并在确认后修改脚本。按需使用。
---

# Playwright 问题修复

## 何时使用

- 执行报告出现失败 / flaky
- 定位器失效、等待不足、登录态过期
- 用户粘贴报错，或上下文已有失败日志

## 流程

1. 读取失败信息、Trace、相关录制脚本与 Page Object
2. 先给出修复建议（定位器优先级、等待、数据隔离、登录态）
3. 询问用户是否允许修改
4. 用户确认后再改代码，并建议重新执行 `playwright-test-runner`

## 修复原则

- 定位优先级：testId > role/name > label > css > xpath
- 避免无意义 sleep，优先 `expect` / `wait_for`
- 动态数据使用工厂随机值，避免脏数据互相污染
''',
        'files': {
            'references/common-fixes.md': (
                '# Common Fixes\n'
                '- strict mode violation：收窄 locator\n'
                '- timeout：补齐可见/可点击等待\n'
                '- auth expired：刷新 storageState\n'
            ),
        },
        'is_builtin': True,
        'is_enabled': True,
    },
]


def seed_playwright_skills(apps, schema_editor):
    Skill = apps.get_model('core', 'Skill')
    for item in PLAYWRIGHT_SKILLS:
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


def unseed_playwright_skills(apps, schema_editor):
    Skill = apps.get_model('core', 'Skill')
    Skill.objects.filter(
        name__in=[s['name'] for s in PLAYWRIGHT_SKILLS],
        is_builtin=True,
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0006_mcpserver'),
    ]

    operations = [
        migrations.RunPython(seed_playwright_skills, unseed_playwright_skills),
    ]
