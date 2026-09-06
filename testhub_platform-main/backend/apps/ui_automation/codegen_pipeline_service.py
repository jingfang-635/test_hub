"""
Playwright Codegen 后续流水线：解析 → 用例计划（确认门禁）→ 工程化脚本生成。
对齐 01-playwright-codegen Skill Phase 2–4。
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent / 'codegen_templates'

FRAGILE_SELECTOR_HINTS = (
    'nth=',
    ' >> nth=',
    'xpath=',
    'css=',
    'page.locator(',
    '.nth(',
)

CAPTCHA_KEYWORDS = (
    'captcha',
    '验证码',
    'verifycode',
    'verify_code',
    'vcode',
    'checkcode',
)


def _media_root() -> Path:
    return Path(settings.MEDIA_ROOT) / 'ui-automation'


def _sanitize_scenario(name: str) -> str:
    raw = (name or 'scenario').strip()
    raw = re.sub(r'\.(py|js|ts|spec\.ts)$', '', raw, flags=re.I)
    raw = re.sub(r'[^\w\u4e00-\u9fff\-]+', '_', raw).strip('_')
    return raw[:80] or 'scenario'


def _read_template(name: str) -> str:
    path = TEMPLATES_DIR / name
    if not path.exists():
        return ''
    return path.read_text(encoding='utf-8')


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def parse_recorded(content: str, language: str = 'python') -> dict[str, Any]:
    """Phase 2：确定性解析录制脚本（不调 AI）。"""
    text = content or ''
    lines = text.splitlines()
    steps: list[dict[str, Any]] = []
    urls: list[str] = []
    fills: list[dict[str, str]] = []
    selectors: list[str] = []
    assertions: list[str] = []
    pages: list[str] = []

    goto_re = re.compile(r'''\.goto\(\s*["']([^"']+)["']''')
    # 定位器参数可能含 nth-child(3) 等括号；动作前可能有 .first / .nth(1) / .filter(...) 链
    # codegen 常见：page.locator("span").filter(has_text="个人中心").click()
    _arg = r'''(?:[^()"']|"[^"]*"|'[^']*'|\([^()]*\))*'''
    _chain = rf'''(?:\.(?:first|last|nth\(\s*\d+\s*\)|filter\({_arg}\)))*'''
    _loc = (
        rf'''(?P<loc>(?:page\.)?(?:get_by_\w+|locator|getBy\w+)\({_arg}\)'''
        + _chain
        + r''')'''
    )
    fill_re = re.compile(_loc + r'''\.fill\(\s*["'](?P<val>[^"']*)["']''')
    click_re = re.compile(_loc + r'''\.click\(''')
    select_re = re.compile(_loc + r'''\.select_option\(''')
    expect_re = re.compile(r'''expect\((?P<body>[^)]+)\)''')
    locator_lit_re = re.compile(
        r'''(?:get_by_role|get_by_label|get_by_text|get_by_placeholder|get_by_test_id|'''
        r'''locator|getByRole|getByLabel|getByText|getByPlaceholder|getByTestId)'''
        + rf'''\({_arg}\)'''
        + _chain
    )

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue

        m_goto = goto_re.search(stripped)
        if m_goto:
            url = m_goto.group(1)
            urls.append(url)
            steps.append({'line': idx, 'action': 'navigate', 'url': url, 'raw': stripped})
            pages.append(_page_name_from_url(url))
            continue

        m_fill = fill_re.search(stripped)
        if m_fill:
            loc, val = m_fill.group('loc'), m_fill.group('val')
            selectors.append(loc)
            fills.append({'locator': loc, 'value': val, 'line': str(idx)})
            steps.append({'line': idx, 'action': 'fill', 'locator': loc, 'value': val, 'raw': stripped})
            continue

        m_click = click_re.search(stripped)
        if m_click:
            loc = m_click.group('loc')
            selectors.append(loc)
            steps.append({'line': idx, 'action': 'click', 'locator': loc, 'raw': stripped})
            continue

        m_select = select_re.search(stripped)
        if m_select:
            loc = m_select.group('loc')
            selectors.append(loc)
            steps.append({'line': idx, 'action': 'select', 'locator': loc, 'raw': stripped})
            continue

        m_expect = expect_re.search(stripped)
        if m_expect:
            assertions.append(stripped)
            steps.append({'line': idx, 'action': 'assert', 'raw': stripped})
            continue

        for lit in locator_lit_re.findall(stripped):
            selectors.append(lit)

    # 参数化候选：非空 fill 值
    param_candidates = []
    for item in fills:
        val = item['value']
        if val and len(val) >= 2:
            param_candidates.append({
                'field_hint': item['locator'][:80],
                'recorded_value': val,
                'suggest': 'faker' if not _looks_sensitive(val) else '.env',
            })

    fragile = []
    for sel in selectors:
        lower = sel.lower()
        if any(h in lower for h in FRAGILE_SELECTOR_HINTS) or 'xpath' in lower:
            fragile.append({
                'original': sel,
                'suggestion': '优先 getByRole / getByLabel / getByTestId，避免 nth/xpath',
            })

    has_captcha = _detect_captcha(text, fills)
    unique_pages = []
    for p in pages:
        if p and p not in unique_pages:
            unique_pages.append(p)
    if not unique_pages:
        unique_pages = ['main']

    missing_assertions = len(assertions) == 0

    return {
        'language': language,
        'step_count': len(steps),
        'steps': steps,
        'urls': urls,
        'target_url': urls[0] if urls else '',
        'pages': [{'name': p, 'class_name': _to_page_class(p)} for p in unique_pages],
        'param_candidates': param_candidates,
        'fragile_selectors': fragile,
        'assertions': assertions,
        'missing_assertions': missing_assertions,
        'has_captcha': has_captcha,
        'selectors': list(dict.fromkeys(selectors)),
    }


def _page_name_from_url(url: str) -> str:
    try:
        from urllib.parse import urlparse
        path = urlparse(url).path.strip('/') or 'home'
        part = path.split('/')[0] or 'home'
        part = re.sub(r'[^\w\u4e00-\u9fff]+', '_', part)
        return part or 'home'
    except Exception:  # noqa: BLE001
        return 'home'


def _to_page_class(name: str) -> str:
    parts = re.split(r'[_\-\s]+', name)
    cleaned = ''.join(p.capitalize() for p in parts if p)
    if not cleaned:
        cleaned = 'Main'
    if not cleaned.endswith('Page'):
        cleaned += 'Page'
    return cleaned


def _looks_sensitive(val: str) -> bool:
    if re.fullmatch(r'\d{11}', val):
        return True
    if len(val) >= 6 and re.search(r'[A-Za-z]', val) and re.search(r'\d', val):
        return True
    return False


def _detect_captcha(text: str, fills: list[dict[str, str]]) -> bool:
    lower = text.lower()
    if any(k in lower or k in text for k in CAPTCHA_KEYWORDS):
        return True
    if '/captcha' in lower:
        return True
    # 同一验证码字段多次短串 fill
    captcha_fills = [
        f for f in fills
        if any(k in f['locator'].lower() or k in f['locator'] for k in CAPTCHA_KEYWORDS)
    ]
    if len(captcha_fills) >= 2:
        return True
    short_retries = [f for f in fills if 0 < len(f.get('value', '')) <= 6]
    if len(short_retries) >= 3 and any('code' in f['locator'].lower() for f in short_retries):
        return True
    return False


def _extract_ai_text(resp: dict[str, Any]) -> str:
    """兼容 content / reasoning_content / 多段 contents。"""
    try:
        message = (resp.get('choices') or [{}])[0].get('message') or {}
    except Exception:  # noqa: BLE001
        message = {}

    candidates: list[str] = []
    for key in ('content', 'reasoning_content', 'text'):
        val = message.get(key)
        if isinstance(val, str) and val.strip():
            candidates.append(val.strip())

    # 部分模型用 list content blocks
    content = message.get('content')
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(str(block.get('text') or block.get('content') or ''))
        joined = '\n'.join(p for p in parts if p).strip()
        if joined:
            candidates.append(joined)

    if candidates:
        # 优先取含 JSON / 代码特征的最长文本
        candidates.sort(key=lambda s: (('{' in s or 'class ' in s or 'def ' in s), len(s)), reverse=True)
        return candidates[0]
    return ''


def _run_ai(
    messages: list[dict[str, str]],
    max_tokens: int | None = None,
    *,
    timeout: float = 600,
) -> str:
    from apps.requirement_analysis.models import AIModelConfig, AIModelService

    config = AIModelConfig.objects.filter(role='writer', is_active=True).first()
    if not config:
        raise RuntimeError('未配置可用的 AI 模型（role=writer 且 is_active=True），请先在配置中心启用')

    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        resp = loop.run_until_complete(
            asyncio.wait_for(
                AIModelService.call_openai_compatible_api(config, messages, max_tokens=max_tokens),
                timeout=timeout,
            )
        )
    finally:
        loop.close()

    text = _extract_ai_text(resp if isinstance(resp, dict) else {})
    if not text:
        # 记录 finish_reason 便于排查
        try:
            finish = (resp.get('choices') or [{}])[0].get('finish_reason')
            logger.warning('AI empty content, finish_reason=%s keys=%s', finish, list(((resp.get('choices') or [{}])[0].get('message') or {}).keys()))
        except Exception:  # noqa: BLE001
            pass
        raise RuntimeError('AI 返回内容为空，请重试或检查模型配置（部分推理模型可能把答案放在 reasoning_content）')
    return text


def _load_skill_content(compact: bool = False) -> str:
    try:
        from apps.core.models import Skill
        skill = Skill.objects.filter(name='playwright-codegen', is_enabled=True).first()
        if skill and skill.content:
            if compact:
                # Phase 4 不注入全文，避免占满 token 导致 content 为空
                return (
                    '你是 Playwright UI 自动化架构师。按已确认计划生成 Page Object / data factory / specs。'
                    '默认 Python pytest-playwright；一功能模块一 specs；禁止写死验证码；删除无意义 page.pause()。'
                )
            return skill.content
    except Exception as exc:  # noqa: BLE001
        logger.warning('load skill failed: %s', exc)
    return (
        '你是 Playwright UI 自动化架构师。按 Phase 2–4：解析录制、生成用例计划 MD、'
        '确认后生成 Page Object / data factory / specs。Python 默认 pytest-playwright。'
    )


def _strip_code_fence(text: str) -> str:
    text = (text or '').strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:markdown|md|json|python|javascript|ts)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    return text.strip()


def create_from_parse(
    *,
    project,
    user,
    content: str,
    language: str = 'python',
    scenario: str = '',
    target_url: str = '',
    recorded_name: str = '',
    source_script=None,
):
    from .models import CodegenConversion

    lang = 'javascript' if language in ('javascript', 'js', 'typescript') else 'python'
    if language == 'typescript':
        lang = 'javascript'
    scenario_name = _sanitize_scenario(scenario or recorded_name or 'recorded')
    parse_result = parse_recorded(content, lang)
    if not target_url:
        target_url = parse_result.get('target_url') or ''

    conversion = CodegenConversion.objects.create(
        project=project,
        user=user,
        scenario=scenario_name,
        language=lang,
        target_url=target_url,
        recorded_name=recorded_name or f'{scenario_name}.{"js" if lang == "javascript" else "py"}',
        recorded_content=content,
        parse_result=parse_result,
        status='parsed',
        source_script=source_script,
    )
    return conversion


def generate_plan(conversion, user_cases_md: str | None = None, *, use_ai: bool = False) -> Any:
    """Phase 3：生成用例计划 MD。

    默认按解析结果确定性填充模板（秒级）；仅 use_ai=True 时调用 AI。
    """
    if user_cases_md is not None:
        conversion.user_cases_md = user_cases_md

    now = timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')
    md = ''
    ai_error = ''

    if use_ai:
        template = _read_template('test-plan.md.tpl')
        skill = _load_skill_content(compact=True)
        parse = conversion.parse_result or {}
        # 压缩上下文，避免超长 prompt 拖慢首包与生成
        parse_compact = {
            'step_count': parse.get('step_count'),
            'pages': parse.get('pages') or [],
            'param_candidates': (parse.get('param_candidates') or [])[:8],
            'fragile_selectors': (parse.get('fragile_selectors') or [])[:8],
            'missing_assertions': parse.get('missing_assertions'),
            'has_captcha': parse.get('has_captcha'),
            'urls': (parse.get('urls') or [])[:5],
            'steps': (parse.get('steps') or [])[:40],
        }
        parse_json = json.dumps(parse_compact, ensure_ascii=False)
        recorded_excerpt = (conversion.recorded_content or '')[:2500]
        user_cases_excerpt = (conversion.user_cases_md or '（无）')[:2000]

        system = (
            f'{skill}\n'
            '执行 Phase 3：只输出完整用例计划 Markdown，不要 pages/data/specs 代码，不要解释。\n'
            '遵循模板结构：\n'
            f'{template}\n'
            '规则：状态保持「待确认」；无用户用例时推导正向(P0)+负向+边界+权限(若登录)；'
            '有用户用例时以用户为主；含验证码时数据规划含 captcha；一功能模块一 specs。'
        )
        user_msg = (
            f'场景：{conversion.scenario}\n'
            f'语言：{conversion.language}\n'
            f'录制文件：{conversion.recorded_name}\n'
            f'目标 URL：{conversion.target_url}\n'
            f'生成时间：{now}\n'
            f'解析结果 JSON：\n{parse_json}\n\n'
            f'录制脚本（节选）：\n```\n{recorded_excerpt}\n```\n\n'
            f'用户提供用例（可空）：\n{user_cases_excerpt}\n'
        )
        try:
            md = _strip_code_fence(_run_ai(
                [
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user_msg},
                ],
                max_tokens=4000,
                timeout=60,
            ))
            if not md or len(md) < 50:
                raise RuntimeError('AI 返回的计划内容过短')
        except Exception as exc:  # noqa: BLE001
            ai_error = str(exc)
            logger.warning('AI generate_plan failed, fallback to template: %s', exc)
            md = ''

    if not md:
        md = _build_plan_from_parse(conversion, generated_at=now)

    try:
        conversion.plan_md = md
        conversion.plan_status = 'draft'
        conversion.status = 'plan_ready'
        conversion.error = (f'AI 增强失败已回退模板计划: {ai_error}' if ai_error else '')
        conversion.save(update_fields=[
            'plan_md', 'plan_status', 'status', 'error', 'user_cases_md', 'updated_at'
        ])
        _persist_plan_file(conversion)
        return conversion
    except Exception as exc:  # noqa: BLE001
        conversion.status = 'failed'
        conversion.error = str(exc)
        conversion.save(update_fields=['status', 'error', 'updated_at'])
        raise


def _build_plan_from_parse(conversion, *, generated_at: str = '') -> str:
    """按解析结果确定性生成用例计划 Markdown（秒级）。"""
    parse = conversion.parse_result or {}
    pages = parse.get('pages') or [{'name': 'main', 'class_name': 'MainPage'}]
    params = parse.get('param_candidates') or []
    fragile = parse.get('fragile_selectors') or []
    steps = parse.get('steps') or []
    has_captcha = bool(parse.get('has_captcha'))
    missing_assertions = bool(parse.get('missing_assertions'))
    scenario = conversion.scenario or 'scenario'
    lang = conversion.language or 'python'
    is_py = lang == 'python'
    ext = 'py' if is_py else 'js'
    feature = scenario
    test_class = f"Test{_to_page_class(scenario).replace('Page', '')}"
    snake_scenario = _snake(scenario)
    generated_at = generated_at or timezone.localtime().strftime('%Y-%m-%d %H:%M:%S')

    # Page Object 表
    page_rows = []
    for page in pages:
        name = page.get('name') or 'main'
        class_name = page.get('class_name') or _to_page_class(name)
        snake = _snake(name)
        methods = ['goto']
        for idx, step in enumerate(steps):
            action = step.get('action')
            loc = step.get('locator') or ''
            if action == 'fill' and loc:
                methods.append(f"fill_{_method_name_from_locator(loc, idx)}")
            elif action == 'click' and loc:
                methods.append(f"click_{_method_name_from_locator(loc, idx)}")
        methods = list(dict.fromkeys(methods))[:8]
        page_file = f"{snake}_page.{ext}" if is_py else f"{class_name}.{ext}"
        page_rows.append(
            f"| {name} | {class_name} | {', '.join(methods)} | tests/pages/{page_file} |"
        )
    if not page_rows:
        page_rows = ['| main | MainPage | goto | tests/pages/main_page.py |']

    # 数据造数
    data_rows = []
    for i, p in enumerate(params[:8]):
        src = p.get('suggest') or 'faker'
        val = (p.get('recorded_value') or '')[:40]
        hint = (p.get('field_hint') or f'field_{i + 1}')[:60]
        data_rows.append(f'| field_{i + 1} | {src} | 录制值参考 `{val}`；定位：`{hint}` |')
    if has_captcha:
        data_rows.append('| captcha | ddddocr | CAPTCHA_MODE=ocr，禁止写死录制验证码 |')
        data_rows.append('| captcha | manual | CAPTCHA_MODE=manual，有头人工填一次后写 auth.json |')
    if not data_rows:
        data_rows = ['| username | faker | 默认造数 |', '| password | .env | 敏感值走环境变量 |']

    # 用例推导
    step_summary = ' → '.join(
        f"{s.get('action')}" for s in steps[:12] if s.get('action')
    ) or '打开页面并完成录制主流程'
    login_like = any(
        k in (conversion.scenario or '').lower()
        or k in (conversion.target_url or '').lower()
        or any(k in (s.get('raw') or '').lower() for s in steps)
        for k in ('login', '登录', 'signin', 'auth')
    )
    cases = [
        {
            'id': 'TC-001',
            'type': '正向',
            'name': f'{scenario} 主流程成功',
            'pre': '环境可用；测试账号有效' + ('；验证码可识别' if has_captcha else ''),
            'steps': step_summary,
            'expected': '流程完成且关键断言成立' if not missing_assertions else '流程完成（建议补充断言）',
            'priority': 'P0',
            'gen': '是',
        }
    ]
    # 负向：基于 fill 字段
    fill_steps = [s for s in steps if s.get('action') == 'fill']
    if fill_steps:
        cases.append({
            'id': 'TC-002',
            'type': '负向',
            'name': f'{scenario} 必填为空/错误值',
            'pre': '进入目标页面',
            'steps': '关键字段留空或填入非法值后提交',
            'expected': '提示校验错误，不进入成功态',
            'priority': 'P1',
            'gen': '是',
        })
        cases.append({
            'id': 'TC-003',
            'type': '边界',
            'name': f'{scenario} 边界输入',
            'pre': '进入目标页面',
            'steps': '超长字符串 / 特殊字符输入后提交',
            'expected': '系统稳定，给出明确校验或截断策略',
            'priority': 'P2',
            'gen': '是',
        })
    if login_like:
        cases.append({
            'id': f'TC-{len(cases) + 1:03d}',
            'type': '权限',
            'name': '未登录访问受保护页',
            'pre': '清除登录态',
            'steps': '直接访问目标 URL',
            'expected': '跳转登录页或返回未授权提示',
            'priority': 'P1',
            'gen': '是',
        })

    # 用户用例优先补充
    user_cases = (conversion.user_cases_md or '').strip()
    if user_cases:
        cases.insert(1, {
            'id': 'TC-U01',
            'type': '正向',
            'name': '用户提供用例（详见用户用例区，请审阅拆分）',
            'pre': '见用户用例',
            'steps': user_cases.replace('\n', ' / ')[:120],
            'expected': '满足用户用例预期',
            'priority': 'P0',
            'gen': '是',
        })

    case_rows = [
        f"| {c['id']} | {c['type']} | {c['name']} | {c['pre']} | {c['steps']} | {c['expected']} | {c['priority']} | {c['gen']} |"
        for c in cases
    ]
    tc_range = f"{cases[0]['id']} ~ {cases[-1]['id']}" if cases else 'TC-001'

    fragile_rows = []
    for item in fragile[:10]:
        original = (item.get('original') or '').replace('|', '\\|')
        suggestion = (item.get('suggestion') or '优先 getByRole / getByLabel / getByTestId').replace('|', '\\|')
        fragile_rows.append(f'| `{original}` | {suggestion} |')
    if not fragile_rows:
        fragile_rows = ['| （无） | 录制选择器整体可接受，建议回归时复核稳定性 |']

    checklist = [
        '- [ ] 用例覆盖是否完整',
        '- [ ] 造数方式是否可行',
        '- [ ] 是否需要 API 前置造数',
        '- [ ] Page Object 拆分是否合理',
        '- [ ] 用例是否按模块拆分到独立 specs 文件',
    ]
    if missing_assertions:
        checklist.append('- [ ] 录制缺少断言，确认补充 expect')
    if has_captcha:
        checklist.append('- [ ] 验证码策略（ddddocr / manual）已确认')

    return '\n'.join([
        f'# {scenario} UI 自动化用例计划',
        '',
        '> 状态：**待确认** — 用户确认前禁止生成 pages/data/specs 代码',
        '',
        '## 基本信息',
        '',
        f'- 场景：{scenario}',
        f'- 语言：{lang}',
        f'- 录制文件：tests/recorded/{conversion.recorded_name or f"{scenario}.{ext}"}',
        f'- 目标 URL：{conversion.target_url or (parse.get("target_url") or "")}',
        f'- 生成时间：{generated_at}',
        f'- 生成方式：模板（基于解析结果）',
        '',
        '## 页面与 Page Object 规划',
        '',
        '| 页面 | 类名 | 主要方法 | 输出文件 |',
        '|------|------|----------|----------|',
        *page_rows,
        '',
        '## 用例文件规划',
        '',
        '| 功能模块 | Test 类 | 用例 ID 范围 | 输出文件 |',
        '|----------|---------|--------------|----------|',
        f'| {feature} | {test_class} | {tc_range} | tests/specs/test_{snake_scenario}.{ext} |',
        '',
        '规则：一功能模块一 specs 文件；与 page 模块对齐；禁止多个 Test* 写入同一文件。',
        '',
        '## 数据与造数规划',
        '',
        '| 字段 | 来源 | 说明 |',
        '|------|------|------|',
        *data_rows,
        '',
        '来源可选：`faker` / `.env` / `api_setup` / `fixtures` / `ddddocr` / `manual`（有头人工）',
        '',
        '## 用例清单',
        '',
        '| ID | 类型 | 用例名称 | 前置条件 | 步骤 | 预期结果 | 优先级 | 是否生成 |',
        '|----|------|----------|----------|------|----------|--------|----------|',
        *case_rows,
        '',
        '类型：`正向` / `负向` / `边界` / `权限`',
        '',
        '## 选择器优化建议',
        '',
        '| 原选择器（录制） | 建议优化 |',
        '|------------------|----------|',
        *fragile_rows,
        '',
        '## 待确认项',
        '',
        *checklist,
        '',
        '## 确认记录',
        '',
        '- 确认人：',
        '- 确认时间：',
        '- 备注：',
        '',
    ])


def update_plan_md(conversion, plan_md: str) -> Any:
    conversion.plan_md = plan_md or ''
    if conversion.plan_status == 'confirmed':
        conversion.plan_status = 'draft'
        conversion.status = 'plan_ready'
    conversion.save(update_fields=['plan_md', 'plan_status', 'status', 'updated_at'])
    _persist_plan_file(conversion)
    return conversion


def confirm_plan(conversion, plan_md: str | None = None) -> Any:
    if plan_md is not None and plan_md.strip():
        conversion.plan_md = plan_md
    if not conversion.plan_md.strip():
        raise ValueError('计划内容为空，无法确认')

    md = conversion.plan_md
    md = re.sub(r'(状态：\*\*)待确认(\*\*)', r'\1已确认\2', md)
    md = re.sub(r'(状态：)待确认', r'\1已确认', md)
    if '已确认' not in md[:200]:
        md = md.replace('> 状态：**待确认**', '> 状态：**已确认**', 1)
    conversion.plan_md = md
    conversion.plan_status = 'confirmed'
    conversion.status = 'confirmed'
    conversion.error = ''
    conversion.save(update_fields=['plan_md', 'plan_status', 'status', 'error', 'updated_at'])
    _persist_plan_file(conversion)
    return conversion


def _persist_plan_file(conversion) -> Path:
    plans_dir = _media_root() / 'plans'
    path = plans_dir / f'{conversion.scenario}-test-plan.md'
    _write_text(path, conversion.plan_md)
    return path


def generate_scripts(conversion, *, use_ai: bool = False) -> Any:
    """Phase 4：确认后生成工程化脚本 + 脚手架 + 落库。

    默认走确定性模板生成（秒级响应）；仅当 use_ai=True 时才调用 AI 增强。
    """
    if conversion.plan_status != 'confirmed':
        raise ValueError('计划尚未确认，禁止生成 pages/data/specs')

    has_captcha = bool((conversion.parse_result or {}).get('has_captcha'))
    artifacts = None
    ai_error = ''

    if use_ai:
        skill = _load_skill_content(compact=True)
        is_py = conversion.language == 'python'
        parse = conversion.parse_result or {}
        system = (
            f'{skill}\n'
            '只输出合法 JSON 对象，不要 Markdown 解释，不要代码围栏。格式：\n'
            '{"pages":[{"path":"tests/pages/login_page.py","class_name":"LoginPage","name":"Login","code":"..."}],'
            '"data":[{"path":"tests/data/user_factory.py","code":"..."}],'
            '"specs":[{"path":"tests/specs/test_login.py","name":"test_login","code":"..."}]}\n'
            f'语言：{"Python pytest-playwright" if is_py else "JavaScript Playwright"}。'
            '一功能模块一个 specs；跳过计划中「是否生成=否」；禁止写死验证码字符串。'
        )
        # 压缩上下文 + 短超时：失败立即回退模板，避免长时间卡住
        plan_excerpt = (conversion.plan_md or '')[:3000]
        recorded_excerpt = (conversion.recorded_content or '')[:2500]
        user_msg = (
            f'场景：{conversion.scenario}\n目标 URL：{conversion.target_url}\n'
            f'页面候选：{json.dumps(parse.get("pages") or [], ensure_ascii=False)}\n'
            f'是否含验证码：{has_captcha}\n\n'
            f'已确认计划（节选）：\n{plan_excerpt}\n\n'
            f'录制脚本（节选）：\n{recorded_excerpt}\n'
        )
        try:
            raw = _strip_code_fence(_run_ai(
                [
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': user_msg},
                ],
                max_tokens=4000,
                timeout=60,
            ))
            artifacts = _parse_artifacts_json(raw)
        except Exception as exc:  # noqa: BLE001
            ai_error = str(exc)
            logger.warning('AI generate_scripts failed, fallback to template: %s', exc)
            artifacts = None

    if artifacts is None:
        artifacts = _build_fallback_artifacts(conversion)

    try:
        result = _materialize_artifacts(conversion, artifacts, has_captcha=has_captcha)
        conversion.generated_files = result['files']
        conversion.generated_script_ids = result['script_ids']
        conversion.generated_page_object_ids = result['page_object_ids']
        conversion.status = 'generated'
        if ai_error:
            conversion.error = f'AI 增强失败已回退模板生成: {ai_error}'
        else:
            conversion.error = ''
        conversion.save(update_fields=[
            'generated_files', 'generated_script_ids', 'generated_page_object_ids',
            'status', 'error', 'updated_at',
        ])
        return conversion
    except Exception as exc:  # noqa: BLE001
        conversion.status = 'failed'
        conversion.error = str(exc)
        conversion.save(update_fields=['status', 'error', 'updated_at'])
        raise


_CASE_TYPE_KEYWORDS = {
    '正向', '负向', '边界', '权限', '冒烟', '回归',
    'positive', 'negative', 'boundary', 'auth', 'smoke', 'regression',
}


def _extract_plan_cases(plan_md: str) -> list[dict[str, str]]:
    """从计划 MD「用例清单」表格中提取用例行（TC-xxx），供模板生成 specs。

    只解析「用例清单」小节，避免误扫「用例文件规划」里的 ``TC-001 ~ TC-003`` 范围行；
    按用例 ID 去重，防止同名 ``test_tc_001`` 互相覆盖。
    """
    cases: list[dict[str, str]] = []
    if not plan_md:
        return cases

    section = plan_md
    section_match = re.search(r'^##\s*用例清单\s*$', plan_md, flags=re.M)
    if section_match:
        rest = plan_md[section_match.end():]
        next_heading = re.search(r'^##\s+', rest, flags=re.M)
        section = rest[: next_heading.start()] if next_heading else rest

    seen_ids: set[str] = set()
    for line in section.splitlines():
        stripped = line.strip()
        if not stripped.startswith('|'):
            continue
        lower = stripped.lower()
        if '是否生成' in stripped and ('用例' in stripped or 'id' in lower):
            continue
        if 'tc-' not in lower and 'tc_' not in lower:
            continue
        # 跳过「TC-001 ~ TC-003」一类范围单元格（用例文件规划表）
        if re.search(r'TC[-_]?\d+\s*[~～\-–—至到]+\s*TC[-_]?\d+', stripped, flags=re.I):
            continue
        cells = [c.strip() for c in stripped.strip('|').split('|')]
        if len(cells) < 2:
            continue
        if all(set(c) <= {'-', ':', ' '} for c in cells):
            continue
        tc_id = ''
        for cell in cells:
            m = re.search(r'(TC[-_]?\d+)', cell, flags=re.I)
            if m and not tc_id:
                tc_id = m.group(1).upper().replace('_', '-')
                break
        if not tc_id or tc_id in seen_ids:
            continue

        case_type = ''
        title = cells[1] if len(cells) > 1 else tc_id
        if re.search(r'TC[-_]?\d+', title, flags=re.I) and len(cells) > 2:
            title = cells[2]
        if title in _CASE_TYPE_KEYWORDS and len(cells) > 2:
            case_type = title
            title = cells[2]
        elif len(cells) > 2 and cells[1] in _CASE_TYPE_KEYWORDS:
            case_type = cells[1]
            title = cells[2]

        generate_flag = '是'
        for cell in cells:
            if cell in ('否', 'no', 'No', 'N', 'n'):
                generate_flag = '否'
                break
        if generate_flag == '否':
            continue

        seen_ids.add(tc_id)
        cases.append({
            'id': tc_id,
            'title': (title[:80] or tc_id),
            'type': case_type,
        })
    return cases


def _build_fallback_artifacts(conversion) -> dict[str, Any]:
    """按解析结果 + 录制脚本 + 计划用例生成可用的 POM / data / specs（确定性，秒级）。"""
    parse = conversion.parse_result or {}
    pages_meta = parse.get('pages') or [{'name': 'main', 'class_name': 'MainPage'}]
    scenario = conversion.scenario
    is_py = conversion.language == 'python'
    target = conversion.target_url or (parse.get('target_url') or '')
    steps = parse.get('steps') or []
    params = parse.get('param_candidates') or []
    plan_cases = _extract_plan_cases(conversion.plan_md or '')

    page0 = pages_meta[0]
    page_name = page0.get('name') or 'main'
    class_name = page0.get('class_name') or _to_page_class(page_name)
    snake = _snake(page_name)

    if is_py:
        methods = []
        for idx, step in enumerate(steps):
            action = step.get('action')
            if action == 'navigate':
                continue
            loc = step.get('locator') or ''
            if not loc:
                continue
            attr = _method_name_from_locator(loc, idx)
            expr = loc if loc.startswith('page.') or loc.startswith('self.page') else loc
            expr = expr.replace('page.', 'self.page.', 1) if expr.startswith('page.') else expr
            if action == 'fill':
                methods.append(
                    f'    def fill_{attr}(self, value: str) -> None:\n'
                    f'        {expr}.fill(value)\n'
                )
            elif action == 'click':
                methods.append(
                    f'    def click_{attr}(self) -> None:\n'
                    f'        {expr}.click()\n'
                )

        page_code = (
            f'"""{page_name} 页面对象（由录制确定性生成）。"""\n\n'
            'from playwright.sync_api import Page, Locator\n\n\n'
            f'class {class_name}:\n'
            '    def __init__(self, page: Page):\n'
            '        self.page = page\n\n'
            '    def goto(self, url: str | None = None) -> None:\n'
            f'        self.page.goto(url or "{target}")\n\n'
            + ('\n'.join(methods) if methods else '    def run_recorded_flow(self) -> None:\n        """请完善录制步骤封装。"""\n        pass\n')
        )

        factory_fields = []
        for i, p in enumerate(params[:6]):
            key = f'field_{i + 1}'
            if p.get('suggest') == '.env':
                factory_fields.append(f'        "{key}": os.getenv("TEST_FIELD_{i + 1}", "{p.get("recorded_value", "")}"),')
            else:
                factory_fields.append(f'        "{key}": fake.user_name(),')
        data_code = (
            '"""数据工厂（确定性生成）。"""\n'
            'import os\n'
            'from faker import Faker\n\n'
            'fake = Faker("zh_CN")\n\n'
            f'def create_{snake}(**overrides):\n'
            '    data = {\n'
            + ('\n'.join(factory_fields) if factory_fields else '        "username": fake.user_name(),\n        "password": fake.password(length=10),\n')
            + '\n    }\n'
            '    data.update(overrides)\n'
            '    return data\n'
        )

        body_lines = []
        for step in steps:
            raw = step.get('raw') or ''
            if not raw:
                continue
            if step.get('action') == 'fill' and step.get('value'):
                body_lines.append(f'        # TODO: 参数化原值 {step.get("value")!r}')
                body_lines.append(f'        {raw.strip()}')
            else:
                body_lines.append(f'        {raw.strip()}')
        if not body_lines:
            body_lines = [
                '        page.goto(base_url)',
                f'        pom = {class_name}(page)',
                '        pom.goto()',
            ]

        case_methods = []
        used_method_names: set[str] = set()
        if plan_cases:
            for i, case in enumerate(plan_cases):
                tc_slug = _snake(case['id'])
                method_name = f'test_{tc_slug}'
                base_name = method_name
                suffix = 2
                while method_name in used_method_names:
                    method_name = f'{base_name}_{suffix}'
                    suffix += 1
                used_method_names.add(method_name)

                case_type = (case.get('type') or '').lower()
                title_text = case.get('title') or ''
                if case_type in {'正向', 'positive', 'smoke', '冒烟'} or i == 0:
                    mark = 'positive'
                elif any(k in case_type or k in title_text for k in ('负向', '边界', '权限', '失败', 'negative', 'boundary')):
                    mark = 'negative'
                else:
                    mark = 'positive' if i == 0 else 'negative'

                # 仅首条注入录制主流程；其余未实现用例必须 skip，禁止 assert data 假成功
                if i == 0:
                    body = '\n'.join(body_lines)
                else:
                    body = (
                        f'        pytest.skip("计划用例 {case["id"]} {title_text} 尚未根据录制步骤实现")'
                    )
                case_methods.append(
                    f'    @pytest.mark.{mark}\n'
                    f'    def {method_name}(self, page: Page, base_url: str) -> None:\n'
                    f'        """{case["id"]} {case["title"]}"""\n'
                    f'        data = create_{snake}()\n'
                    f'        pom = {class_name}(page)\n'
                    f'{body}\n'
                )
        else:
            case_methods.append(
                '    @pytest.mark.positive\n'
                f'    def test_tc_001_{_snake(scenario)}_main(self, page: Page, base_url: str) -> None:\n'
                f'        """TC-001 {scenario} 主流程"""\n'
                f'        data = create_{snake}()\n'
                f'        pom = {class_name}(page)\n'
                + '\n'.join(body_lines) + '\n'
            )

        spec_code = (
            f'"""{scenario} UI 自动化用例（确定性生成）。"""\n\n'
            'import pytest\n'
            'from playwright.sync_api import Page, expect\n\n'
            f'from tests.pages.{snake}_page import {class_name}\n'
            f'from tests.data.{snake}_factory import create_{snake}\n\n\n'
            f'class Test{_to_page_class(scenario).replace("Page", "")}:\n'
            + '\n'.join(case_methods)
        )

        return {
            'pages': [{
                'path': f'tests/pages/{snake}_page.py',
                'class_name': class_name,
                'name': page_name,
                'code': page_code,
            }],
            'data': [{
                'path': f'tests/data/{snake}_factory.py',
                'code': data_code,
            }],
            'specs': [{
                'path': f'tests/specs/test_{_snake(scenario)}.py',
                'name': f'test_{_snake(scenario)}',
                'code': spec_code,
            }],
        }

    # javascript fallback
    page_code = (
        f'export class {class_name} {{\n'
        '  /** @param {import("@playwright/test").Page} page */\n'
        '  constructor(page) { this.page = page; }\n'
        f'  async goto(url = "{target}") {{ await this.page.goto(url); }}\n'
        '}\n'
    )
    spec_code = (
        "const { test, expect } = require('@playwright/test');\n"
        f"const {{ {class_name} }} = require('../pages/{class_name}');\n\n"
        f"test.describe('{scenario}', () => {{\n"
        f"  test('TC-001 main flow', async ({{ page }}) => {{\n"
        f"    const pom = new {class_name}(page);\n"
        f"    await pom.goto('{target}');\n"
        '    // TODO: 将录制步骤迁移为 POM 调用\n'
        '  });\n'
        '});\n'
    )
    return {
        'pages': [{'path': f'tests/pages/{class_name}.js', 'class_name': class_name, 'name': page_name, 'code': page_code}],
        'data': [{'path': 'tests/data/factory.js', 'code': 'module.exports = { createData: () => ({}) };\n'}],
        'specs': [{'path': f'tests/specs/{_snake(scenario)}.spec.js', 'name': _snake(scenario), 'code': spec_code}],
    }


def _parse_artifacts_json(raw: str) -> dict[str, Any]:
    text = _strip_code_fence(raw)
    if not text or not text.strip():
        raise RuntimeError('AI 返回为空，无法解析 JSON')
    # 尝试截取最外层 JSON
    start = text.find('{')
    end = text.rfind('}')
    if start >= 0 and end > start:
        text = text[start:end + 1]
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        text2 = text.replace('"', '"').replace('"', '"')
        try:
            data = json.loads(text2)
        except json.JSONDecodeError:
            raise RuntimeError(f'AI 返回的不是合法 JSON: {exc}') from exc
    if not isinstance(data, dict):
        raise RuntimeError('AI 未返回 JSON 对象')
    for key in ('pages', 'data', 'specs'):
        if key not in data or not isinstance(data[key], list):
            data[key] = data.get(key) or []
    if not data['pages'] and not data['specs']:
        raise RuntimeError('AI 未生成 pages/specs')
    return data


def _materialize_artifacts(conversion, artifacts: dict[str, Any], *, has_captcha: bool) -> dict[str, Any]:
    from .models import PageObject, TestScript

    root = _media_root() / 'generated' / conversion.scenario
    files: list[str] = []
    script_ids: list[int] = []
    page_object_ids: list[int] = []

    # 脚手架
    scaffold_map = _scaffold_files(conversion.language, has_captcha=has_captcha)
    for rel, content in scaffold_map.items():
        path = root / rel
        _write_text(path, content)
        files.append(str(path.relative_to(_media_root())).replace('\\', '/'))

    with transaction.atomic():
        for page in artifacts.get('pages') or []:
            code = page.get('code') or ''
            rel = page.get('path') or f"tests/pages/{_snake(page.get('name') or 'page')}_page.py"
            if conversion.language == 'javascript' and not rel.endswith(('.js', '.ts')):
                rel = rel.rsplit('.', 1)[0] + '.js'
            path = root / rel
            _write_text(path, code)
            files.append(str(path.relative_to(_media_root())).replace('\\', '/'))

            class_name = page.get('class_name') or _to_page_class(page.get('name') or 'Main')
            name = page.get('name') or class_name
            po, _ = PageObject.objects.update_or_create(
                project=conversion.project,
                name=name[:200],
                defaults={
                    'class_name': class_name[:200],
                    'url_pattern': conversion.target_url or '',
                    'description': f'由 codegen 流水线生成：{conversion.scenario}',
                    'template_code': code,
                    'created_by': conversion.user,
                },
            )
            page_object_ids.append(po.id)
            _sync_elements_from_parse(conversion, po)

        for data_item in artifacts.get('data') or []:
            code = data_item.get('code') or ''
            rel = data_item.get('path') or 'tests/data/factory.py'
            path = root / rel
            _write_text(path, code)
            files.append(str(path.relative_to(_media_root())).replace('\\', '/'))

        for spec in artifacts.get('specs') or []:
            code = spec.get('code') or ''
            rel = spec.get('path') or f"tests/specs/test_{_snake(conversion.scenario)}.py"
            if conversion.language == 'javascript' and not rel.endswith(('.js', '.ts', '.spec.js', '.spec.ts')):
                rel = rel.rsplit('.', 1)[0] + '.spec.js'
            path = root / rel
            _write_text(path, code)
            files.append(str(path.relative_to(_media_root())).replace('\\', '/'))

            script_name = (spec.get('name') or Path(rel).name)[:200]
            if not script_name.endswith(('.py', '.js', '.ts')):
                script_name = f"{script_name}.{'js' if conversion.language == 'javascript' else 'py'}"
            ts = TestScript.objects.create(
                project=conversion.project,
                name=f'{conversion.scenario}_{script_name}'[:200],
                description=f'Codegen Phase4 生成 · {conversion.scenario}',
                script_type='CODE',
                content=code,
                language=conversion.language,
                framework='playwright',
            )
            script_ids.append(ts.id)

    return {
        'files': files,
        'script_ids': script_ids,
        'page_object_ids': page_object_ids,
        'root': str(root),
    }


def _sync_elements_from_parse(conversion, page_object) -> None:
    """尽力从解析结果创建 Element / PageObjectElement。"""
    from .models import Element, LocatorStrategy, PageObjectElement

    try:
        selectors = (conversion.parse_result or {}).get('selectors') or []
        strategy = LocatorStrategy.objects.filter(name__icontains='css').first()
        if not strategy:
            strategy = LocatorStrategy.objects.first()
        if not strategy:
            return

        for idx, sel in enumerate(selectors[:30]):
            method = _method_name_from_locator(sel, idx)
            locator_value = sel[:500]
            element, _ = Element.objects.get_or_create(
                project=conversion.project,
                name=f'{page_object.name}_{method}'[:200],
                defaults={
                    'description': 'codegen 自动提取',
                    'element_type': 'BUTTON',
                    'locator_strategy': strategy,
                    'locator_value': locator_value,
                    'created_by': conversion.user,
                },
            )
            PageObjectElement.objects.get_or_create(
                page_object=page_object,
                method_name=method[:100],
                defaults={'element': element, 'is_property': True, 'order': idx},
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning('sync elements from parse failed: %s', exc)


def _method_name_from_locator(sel: str, idx: int) -> str:
    m = re.search(r'''name\s*=\s*["']([^"']+)["']''', sel)
    if m:
        base = re.sub(r'[^\w]+', '_', m.group(1)).strip('_').lower() or f'el_{idx}'
        return base[:80]
    m = re.search(r'''["']([^"']{2,40})["']''', sel)
    if m:
        base = re.sub(r'[^\w]+', '_', m.group(1)).strip('_').lower() or f'el_{idx}'
        return base[:80]
    return f'el_{idx}'


_ROLE_TYPE_ZH = {
    'button': '按钮',
    'textbox': '输入框',
    'text box': '输入框',
    'searchbox': '搜索框',
    'link': '链接',
    'checkbox': '复选框',
    'radio': '单选框',
    'combobox': '下拉框',
    'listbox': '下拉框',
    'option': '选项',
    'menuitem': '菜单项',
    'menuitemcheckbox': '菜单项',
    'menuitemradio': '菜单项',
    'tab': '标签',
    'switch': '开关',
    'img': '图片',
    'image': '图片',
    'heading': '标题',
    'spinbutton': '输入框',
}

_ELEMENT_TYPE_ZH = {
    'INPUT': '输入框',
    'BUTTON': '按钮',
    'LINK': '链接',
    'DROPDOWN': '下拉框',
    'CHECKBOX': '复选框',
    'RADIO': '单选框',
    'TEXT': '文本',
    'IMAGE': '图片',
    'CONTAINER': '容器',
    'TABLE': '表格',
    'FORM': '表单',
    'MODAL': '弹窗',
}

_ROLE_TO_ELEMENT_TYPE = {
    'button': 'BUTTON',
    'link': 'LINK',
    'textbox': 'INPUT',
    'searchbox': 'INPUT',
    'spinbutton': 'INPUT',
    'checkbox': 'CHECKBOX',
    'radio': 'RADIO',
    'combobox': 'DROPDOWN',
    'listbox': 'DROPDOWN',
    'img': 'IMAGE',
    'image': 'IMAGE',
}


def _clean_display_label(label: str) -> str:
    """去掉 recorded_ / record_ 前缀，整理可读标签。"""
    text = (label or '').strip()
    if not text:
        return ''
    text = re.sub(r'^(?:recorded?_)+', '', text, flags=re.I)
    text = re.sub(r'[_]+', ' ', text).strip()
    text = re.sub(r'\s+', ' ', text)
    return text[:80]


def _filter_has_text(raw: str) -> str:
    """从 .filter(has_text=...) / .filter({ hasText: ... }) 提取文案。"""
    m = re.search(
        r'''\.filter\(\s*(?:has_text|hasText)\s*=\s*["']([^"']+)["']'''
        r'''|\.filter\(\s*\{\s*hasText\s*:\s*["']([^"']+)["']''',
        raw or '',
        re.I,
    )
    if not m:
        return ''
    return (m.group(1) or m.group(2) or '').strip()


def _extract_locator_label_and_kind(locator: str, action: str = '') -> tuple[str, str, str]:
    """
    从 Playwright 定位表达式提取 (显示标签, 控件类型中文, Element.element_type)。
    例如 get_by_role("button", name="登录") → ("登录", "按钮", "BUTTON")
    """
    raw = _strip_page_prefix(locator or '')
    action_l = (action or '').lower()
    default_type = _element_type_for_action(action_l)
    default_kind = _ELEMENT_TYPE_ZH.get(default_type, '元素')

    if not raw:
        return '', default_kind, default_type

    # locator("span").filter(has_text="个人中心") → 用文案作标签
    filter_text = _filter_has_text(raw)
    if filter_text:
        return _clean_display_label(filter_text) or default_kind, default_kind, default_type

    role_m = re.search(
        r'''(?:get_by_role|getByRole)\(\s*["']([^"']+)["'](?:[^)]*name\s*[:=]\s*["']([^"']*)["'])?''',
        raw,
        re.I,
    )
    if role_m:
        role = (role_m.group(1) or '').strip().lower()
        name = _clean_display_label(role_m.group(2) or '')
        kind = _ROLE_TYPE_ZH.get(role, default_kind)
        el_type = _ROLE_TO_ELEMENT_TYPE.get(role, default_type)
        if not name:
            name = kind
        return name, kind, el_type

    for method, kind, el_type in (
        ('get_by_placeholder|getByPlaceholder', '输入框', 'INPUT'),
        ('get_by_label|getByLabel', '输入框', 'INPUT'),
        ('get_by_text|getByText', '文本', 'TEXT'),
        ('get_by_title|getByTitle', '元素', default_type),
        ('get_by_alt_text|getByAltText', '图片', 'IMAGE'),
        ('get_by_test_id|getByTestId', default_kind, default_type),
    ):
        m = re.search(rf'''(?:{method})\(\s*["']([^"']+)["']''', raw, re.I)
        if m:
            label = _clean_display_label(m.group(1))
            return label or kind, kind, el_type

    loc_m = re.search(r'''(?:locator)\(\s*["']([^"']+)["']''', raw, re.I)
    if loc_m:
        val = loc_m.group(1).strip()
        # #username / [name="user"] / input[placeholder="..."]
        id_m = re.match(r'#([\w\-]+)', val)
        if id_m:
            return _clean_display_label(id_m.group(1)) or default_kind, default_kind, default_type
        name_m = re.search(r'''\[(?:name|aria-label|placeholder|title)\s*=\s*["']([^"']+)["']''', val, re.I)
        if name_m:
            label = _clean_display_label(name_m.group(1))
            kind = default_kind
            if 'placeholder' in val.lower() or re.search(r'\binput\b', val, re.I):
                kind, default_type = '输入框', 'INPUT'
            elif re.search(r'\bbutton\b', val, re.I):
                kind, default_type = '按钮', 'BUTTON'
            elif re.search(r'\ba\b', val, re.I):
                kind, default_type = '链接', 'LINK'
            return label or kind, kind, default_type
        # 取末段有意义文本
        text_m = re.search(r'''["']([^"']{1,40})["']\s*$''', val)
        if text_m:
            return _clean_display_label(text_m.group(1)) or default_kind, default_kind, default_type
        cleaned = _clean_display_label(re.sub(r'[^\w\u4e00-\u9fff\-]+', ' ', val))
        if cleaned:
            return cleaned[:40], default_kind, default_type

    # 回退：任意引号内文案
    m = re.search(r'''["']([^"']{1,40})["']''', raw)
    if m:
        return _clean_display_label(m.group(1)) or default_kind, default_kind, default_type

    method = _clean_display_label(_method_name_from_locator(raw, 0))
    return method or default_kind, default_kind, default_type


def _build_step_description(
    *,
    action: str,
    locator: str = '',
    url: str = '',
    value: str = '',
    raw: str = '',
    element_name: str = '',
    element_type: str = '',
) -> str:
    """生成可读的步骤描述，如「点击「登录」按钮」，不含 recorded_ 前缀。"""
    action_l = (action or '').lower()
    label, kind, inferred_type = _extract_locator_label_and_kind(locator, action_l)
    el_type = element_type or inferred_type
    if not kind and el_type:
        kind = _ELEMENT_TYPE_ZH.get(el_type, '元素')
    if not label:
        label = _clean_display_label(element_name) or kind or '元素'

    if action_l == 'navigate':
        return f'跳转到 {url}' if url else '跳转到页面'

    if action_l == 'click':
        if kind in ('文本', '元素') or label == kind:
            return f'点击「{label}」'
        return f'点击「{label}」{kind}'

    if action_l == 'fill':
        ctrl = kind if kind not in ('文本', '元素') else '输入框'
        if value:
            shown = value if len(value) <= 40 else value[:37] + '...'
            return f'在「{label}」{ctrl}中输入「{shown}」'
        return f'在「{label}」{ctrl}中输入'

    if action_l == 'select':
        ctrl = kind if kind not in ('文本', '元素') else '下拉框'
        if value:
            return f'在「{label}」{ctrl}中选择「{value}」'
        return f'在「{label}」{ctrl}中选择'

    if action_l == 'assert':
        assert_type, assert_value = _infer_assert_fields(raw)
        target = f'「{label}」' if label else '元素'
        if assert_type == 'urlContains':
            return f'断言 URL 包含「{assert_value}」' if assert_value else '断言 URL'
        if assert_type == 'textContains':
            return f'断言{target}文本包含「{assert_value}」' if assert_value else f'断言{target}文本'
        if assert_type == 'textEquals':
            return f'断言{target}文本等于「{assert_value}」' if assert_value else f'断言{target}文本'
        if assert_type == 'hasAttribute':
            return f'断言{target}具有属性「{assert_value}」' if assert_value else f'断言{target}属性'
        return f'断言{target}可见'

    return f'操作「{label}」{kind}'


def _strip_page_prefix(locator: str) -> str:
    s = (locator or '').strip()
    if s.startswith('page.'):
        return s[5:]
    return s


def _extract_locator_nth_suffix(raw: str) -> str:
    """从 .nth(1) / .first / .last 链提取 Playwright >> nth= 后缀。"""
    parts: list[str] = []
    for m in re.finditer(r'''\.(?:first|last|nth\(\s*(\d+)\s*\))''', raw or '', re.I):
        token = m.group(0).lower()
        if token == '.first':
            parts.append('nth=0')
        elif token == '.last':
            parts.append('nth=-1')
        else:
            parts.append(f'nth={m.group(1)}')
    if not parts:
        return ''
    return ' >> ' + ' >> '.join(parts)


def _parse_playwright_locator(locator: str) -> tuple[str, str]:
    """将 codegen 定位表达式转为 (strategy_name, locator_value)。"""
    raw = _strip_page_prefix(locator or '')
    if not raw:
        return 'css', ''

    nth_suffix = _extract_locator_nth_suffix(raw)

    # locator(...).filter(has_text="...") / get_by_role(...).filter(has_text=...)
    filter_text = _filter_has_text(raw)
    if filter_text:
        role_m = re.search(r'''(?:get_by_role|getByRole)\(\s*["']([^"']+)["']''', raw, re.I)
        if role_m:
            role = role_m.group(1)
            if '"' in filter_text and "'" not in filter_text:
                base = f"{role}[name='{filter_text}']"
            else:
                safe = filter_text.replace('\\', '\\\\').replace('"', '\\"')
                base = f'{role}[name="{safe}"]'
            return 'role', f'{base}{nth_suffix}'
        return 'text', f'{filter_text}{nth_suffix}'

    # python: get_by_role("button", name="登录") / js: getByRole('button', { name: '登录' })
    # 保留 role+name，写入 Playwright role 选择器：button[name="登录"]
    # （勿降级为 text，否则 aria-label/无障碍名称匹配会丢失）
    role_m = re.search(
        r'''(?:get_by_role|getByRole)\(\s*["']([^"']+)["'](?:[^)]*name\s*[:=]\s*["']([^"']*)["'])?''',
        raw,
        re.I,
    )
    if role_m:
        role, name = role_m.group(1), role_m.group(2)
        if name:
            if '"' in name and "'" not in name:
                base = f"{role}[name='{name}']"
            else:
                safe_name = name.replace('\\', '\\\\').replace('"', '\\"')
                base = f'{role}[name="{safe_name}"]'
        else:
            base = role
        return 'role', f'{base}{nth_suffix}'

    for method, strategy in (
        ('get_by_label|getByLabel', 'label'),
        ('get_by_placeholder|getByPlaceholder', 'placeholder'),
        ('get_by_text|getByText', 'text'),
        ('get_by_title|getByTitle', 'title'),
        ('get_by_test_id|getByTestId', 'test-id'),
    ):
        m = re.search(rf'''(?:{method})\(\s*["']([^"']+)["']''', raw, re.I)
        if m:
            return strategy, f'{m.group(1)}{nth_suffix}'

    loc_m = re.search(r'''(?:locator)\(\s*["']([^"']+)["']''', raw, re.I)
    if loc_m:
        val = loc_m.group(1)
        if val.startswith('xpath=') or val.startswith('//') or val.startswith('(//'):
            return 'xpath', f"{val[6:] if val.startswith('xpath=') else val}{nth_suffix}"
        if val.startswith('#'):
            return 'id', f'{val[1:]}{nth_suffix}'
        return 'css', f'{val}{nth_suffix}'

    # 回退：整段表达式写入 css，便于人工修正
    return 'css', raw[:500]


def _resolve_locator_strategy(strategy_name: str):
    from .models import LocatorStrategy

    name = (strategy_name or 'css').strip()
    aliases = {
        'css': ['css', 'CSS', 'css selector', 'CSS Selector'],
        'xpath': ['xpath', 'XPath', 'XPATH'],
        'id': ['id', 'ID', 'Id'],
        'text': ['text', 'Text', 'TEXT'],
        'name': ['name', 'Name', 'NAME'],
        'class': ['class', 'Class', 'class name', 'CLASS'],
        'tag': ['tag', 'Tag', 'tag name'],
        'placeholder': ['placeholder', 'Placeholder'],
        'role': ['role', 'Role', 'ROLE'],
        'label': ['label', 'Label', 'LABEL'],
        'title': ['title', 'Title', 'TITLE'],
        'test-id': ['test-id', 'testid', 'test_id', 'data-testid', 'Test ID'],
    }
    candidates = aliases.get(name.lower(), [name])
    for cand in candidates:
        obj = LocatorStrategy.objects.filter(name__iexact=cand).first()
        if obj:
            return obj
    obj = LocatorStrategy.objects.filter(name__icontains=name).first()
    if obj:
        return obj
    return LocatorStrategy.objects.filter(name__icontains='css').first() or LocatorStrategy.objects.first()


def _element_type_for_action(action: str) -> str:
    if action == 'fill':
        return 'INPUT'
    if action == 'select':
        return 'DROPDOWN'
    if action == 'assert':
        return 'TEXT'
    return 'BUTTON'


def _resolve_page_group(project, page_name: str):
    """按页面名查找或创建该项目的「页面」分组（ElementGroup），返回 ElementGroup 或 None。

    元素管理页的「页面」节点即 ElementGroup，元素通过 group_id 关联到页面。
    解析时自动给元素绑定对应页面分组，使其在元素管理页显示在对应页面下，而非「未关联页面」。
    """
    from .models import ElementGroup

    name = (page_name or '').strip()
    if not name:
        return None
    # 优先复用该项目下同名顶层分组，避免重复建组
    group = ElementGroup.objects.filter(
        project=project,
        name=name,
        parent_group__isnull=True,
    ).first()
    if group:
        return group
    return ElementGroup.objects.create(
        project=project,
        name=name,
        order=0,
    )


def _get_or_create_element_from_locator(
    *,
    project,
    user,
    locator: str,
    action: str,
    page_name: str,
    cache: dict[str, Any],
    idx: int,
    capture: dict[str, Any] | None = None,
) -> tuple[Any, bool] | tuple[None, bool]:
    """按定位表达式匹配或创建 Element，返回 (element, created)。"""
    from .models import Element

    key = (locator or '').strip()
    if not key:
        return None, False
    if key in cache:
        element = cache[key]
        if capture:
            _apply_capture_to_element(element, capture, primary_strategy=_parse_playwright_locator(key)[0], primary_value=_parse_playwright_locator(key)[1])
        return element, False

    strategy_name, locator_value = _parse_playwright_locator(key)
    if not locator_value:
        return None, False

    strategy = _resolve_locator_strategy(strategy_name)
    if not strategy:
        return None, False

    existing = Element.objects.filter(
        project=project,
        locator_value=locator_value[:500],
    ).first()
    if existing:
        # 兼容修复：历史解析创建但未绑定页面分组的元素，补绑其对应页面分组
        if not existing.group_id:
            target_page = existing.page or page_name
            group = _resolve_page_group(project, target_page)
            if group:
                existing.group = group
                if not existing.page:
                    existing.page = group.name
                existing.save(update_fields=['group', 'page'])
        if capture:
            _apply_capture_to_element(existing, capture, primary_strategy=strategy_name, primary_value=locator_value)
        cache[key] = existing
        return existing, False

    label, kind, el_type = _extract_locator_label_and_kind(key, action)
    # 可读名称：如「登录按钮」「用户名输入框」，避免 recorded_ 前缀
    if label and kind and label != kind:
        base_name = f'{label}{kind}'[:200]
    elif label:
        base_name = label[:200]
    else:
        base_name = kind or _clean_display_label(_method_name_from_locator(key, idx)) or f'元素{idx + 1}'
    name = base_name
    n = 1
    while Element.objects.filter(project=project, name=name).exists():
        name = f'{base_name}_{n}'[:200]
        n += 1

    # 解析页面分组，使元素归属于对应页面，而非「未关联页面」
    page_group = _resolve_page_group(project, page_name)

    element = Element.objects.create(
        project=project,
        name=name,
        description=f'录制步骤自动创建: {key[:200]}',
        element_type=el_type or _element_type_for_action(action),
        locator_strategy=strategy,
        locator_value=locator_value[:500],
        page=(page_name or '')[:200],
        group=page_group,
        created_by=user,
        validation_status='UNKNOWN',
    )
    if capture:
        _apply_capture_to_element(element, capture, primary_strategy=strategy_name, primary_value=locator_value)
    cache[key] = element
    return element, True


def _load_recording_captures(recorded_name: str = '', captures_path: str = '') -> list[dict[str, Any]]:
    """读取录制 sidecar：media/.../recorded/{name}.captures.json。"""
    import json

    root = Path(settings.MEDIA_ROOT) / 'ui-automation' / 'recorded'
    candidates: list[Path] = []
    if captures_path:
        candidates.append(Path(captures_path))
    if recorded_name:
        name = str(recorded_name).strip()
        candidates.append(root / f'{name}.captures.json')
        candidates.append(root / name)
        if not name.endswith('.captures.json'):
            candidates.append(root / f'{name}.captures.json')
        # case_8_record → case_8_record.py.captures.json
        if not name.endswith('.py'):
            candidates.append(root / f'{name}.py.captures.json')
        stem = name
        for suffix in ('.captures.json', '.py', '.js', '.spec.ts'):
            if stem.endswith(suffix):
                stem = stem[: -len(suffix)]
        if stem:
            candidates.append(root / f'{stem}.py.captures.json')
            candidates.append(root / f'{stem}.captures.json')

    for path in candidates:
        try:
            if not path.is_file():
                continue
            if not (path.suffix == '.json' or str(path).endswith('.captures.json')):
                continue
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, list) and data:
                logger.info('loaded captures from %s count=%s', path, len(data))
                return data
        except Exception as exc:  # noqa: BLE001
            logger.warning('load captures failed %s: %s', path, exc)

    # 兜底：取 recorded 目录下最新的 *.captures.json
    try:
        newest = sorted(root.glob('*.captures.json'), key=lambda p: p.stat().st_mtime, reverse=True)
        for path in newest[:3]:
            data = json.loads(path.read_text(encoding='utf-8'))
            if isinstance(data, list) and data:
                logger.info('loaded captures fallback %s count=%s', path, len(data))
                return data
    except Exception as exc:  # noqa: BLE001
        logger.warning('captures fallback failed: %s', exc)
    return []


def _is_junk_capture_locator(strategy: str, value: str) -> bool:
    v = (value or '').lower()
    return 'x-pw-glass' in v or 'playwright-inspector' in v or 'pw-glass' in v


def _is_junk_capture(capture: dict[str, Any]) -> bool:
    tag = (capture.get('tag') or '').lower()
    if tag.startswith('x-pw-') or tag == 'x-pw-glass':
        return True
    locs = capture.get('locators') or []
    if not locs:
        return True
    return all(_is_junk_capture_locator(l.get('strategy') or '', l.get('value') or '') for l in locs)


def _capture_match_score(capture: dict[str, Any], primary_strategy: str, primary_value: str) -> int:
    """录制采集与 codegen 主定位器的相似度（越高越匹配）。"""
    if _is_junk_capture(capture):
        return 0
    primary_s = (primary_strategy or '').strip().lower()
    primary_v = (primary_value or '').strip()
    if not primary_v:
        return 0
    score = 0
    for loc in capture.get('locators') or []:
        strategy = (loc.get('strategy') or '').strip().lower()
        value = (loc.get('value') or '').strip()
        if not value or _is_junk_capture_locator(strategy, value):
            continue
        if value == primary_v:
            score = max(score, 100 if strategy == primary_s else 80)
        elif primary_v in value or value in primary_v:
            score = max(score, 40)
        elif primary_s and strategy == primary_s and (
            primary_v[:20] in value or value[:20] in primary_v
        ):
            score = max(score, 30)
    return score


def _take_best_capture(
    captures: list[dict[str, Any]],
    used: set[int],
    *,
    primary_strategy: str,
    primary_value: str,
    sequential_idx: int,
) -> dict[str, Any] | None:
    """优先按内容匹配未使用的 capture，其次按顺序消费。不分配 junk/零分 capture。"""
    best_i = -1
    best_score = 0
    for i, cap in enumerate(captures):
        if i in used or _is_junk_capture(cap):
            continue
        score = _capture_match_score(cap, primary_strategy, primary_value)
        if score > best_score:
            best_score = score
            best_i = i
    if best_i >= 0 and best_score >= 30:
        used.add(best_i)
        return captures[best_i]
    # 回退顺序：仅当尚未用过 sequential_idx 且非 junk
    if 0 <= sequential_idx < len(captures) and sequential_idx not in used:
        cap = captures[sequential_idx]
        if not _is_junk_capture(cap):
            used.add(sequential_idx)
            return cap
    return None


def _canonicalize_backup_strategy(strategy_name: str) -> str:
    """对齐 LocatorStrategy.name；失败则保留原名。策略可重复出现在备用列表中。"""
    from .models import LocatorStrategy

    name = (strategy_name or '').strip()
    if not name:
        return ''
    aliases = {
        'css': ['css', 'CSS', 'css selector', 'CSS Selector'],
        'xpath': ['xpath', 'XPath', 'XPATH'],
        'id': ['id', 'ID', 'Id'],
        'text': ['text', 'Text', 'TEXT'],
        'name': ['name', 'Name', 'NAME'],
        'class': ['class', 'Class', 'class name', 'CLASS'],
        'tag': ['tag', 'Tag', 'tag name'],
        'placeholder': ['placeholder', 'Placeholder'],
        'role': ['role', 'Role', 'ROLE'],
        'label': ['label', 'Label', 'LABEL'],
        'title': ['title', 'Title', 'TITLE'],
        'test-id': ['test-id', 'testid', 'test_id', 'data-testid', 'Test ID'],
    }
    try:
        for cand in aliases.get(name.lower(), [name]):
            obj = LocatorStrategy.objects.filter(name__iexact=cand).first()
            if obj:
                return obj.name
        obj = LocatorStrategy.objects.filter(name__iexact=name).first()
        if obj:
            return obj.name
    except Exception:  # noqa: BLE001
        pass
    return name


def _apply_capture_to_element(
    element,
    capture: dict[str, Any],
    *,
    primary_strategy: str,
    primary_value: str,
) -> None:
    """把录制采集的备用定位器与控件截图写入 Element。

    规则：定位策略可重复；同一策略下同一表达式不可重复（大小写不敏感的策略名 + 精确表达式）。
    """
    from django.core.files.base import ContentFile
    import base64

    update_fields: list[str] = []
    locators = capture.get('locators') or []
    backups: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    primary_s = (primary_strategy or '').strip().lower()
    primary_v = (primary_value or '').strip()
    for loc in locators:
        raw_strategy = (loc.get('strategy') or '').strip()
        value = (loc.get('value') or '').strip()
        if not raw_strategy or not value:
            continue
        if _is_junk_capture_locator(raw_strategy, value):
            continue
        if raw_strategy.lower() == primary_s and value == primary_v:
            continue
        strategy = _canonicalize_backup_strategy(raw_strategy)
        key = (strategy.lower(), value)
        if key in seen:
            continue
        seen.add(key)
        backups.append({'strategy': strategy, 'value': value[:500]})

    if backups:
        # 录制采集为准：覆盖旧备用，避免历史空/脏数据挡掉新结果
        element.backup_locators = backups
        update_fields.append('backup_locators')

    shot_b64 = capture.get('screenshot_b64') or ''
    if shot_b64:
        try:
            raw = base64.b64decode(shot_b64)
            element.screenshot.save(
                f'element_{element.pk or "new"}_{int(timezone.now().timestamp())}.png',
                ContentFile(raw),
                save=False,
            )
            update_fields.append('screenshot')
        except Exception as exc:  # noqa: BLE001
            logger.warning('save element screenshot failed: %s', exc)

    if update_fields:
        element.save(update_fields=update_fields)


def _element_screenshot_url(element) -> str:
    """控件截图可访问地址：优先 data URI（不依赖 /media 代理），否则相对 /media/ 路径。"""
    import base64
    import os
    from urllib.parse import urlparse

    if not element:
        return ''
    try:
        if not element.screenshot:
            return ''
    except Exception:  # noqa: BLE001
        return ''

    try:
        path = element.screenshot.path
        if path and os.path.isfile(path):
            size = os.path.getsize(path)
            # 控件截图通常很小；给步骤/列表内联，避免跨域/代理丢图
            if 0 < size <= 300_000:
                with open(path, 'rb') as fh:
                    raw = fh.read()
                return f'data:image/png;base64,{base64.b64encode(raw).decode("ascii")}'
    except Exception:  # noqa: BLE001
        pass

    try:
        url = element.screenshot.url or ''
        if url.startswith('http://') or url.startswith('https://'):
            return urlparse(url).path or url
        if url and not url.startswith('/'):
            return f'/media/{url.lstrip("/")}'
        return url
    except Exception:  # noqa: BLE001
        return ''


def _element_step_extras(element) -> dict[str, Any]:
    """步骤 DTO 上附带的元素展示字段。"""
    if not element:
        return {
            'element_name': '',
            'element_locator': '',
            'element_locator_strategy': '',
            'element_backup_locators': [],
            'element_screenshot': '',
        }
    return {
        'element_name': element.name or '',
        'element_locator': element.locator_value or '',
        'element_locator_strategy': (
            element.locator_strategy.name if element.locator_strategy_id else ''
        ),
        'element_backup_locators': list(element.backup_locators or []),
        'element_screenshot': _element_screenshot_url(element),
    }



def _infer_assert_fields(raw: str) -> tuple[str, str]:
    text = raw or ''
    if re.search(r'to_be_visible|toBeVisible|to_be_attached|toBeAttached', text, re.I):
        return 'isVisible', ''
    if re.search(r'to_have_url|toHaveURL', text, re.I):
        m = re.search(r'''["']([^"']+)["']''', text)
        return 'urlContains', m.group(1) if m else ''
    if re.search(r'to_have_text|toHaveText|to_contain_text|toContainText', text, re.I):
        m = re.search(r'''["']([^"']+)["']''', text)
        return 'textContains', m.group(1) if m else ''
    if re.search(r'to_have_attribute|toHaveAttribute', text, re.I):
        m = re.findall(r'''["']([^"']+)["']''', text)
        return 'hasAttribute', m[-1] if m else ''
    return 'isVisible', ''


def map_parse_to_case_steps(
    *,
    project,
    user,
    content: str,
    language: str = 'python',
    create_elements: bool = True,
    recorded_name: str = '',
    captures_path: str = '',
) -> dict[str, Any]:
    """
    将录制脚本解析为用例管理可用的步骤列表。
    返回 { parse_result, steps, created_element_ids }。
    """
    parse = parse_recorded(content, language=language or 'python')
    pages = parse.get('pages') or []
    default_page = pages[0]['name'] if pages else 'main'
    urls = parse.get('urls') or []
    captures = _load_recording_captures(recorded_name=recorded_name, captures_path=captures_path)
    capture_used: set[int] = set()
    capture_seq = 0

    element_cache: dict[str, Any] = {}
    created_ids: list[int] = []
    mapped: list[dict[str, Any]] = []
    current_page = default_page

    for idx, step in enumerate(parse.get('steps') or []):
        action = (step.get('action') or '').lower()
        raw = step.get('raw') or ''
        locator = step.get('locator') or ''

        if action == 'navigate':
            url = step.get('url') or ''
            if url:
                current_page = _page_name_from_url(url) or current_page
            mapped.append({
                'action_type': 'navigateUrl',
                'page_filter': current_page,
                'element_id': None,
                'input_value': url,
                'wait_time': 1000,
                'assert_type': '',
                'assert_value': '',
                'description': _build_step_description(action='navigate', url=url, raw=raw)[:500],
                'raw': raw,
                **_element_step_extras(None),
            })
            continue

        element = None
        capture = None
        if create_elements and locator:
            strategy_name, locator_value = _parse_playwright_locator(locator)
            capture = _take_best_capture(
                captures,
                capture_used,
                primary_strategy=strategy_name,
                primary_value=locator_value,
                sequential_idx=capture_seq,
            )
            capture_seq += 1
            element, created = _get_or_create_element_from_locator(
                project=project,
                user=user,
                locator=locator,
                action=action,
                page_name=current_page,
                cache=element_cache,
                idx=idx,
                capture=capture,
            )
            if created and element:
                created_ids.append(element.id)

        extras = _element_step_extras(element)

        if action == 'assert':
            assert_type, assert_value = _infer_assert_fields(raw)
            mapped.append({
                'action_type': 'assert',
                'page_filter': current_page,
                'element_id': element.id if element else None,
                'input_value': '',
                'wait_time': 1000,
                'assert_type': assert_type,
                'assert_value': assert_value,
                'description': _build_step_description(
                    action='assert',
                    locator=locator,
                    raw=raw,
                    element_name=element.name if element else '',
                    element_type=element.element_type if element else '',
                )[:500],
                'raw': raw,
                **extras,
            })
            continue

        # click / fill / select（用例无 select，映射为 fill）
        action_type = 'fill' if action in ('fill', 'select') else 'click'
        input_value = step.get('value') or ''
        desc = _build_step_description(
            action=action,
            locator=locator,
            value=input_value,
            raw=raw,
            element_name=element.name if element else '',
            element_type=element.element_type if element else '',
        )

        mapped.append({
            'action_type': action_type,
            'page_filter': (element.page if element and element.page else current_page) or '',
            'element_id': element.id if element else None,
            'input_value': input_value,
            'wait_time': 1000,
            'assert_type': '',
            'assert_value': '',
            'description': desc[:500],
            'raw': raw,
            **extras,
        })

    if urls and not any(s.get('action_type') == 'navigateUrl' for s in mapped):
        mapped.insert(0, {
            'action_type': 'navigateUrl',
            'page_filter': default_page,
            'element_id': None,
            'input_value': urls[0],
            'wait_time': 1000,
            'assert_type': '',
            'assert_value': '',
            'description': _build_step_description(action='navigate', url=urls[0])[:500],
            'raw': '',
            **_element_step_extras(None),
        })

    return {
        'parse_result': parse,
        'steps': mapped,
        'step_count': len(mapped),
        'created_element_ids': created_ids,
        'target_url': parse.get('target_url') or (urls[0] if urls else ''),
        'captures_used': len(capture_used),
    }


def _snake(name: str) -> str:
    s = re.sub(r'[^\w\u4e00-\u9fff]+', '_', name or 'item')
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
    return s.lower().strip('_') or 'item'


def _scaffold_files(language: str, *, has_captcha: bool) -> dict[str, str]:
    """返回相对 generated/{scenario}/ 的脚手架文件。"""
    files: dict[str, str] = {}
    if language == 'python':
        mapping = {
            'pytest.ini': 'pytest.ini.tpl',
            'requirements.txt': 'requirements.txt.tpl',
            '.env.example': 'env.example.tpl',
            '.gitignore': 'gitignore.tpl',
            'tests/conftest.py': 'conftest.py.tpl',
            'tests/helpers/trace_support.py': 'trace_support.py.tpl',
            'assets/report.css': 'report.css.tpl',
            'scripts/open-report.sh': 'open-report.sh.tpl',
            'scripts/start-codegen.sh': 'start-codegen.sh.tpl',
            'scripts/serve_report.py': 'serve_report.py.tpl',
        }
        for rel, tpl in mapping.items():
            content = _read_template(tpl)
            if rel == 'requirements.txt' and has_captcha:
                if 'ddddocr' not in content:
                    content = content.rstrip() + '\nddddocr==1.5.6\n'
                else:
                    content = content.replace('# ddddocr==1.5.6', 'ddddocr==1.5.6')
            files[rel] = content
        if has_captcha:
            files['tests/helpers/captcha.py'] = _read_template('captcha.py.tpl')
        files['tests/pages/__init__.py'] = ''
        files['tests/data/__init__.py'] = ''
        files['tests/specs/__init__.py'] = ''
        files['tests/helpers/__init__.py'] = ''
        files['tests/fixtures/.gitkeep'] = ''
    else:
        files['playwright.config.js'] = (
            "module.exports = {\n"
            "  testDir: './tests/specs',\n"
            "  reporter: [['html', { open: 'never' }]],\n"
            "  use: { trace: 'on' },\n"
            "};\n"
        )
        files['package.json'] = json.dumps({
            'name': 'codegen-generated',
            'private': True,
            'devDependencies': {'@playwright/test': '^1.49.0'},
            'scripts': {'test': 'playwright test'},
        }, indent=2)
        files['.gitignore'] = _read_template('gitignore.tpl') or 'node_modules/\ntest-results/\nplaywright-report/\n'
        files['.env.example'] = _read_template('env.example.tpl')
    return files


def conversion_to_dict(conversion) -> dict[str, Any]:
    plan_path = ''
    plans = _media_root() / 'plans' / f'{conversion.scenario}-test-plan.md'
    if plans.exists():
        plan_path = str(plans.relative_to(_media_root())).replace('\\', '/')
    return {
        'id': conversion.id,
        'project_id': conversion.project_id,
        'scenario': conversion.scenario,
        'language': conversion.language,
        'target_url': conversion.target_url,
        'recorded_name': conversion.recorded_name,
        'recorded_content': conversion.recorded_content,
        'parse_result': conversion.parse_result,
        'plan_md': conversion.plan_md,
        'plan_status': conversion.plan_status,
        'plan_path': plan_path,
        'user_cases_md': conversion.user_cases_md,
        'generated_files': conversion.generated_files,
        'generated_script_ids': conversion.generated_script_ids,
        'generated_page_object_ids': conversion.generated_page_object_ids,
        'status': conversion.status,
        'error': conversion.error,
        'source_script_id': conversion.source_script_id,
        'created_at': conversion.created_at.isoformat() if conversion.created_at else None,
        'updated_at': conversion.updated_at.isoformat() if conversion.updated_at else None,
    }


if __name__ == '__main__':
    # ponytail: 匹配逻辑自检，改评分规则时应先挂这里
    _caps = [
        {'locators': [
            {'strategy': 'css', 'value': 'input[name="password"]'},
            {'strategy': 'placeholder', 'value': '请输入密码'},
        ]},
        {'locators': [
            {'strategy': 'role', 'value': 'button[name="登录"]'},
        ]},
    ]
    _used: set[int] = set()
    assert _take_best_capture(
        _caps, _used, primary_strategy='css', primary_value='input[name="password"]', sequential_idx=1
    ) is _caps[0]
    assert _take_best_capture(
        _caps, _used, primary_strategy='role', primary_value='button[name="登录"]', sequential_idx=0
    ) is _caps[1]
    assert _capture_match_score(_caps[0], 'css', 'input[name="password"]') >= 80

    # 同策略多表达式：均可保留；同策略同表达式去重
    _multi = [
        {'strategy': 'css', 'value': '#pwd'},
        {'strategy': 'css', 'value': 'input[name="password"]'},
        {'strategy': 'CSS', 'value': 'input[name="password"]'},  # 策略大小写不同但表达式相同 → 去重
        {'strategy': 'xpath', 'value': '//*[@id="pwd"]'},
        {'strategy': 'xpath', 'value': '/html/body/input[1]'},
    ]
    _seen: set[tuple[str, str]] = set()
    _kept: list[tuple[str, str]] = []
    for _loc in _multi:
        _s = (_loc['strategy'] or '').strip()
        _v = (_loc['value'] or '').strip()
        _key = (_s.lower(), _v)
        if _key in _seen:
            continue
        _seen.add(_key)
        _kept.append((_s.lower(), _v))
    assert _kept == [
        ('css', '#pwd'),
        ('css', 'input[name="password"]'),
        ('xpath', '//*[@id="pwd"]'),
        ('xpath', '/html/body/input[1]'),
    ], _kept
    print('capture_match selfcheck ok')

