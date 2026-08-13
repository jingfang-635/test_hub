# Generated manually: sync desktop 01-playwright-codegen into playwright-codegen Skill

from django.db import migrations


PLAYWRIGHT_CODEGEN_CONTENT = '---\nname: playwright-codegen\ndescription: >-\n  Pipeline 01 — 启动 Playwright codegen 供用户手动录制，生成用例计划 MD 供确认后再输出 UI 自动化脚本\n  （Page Object、数据工厂、多场景用例与 Trace/HTML 脚手架）。用户提供用例则按计划整理，\n  否则从录制代码推导。默认 Python/pytest，用户指定 TS 时用 TypeScript。\n  本 Skill 只做到生成脚本为止，不执行跑测、不打开报告。\n  Use when user mentions 01-playwright-codegen, playwright-codegen-to-tests,\n  playwright codegen, UI recording, 录制转脚本, 生成自动化用例.\n---\n\n# 01 Playwright Codegen（录制 → 脚本）\n\n## 独立性原则\n\n本 Skill **自包含**，禁止引用外部 MCP 或其他 Cursor Skill。仅使用：\n\n- Playwright CLI（`codegen`）\n- 项目内 `scripts/`（`start-codegen.sh` 等）、`templates/`、`tests/helpers/`\n- Python：pytest + pytest-playwright + **pytest-html**（脚手架依赖，本 Skill 只生成配置）\n- TypeScript：@playwright/test（脚手架依赖）\n\n**范围**：Phase 0–4 生成完毕即结束。**不**执行 pytest / playwright test，**不**打开 HTML/Trace 报告，**不**根据失败修代码。\n\n## 工作流总览\n\n```\nPhase 0 语言选择 → Phase 1 启动 codegen → 用户手动录制\n→ Phase 2 解析录制 → Phase 3 生成用例计划 MD → 【用户确认】\n→ Phase 4 生成脚本（含 Trace/HTML 脚手架）→ 【结束】\n```\n\n**关键门禁**：Phase 3 生成 MD 后必须暂停；用户确认前**禁止**生成 `tests/pages/`、`tests/data/`、`tests/specs/` 代码。\n\n---\n\n## Phase 0: 语言选择\n\n| 条件 | 语言 | 标记文件 |\n|------|------|----------|\n| 用户未指定 | **python**（默认） | `.codegen-lang` 写入 `python` |\n| 用户含 ts/typescript/@playwright/test | **typescript** | `.codegen-lang` 写入 `typescript` |\n\n后续所有输出（录制文件、POM、data factory、spec、计划 MD）必须与所选语言一致。\n\n---\n\n## Phase 1: 启动 Codegen\n\nAgent 后台启动 codegen，然后停止自动化，等待用户录制。\n\n### Mac / Linux\n\n```bash\nchmod +x scripts/start-codegen.sh\n./scripts/start-codegen.sh "<URL>" "<scenario>" [python|typescript] [--save-storage|--load-storage]\n```\n\n若 `scripts/start-codegen.sh` 不存在，先从 [templates/start-codegen.sh.tpl](templates/start-codegen.sh.tpl) 创建。\n\n### Windows\n\n```powershell\n.\\scripts\\start-codegen.ps1 -Url "<URL>" -Scenario "<scenario>" -Lang python\n```\n\n### 等价命令\n\n```bash\n# Python（默认）\nnpx playwright codegen "<URL>" -o tests/recorded/<scenario>.py --target python-pytest\n\n# TypeScript\nnpx playwright codegen "<URL>" -o tests/recorded/<scenario>.spec.ts --target javascript\n```\n\n### 登录态\n\n- 首次录制登录：`--save-storage=tests/fixtures/auth.json`\n- 后续跳过登录：`--load-storage=tests/fixtures/auth.json`\n\n### 告知用户\n\n1. 在打开的浏览器中完成完整业务流程\n2. 确认录制文件已保存到 `tests/recorded/`\n3. 回复「录制完成」；如有用例文档一并提供\n\n---\n\n## Phase 2: 解析录制代码\n\n读取 `tests/recorded/<scenario>.py` 或 `.spec.ts`，提取：\n\n- 导航 URL、页面跳转关系\n- 点击 / 输入 / 选择 / 上传等操作序列\n- 硬编码文本 → 参数化候选（账号、商品名等，以录制为准）\n- 缺失断言 → 待补充列表\n- 脆弱选择器 → 优化建议（见 [reference.md](reference.md)）\n- 涉及页面 → Page Object 拆分候选\n- **图形验证码**（满足任一即标记「含图形验证码」）：\n  - 录制中出现 captcha / 验证码类输入框或图片（label/alt/placeholder 以录制为准）\n  - 对同一验证码字段多次 fill（短串后重填）\n  - 调试可见 `/captcha` 类接口\n\n---\n\n## Phase 3: 生成用例计划 MD（确认门禁）\n\n**输出**：`tests/plans/<scenario>-test-plan.md`（基于 [templates/test-plan.md.tpl](templates/test-plan.md.tpl)）\n\n### 用例来源\n\n| 来源 | 处理 |\n|------|------|\n| 用户已提供用例 | 整理进 MD，补充前置条件、步骤、预期结果 |\n| 用户未提供用例 | 从录制代码自动推导（见下方规则） |\n| 两者都有 | 以用户用例为主，录制代码补充遗漏场景 |\n\n### 自动推导规则（无用户用例时）\n\n- **正向**：录制主流程 1 条（P0）\n- **负向**：空字段、错误凭证、非法格式（从表单字段推断）\n- **边界**：最大长度、特殊字符（从输入框推断）\n- **权限**：无权限访问（若含登录/鉴权步骤）\n\n### 含图形验证码时\n\n计划 MD「数据与造数规划」必须说明策略（可写两行）：\n\n| captcha | ddddocr（CAPTCHA_MODE=ocr） | 禁止写死录制中的验证码字符串 |\n| captcha | 人工有头（CAPTCHA_MODE=manual） | 会话填一次后写 auth.json |\n\nPython 默认 `CAPTCHA_MODE=ocr`；复杂/OCR 不稳定时用 `manual`（强制有头，见 [reference.md](reference.md)）。TypeScript 不生成 ddddocr，优先 storage_state 或 manual 等价流程。\n\n### Agent 必须\n\n1. 生成 MD 后展示路径，请用户审阅\n2. 等待「确认」/「通过」或修改意见\n3. 有修改 → 更新 MD，再次请确认\n4. **仅用户明确确认后**进入 Phase 4\n\n计划 MD 中「状态」在用户确认后改为：**已确认**。\n\n---\n\n## Phase 4: 生成工程化脚本（确认后）\n\n严格按已确认的计划 MD 生成，不擅自增删用例。「是否生成=否」的用例跳过。\n\n### Python 业务输出\n\n| 类型 | 路径 | 模板 |\n|------|------|------|\n| Page Object | `tests/pages/<page>_page.py` | [page-object.py.tpl](templates/page-object.py.tpl) |\n| 数据工厂 | `tests/data/<entity>_factory.py` | [data-factory.py.tpl](templates/data-factory.py.tpl) |\n| 用例 | `tests/specs/test_<feature>.py` | [test-case.py.tpl](templates/test-case.py.tpl) |\n\n**specs 拆分（强制）**：按功能模块一文件，与 page 模块对齐（如 `login` → `test_login.py`，`order` → `test_order.py`）。单个 specs 文件只放一个 `Test*` 类；录制跨多模块时生成多个 specs，**禁止**把多个功能的用例合并进一个文件。\n\n### Python 脚手架（缺失则创建，不得跳过）\n\n| 产物 | 模板 / 约定 |\n|------|-------------|\n| `pytest.ini` | [pytest.ini.tpl](templates/pytest.ini.tpl)：`--tracing=on` + `--html=reports/report.html --self-contained-html` |\n| `requirements.txt` | [requirements.txt.tpl](templates/requirements.txt.tpl)：含 `pytest-html` 等 |\n| `tests/helpers/trace_support.py` | [trace_support.py.tpl](templates/trace_support.py.tpl) |\n| `tests/conftest.py` | [conftest.py.tpl](templates/conftest.py.tpl)：HTML extras + 自定义 context tracing |\n| `scripts/open-report.sh` | [open-report.sh.tpl](templates/open-report.sh.tpl)，`chmod +x` |\n| `scripts/start-codegen.sh` | [start-codegen.sh.tpl](templates/start-codegen.sh.tpl)，`chmod +x` |\n| `.env.example` | [env.example.tpl](templates/env.example.tpl)：含 **`REPORT_ORIGIN=http://127.0.0.1:9323`** |\n| `.gitignore` | [gitignore.tpl](templates/gitignore.tpl)：忽略 `.env`、`test-results/`、`reports/`、`tests/fixtures/auth.json` 等 |\n| `assets/report.css` | [report.css.tpl](templates/report.css.tpl)：pytest-html 深色美化主题 |\n\n### Python 条件脚手架（含图形验证码时必须生成）\n\n| 产物 | 模板 / 约定 |\n|------|-------------|\n| `tests/helpers/captcha.py` | [captcha.py.tpl](templates/captcha.py.tpl)：通用 ocr/manual；**定位由调用方传入** |\n| 登录页 Page Object | [page-object.py.tpl](templates/page-object.py.tpl)：按录制生成 locator；方法中接入 captcha helper（见 reference） |\n| `requirements.txt` | **追加** `ddddocr==1.5.6`（仅 ocr 需要；manual-only 可不装） |\n| `.env.example` | `CAPTCHA_MODE=ocr\\|manual`、`CAPTCHA_MANUAL_WAIT=input\\|pause` |\n| `tests/conftest.py` | 按需启用 `_ensure_auth_state` + `authenticated_page`；**manual 时强制 headed** |\n\n规则：\n\n- 模板/脚手架**禁止**写死业务文案、菜单名、首页路径；一律从录制/计划推导\n- 登录 Page Object 应封装 `login_with_retry`（按 `CAPTCHA_MODE` 分支 ocr/manual）；禁止写死录制验证码字符串\n- 需登录的业务用例使用 `authenticated_page` / `storage_state`，避免每例重复 OCR/人工\n- `CAPTCHA_MODE=manual`：预填凭据 → 暂停等用户完成验证码与提交 → 写 `auth.json`\n- 登录成功：先断言离开登录 URL，再用录制推导的稳定 locator；禁止用营销文案子串冒充「已登录」\n- 区分：**会话造登录态用的 pause/input**（允许） vs **录制残留的无意义 `page.pause()`**（删除）\n\n自定义 `browser.new_context()`（如 `storage_state`）**必须**用 `trace_support` 启停 tracing，并在 teardown 后由 conftest 把 Trace 挂到 pytest-html。\n\n### TypeScript 输出\n\n| 类型 | 路径 | 模板 |\n|------|------|------|\n| Page Object | `tests/pages/<Page>.ts` | [page-object.ts.tpl](templates/page-object.ts.tpl) |\n| 数据工厂 | `tests/data/<entity>.factory.ts` | [data-factory.ts.tpl](templates/data-factory.ts.tpl) |\n| 用例 | `tests/specs/<feature>.spec.ts` | [test-case.ts.tpl](templates/test-case.ts.tpl) |\n\n同样强制：一个 `test.describe` / 一个功能模块对应一个 `.spec.ts`；跨模块录制拆成多个文件。\n\nTypeScript 脚手架：`playwright.config.ts` 必须包含：\n\n```ts\nreporter: [["html", { open: "never" }]],\nuse: { trace: "on" },\n```\n\n### 造数策略\n\n- 表单字段 → faker 随机\n- 唯一约束 → 时间戳后缀\n- 后端实体 → `tests/helpers/api_setup.py` 或 `api_setup.ts`\n- 敏感信息 → `.env`（参考 `.env.example`）\n\n### Phase 4 结束时告知用户\n\n脚本与脚手架已生成完毕。本 Skill **到此结束**。若需跑测、打开报告或根据报错改代码，请用户另行明确说明（例如「跑测」「看报告」「根据报错修复」）。\n\n---\n\n## 快速检查清单\n\n```\n- [ ] Phase 0: 语言已确定并写入 .codegen-lang\n- [ ] Phase 1: codegen 已启动，用户已录制完成\n- [ ] Phase 2: 录制代码已解析（含是否「含图形验证码」）\n- [ ] Phase 3: tests/plans/*-test-plan.md 已生成\n- [ ] Phase 3: 用户已确认计划\n- [ ] Phase 4: POM / data / specs 已按计划生成（一功能模块一 specs，无多 Test* 同居）\n- [ ] Phase 4: Trace/HTML 脚手架已齐（pytest.ini、trace_support、conftest、open-report、pytest-html）\n- [ ] Phase 4: 含验证码时 captcha helper（定位入参）+（ocr 时 ddddocr）+ 登录 POM 接入 login_with_retry + auth fixture\n- [ ] 已提示用户：生成结束；跑测/报告/修复需另行触发\n```\n\n## 附加资源\n\n- 选择器优化、造数、Trace 脚手架、图形验证码（ocr / manual）：[reference.md](reference.md)\n'


def update_skill(apps, schema_editor):
    Skill = apps.get_model('core', 'Skill')
    Skill.objects.update_or_create(
        name='playwright-codegen',
        defaults={
            'description': (
                'Pipeline：启动 Playwright codegen 录制，生成用例计划 MD（确认门禁）后输出 '
                'Page Object / 数据工厂 / 多场景用例与 Trace/HTML 脚手架。默认 Python/pytest。'
            ),
            'tags': ['ui', 'playwright', 'codegen', 'recording', 'test-plan'],
            'content': PLAYWRIGHT_CODEGEN_CONTENT,
            'files': {
                'references/codegen-checklist.md': (
                    '# Codegen Checklist\n'
                    '- Phase 0 语言已确定\n'
                    '- Phase 1 录制完成且文件非空\n'
                    '- Phase 2 已解析（含验证码标记）\n'
                    '- Phase 3 计划 MD 已确认\n'
                    '- Phase 4 POM/data/specs + 脚手架已生成\n'
                    '- 不在本 Skill 内跑测/打开报告\n'
                ),
            },
            'is_builtin': True,
            'is_enabled': True,
        },
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_seed_playwright_skills'),
    ]

    operations = [
        migrations.RunPython(update_skill, noop_reverse),
    ]
