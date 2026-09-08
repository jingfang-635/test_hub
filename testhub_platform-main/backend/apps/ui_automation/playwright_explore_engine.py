"""
Playwright 探索测试引擎 — 对齐 playwright-explore-to-test 技能四阶段流程。

阶段：
  1. 理解输入（URL / 用例描述 → LLM 规划探索步骤矩阵）
  2. Playwright 无头浏览器探索界面，逐步操作并采集元素坐标 + 截图
  3. 基于探索结果 + 定位策略生成 Playwright 测试代码
  4. 落库（AIExplorationCase / AIExplorationStep）+ WebSocket 实时投屏

与 ai_exploration.py 的 browser-use 实现互补：
  - browser-use 走自主探索（AI 控浏览器）
  - 本引擎走结构化探索（LLM 规划 → Playwright 执行 → 采集定位器 → 生成脚本）
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import random
import re
import time
import uuid
from typing import Any

from asgiref.sync import sync_to_async

# 后台线程中使用 thread_sensitive=False 避免 sync_to_async 死锁
def _db(func):
    """sync_to_async 包装，禁用 thread_sensitive 避免后台线程死锁。"""
    return sync_to_async(func, thread_sensitive=False)
from django.conf import settings

logger = logging.getLogger('django')

# 与 element_picker_service / playwright_engine 一致的浏览器路径
os.environ.setdefault(
    'PLAYWRIGHT_BROWSERS_PATH',
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'ms-playwright',
    ),
)

try:
    from playwright.async_api import async_playwright, Page, BrowserContext
except ImportError:
    async_playwright = None  # type: ignore[assignment]
    Page = None  # type: ignore[assignment]
    BrowserContext = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# 元素定位策略（对齐 skill references/locator-strategy.md）
# ---------------------------------------------------------------------------

# 页面内采集元素信息的 JS（精简版，复用 element_picker 的 buildLocators 思路）
_SNAPSHOT_JS = r"""
() => {
  function cssEscape(s) {
    if (window.CSS && CSS.escape) return CSS.escape(s);
    return String(s).replace(/[^a-zA-Z0-9_-]/g, c => '\\' + c);
  }
  function getCssPath(node, { stopAtId } = { stopAtId: true }) {
    const parts = [];
    let cur = node;
    while (cur && cur.nodeType === 1 && cur !== document.documentElement) {
      if (stopAtId && cur.id) { parts.unshift('#' + cssEscape(cur.id)); break; }
      let part = cur.tagName.toLowerCase();
      const parent = cur.parentElement;
      if (parent) {
        const same = Array.from(parent.children).filter(c => c.tagName === cur.tagName);
        if (same.length > 1) part += ':nth-of-type(' + (same.indexOf(cur) + 1) + ')';
      }
      parts.unshift(part);
      cur = parent;
    }
    return parts.join(' > ');
  }
  function getXPath(node, { preferId } = { preferId: true }) {
    if (preferId && node.id) return '//*[@id="' + node.id.replace(/"/g, '\\"') + '"]';
    const parts = [];
    let cur = node;
    while (cur && cur.nodeType === 1) {
      let ix = 1;
      let sib = cur.previousElementSibling;
      while (sib) { if (sib.tagName === cur.tagName) ix++; sib = sib.previousElementSibling; }
      parts.unshift(cur.tagName.toLowerCase() + '[' + ix + ']');
      cur = cur.parentElement;
    }
    return '/' + parts.join('/');
  }
  function buildLocators(node) {
    const out = [];
    const push = (priority, strategy, api, value) => {
      if (!value || !String(value).trim()) return;
      const v = String(value).trim().slice(0, 500);
      if (out.some(x => x.strategy === strategy && x.value === v)) return;
      out.push({ priority, strategy, api, value: v });
    };
    const q = s => String(s).replace(/"/g, '\\"');
    const tag = (node.tagName || '').toLowerCase();

    // 1. data-testid
    const testid = node.getAttribute('data-testid') || node.getAttribute('data-test-id');
    if (testid) push(1, 'test-id', "getByTestId", testid);

    // 2. role + accessible name
    const role = node.getAttribute('role') || ({
      button: 'button', a: 'link',
      input: (node.type === 'checkbox' ? 'checkbox' : node.type === 'radio' ? 'radio' : 'textbox'),
      select: 'combobox', textarea: 'textbox',
    })[tag];
    const accessibleName = (node.getAttribute('aria-label') || node.getAttribute('placeholder')
      || (node.innerText || '').trim().slice(0, 60) || node.getAttribute('value') || '').trim();
    if (role && accessibleName) push(2, 'role', "getByRole", role + '[name="' + q(accessibleName) + '"]');
    else if (role) push(2, 'role', "getByRole", role);

    // 3. id
    if (node.id) push(3, 'id', "locator", '#' + cssEscape(node.id));

    // 4. CSS class + tag
    const classRaw = (typeof node.className === 'string' ? node.className : '') || '';
    const classes = classRaw.trim().split(/\s+/).filter(c => c && c.length <= 48 && !/[a-f0-9]{8,}/i.test(c));
    if (classes.length) push(4, 'class', "locator", tag + '.' + classes.map(cssEscape).join('.'));

    // 5. XPath
    push(5, 'xpath', "locator", getXPath(node, { preferId: true }));

    return out;
  }

  const interactiveSelectors = [
    'a[href]', 'button', 'input', 'textarea', 'select',
    '[role="button"]', '[role="link"]', '[role="tab"]',
    '[onclick]', '.el-button', '.el-link', '.el-input__inner',
    '.ant-btn', '.ant-input', '[data-testid]',
  ];
  const seen = new Set();
  const elements = [];
  function addNode(el) {
    if (!el || seen.has(el)) return;
    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) return; // 不可见元素跳过
    seen.add(el);
    const inView = rect.bottom >= 0 && rect.top <= window.innerHeight
      && rect.right >= 0 && rect.left <= window.innerWidth;
    const locators = buildLocators(el);
    const text = (el.innerText || el.textContent || '').trim().slice(0, 80);
    const tag = (el.tagName || '').toLowerCase();
    const type = el.getAttribute('type') || '';
    const placeholder = el.getAttribute('placeholder') || '';
    elements.push({
      index: elements.length,
      tag,
      type,
      text,
      placeholder,
      role: el.getAttribute('role') || '',
      in_view: inView,
      locators,
      rect: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
    });
  }
  // 主文档：采集全部可交互元素（含视口外，Playwright 点击时会自动滚动到元素）
  for (const sel of interactiveSelectors) {
    document.querySelectorAll(sel).forEach(addNode);
  }
  // 开放 Shadow DOM 内的可交互元素（querySelectorAll 不穿透 shadowRoot）
  document.querySelectorAll('*').forEach(el => {
    const sr = el.shadowRoot;
    if (!sr) return;
    for (const sel of interactiveSelectors) {
      try { sr.querySelectorAll(sel).forEach(addNode); } catch (e) { /* ignore */ }
    }
  });
  return { url: location.href, title: document.title, elements };
}
"""

# ---------------------------------------------------------------------------
# LLM 调用
# ---------------------------------------------------------------------------

def _get_llm_config(task):
    """获取任务关联的 AI 模型配置，回退到 browser_use_text 角色。"""
    from apps.requirement_analysis.models import AIModelConfig
    if task.ai_model_config_id:
        cfg = AIModelConfig.objects.filter(id=task.ai_model_config_id, is_active=True).first()
        if cfg:
            return cfg
    return AIModelConfig.objects.filter(role='browser_use_text', is_active=True).first()


async def _run_llm(config, messages, max_tokens=8192, timeout=300):
    """异步调用 LLM，返回文本。

    默认超时 300s（大快照规划 prompt 较长）；响应无文本时自动诊断原因，
    若为 finish_reason=length（推理模型思考耗尽 max_tokens）则翻倍重试一次。
    """
    from apps.requirement_analysis.models import AIModelService

    def _finish_reason(r) -> str:
        try:
            return (r.get('choices') or [{}])[0].get('finish_reason') or ''
        except Exception:
            return ''

    async def _call(mt: int, no_proxy: bool = False):
        try:
            return await asyncio.wait_for(
                AIModelService.call_openai_compatible_api(
                    config, messages, max_tokens=mt, no_proxy=no_proxy),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            raise RuntimeError(f'LLM 请求超时（{timeout}s），请检查 AI 模型服务或网络代理') from None

    async def _call_with_fallback(mt: int):
        """先按系统代理配置请求；网络层断连/重置时绕过代理直连重试一次。"""
        try:
            return await _call(mt)
        except RuntimeError:
            raise
        except Exception as e:
            msg = str(e) or repr(e)
            if 'API返回错误' in msg:
                # HTTP 状态错误（鉴权/参数问题），直连重试无意义
                raise
            await asyncio.sleep(1)
            return await _call(mt, no_proxy=True)

    resp = await _call_with_fallback(max_tokens)
    text = _extract_ai_text(resp)
    if text:
        return text

    finish = _finish_reason(resp)
    if finish == 'length':
        # 推理模型常把 max_tokens 全部耗在思考上导致 content 为空，翻倍重试一次
        resp = await _call_with_fallback(max_tokens * 2)
        text = _extract_ai_text(resp)
        if text:
            return text

    err = resp.get('error') if isinstance(resp, dict) else None
    detail = err.get('message') if isinstance(err, dict) else (str(err) if err else '')
    msg = 'AI 返回内容为空'
    if finish == 'length':
        msg += f'（输出被 max_tokens={max_tokens} 截断，可能为推理模型，建议增大 max_tokens 或换非推理模型）'
    if detail:
        msg += f'；API 错误: {detail}'
    else:
        msg += f'；原始响应片段: {str(resp)[:300]}'
    raise RuntimeError(msg)


def _extract_ai_text(resp: dict) -> str:
    """从 OpenAI 兼容响应提取文本，兼容 reasoning_content。"""
    try:
        msg = (resp.get('choices') or [{}])[0].get('message') or {}
        content = msg.get('content') or ''
        if not content:
            content = msg.get('reasoning_content') or ''
        return content.strip()
    except Exception:
        return ''


def _strip_code_fence(text: str) -> str:
    text = (text or '').strip()
    if text.startswith('```'):
        text = re.sub(r'^```(?:json|python|javascript|typescript|ts|md|markdown)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
    return text.strip()


# ---------------------------------------------------------------------------
# 阶段 1：LLM 规划探索步骤
# ---------------------------------------------------------------------------

def _build_planning_prompt(
    task,
    snapshot_summary: dict[str, Any],
    recent_case_names: list[str] | None = None,
) -> list[dict[str, str]]:
    """构造给 LLM 的规划 prompt，返回探索步骤矩阵。"""
    url = task.start_url
    ds = task.data_source
    case_content = (task.data_content or '').strip()
    intent = (task.intent_content or '').strip()

    # 完整快照传给 LLM（仅做长度兜底，避免 token 爆炸）
    page_info = json.dumps(snapshot_summary, ensure_ascii=False)[:16000]
    case_driven = ds == 'case_driven' and bool(case_content)

    # target 必须逐字引用快照原文，禁止自造描述（如"账号输入框"）
    target_rule = (
        '- target 必须逐字引用页面快照中某个元素的 text 或 placeholder 原文（一字不差复制），'
        '严禁使用"账号输入框""搜索按钮"这类自造描述\n'
    )

    # assert 步骤必须给出结构化校验目标，禁止自造概括词（对齐 skill 的真实 expect 断言）
    assert_rule = (
        '- assert 步骤必须二选一提供校验目标：\n'
        '  * "expect"：操作成功后页面上必定出现的逐字文案（必须是快照中真实存在、或点击后确定出现的原文，'
        '如"退出登录""加入购物车成功"），严禁写"登录表单""搜索结果列表""相关内容"这类页面上不存在的概括词；\n'
        '  * "expect_url"：跳转后 URL 中必定包含的片段（如"/list?st=1"、"/order"）；\n'
        '  assert 步骤的 target 仍写中文断言说明，程序实际按 expect/expect_url 校验\n'
    )

    if case_driven:
        system = (
            '你是 Playwright UI 自动化测试专家。用户已上传功能用例文件（Excel/XMind/Markdown 解析结果），'
            '请严格依据文件中的功能用例规划探索测试步骤矩阵。输出严格 JSON，不要 markdown 围栏。\n'
            '格式：{"cases":[{"id":"EX-001","name":"用例名称","steps":['
            '{"action":"navigate|click|fill|select|assert","target":"元素描述或定位器",'
            '"value":"输入值（fill时必填）","expect":"assert时：页面必须出现的逐字文案",'
            '"expect_url":"assert时：URL必须包含的片段","description":"步骤说明"}]}]}\n'
            '规则：\n'
            '- 文件中的每条功能用例对应一条 case，name 必须逐字复制【用例N】后面的用例名称原文（如"登录成功验证"），'
            '严禁把 name 写成"1""2""用例1""EX-001"等序号\n'
            '- 用例顺序与文件【用例1】【用例2】…序号一致，不得遗漏、合并或自行新增用例\n'
            '- 操作步骤按文件中的步骤顺序逐条转换为 click/fill/select/navigate 动作\n'
            '- action 可选：navigate（导航/打开页面）、click（点击按钮/链接/菜单）、fill（输入框输入）、select（下拉选择）、assert（断言）\n'
            + target_rule +
            '- 文件中的"预期结果"转换为 assert 步骤\n'
            + assert_rule +
            '- fill 步骤必须从步骤描述中提取输入值放入 value\n'
            '- 每条用例开头按需补充 navigate 步骤打开目标页面\n'
            '- 步骤数控制在 3-12 步/用例，用例数量以文件为准（最多 20 条）'
        )
    else:
        system = (
            '你是 Playwright UI 自动化测试专家。根据用户提供的 URL、页面快照和测试意图，'
            '规划探索测试步骤矩阵。输出严格 JSON，不要 markdown 围栏。\n'
            '格式：{"cases":[{"id":"EX-001","name":"用例名称","steps":['
            '{"action":"navigate|click|fill|select|assert","target":"元素描述或定位器",'
            '"value":"输入值（fill时必填）","expect":"assert时：页面必须出现的逐字文案",'
            '"expect_url":"assert时：URL必须包含的片段","description":"步骤说明"}]}]}\n'
            '规则：\n'
            '- 每个验证点一条用例，不要合并多个场景\n'
            '- 若提供了用户意图：意图指定的场景（如登录、指定重点功能）必须规划为最前面的用例并优先完整执行；'
            '意图中给出的账号、密码、验证方式等输入信息必须作为对应 fill 步骤的 value 原样使用\n'
            '- action 可选：navigate（导航）、click（点击）、fill（输入）、select（下拉选择）、assert（断言）\n'
            + target_rule +
            '- 只规划页面快照中真实存在的元素，快照里没有的功能不要凭空编造\n'
            '- 跨页面流程必须包含全部中间步骤：如需要"点击商品详情页的立即购买"，必须先有"点击商品进入详情页"步骤；'
            '禁止在当前页面规划只有跳转后才存在的元素\n'
            '- 登录/注册等弹窗场景：先点击页面上的入口链接打开弹窗，再操作弹窗内的输入框和提交按钮；'
            '提交步骤的 target 必须指向弹窗内的提交按钮（通常是 button 标签），而不是页面头部同名链接\n'
            + assert_rule +
            '- 步骤数控制在 3-8 步/用例\n'
            '- 用例数量根据页面快照中的功能自行决定：快照里能识别出多少个独立可测的功能场景，就规划多少条用例，不强设上限'
        )

    parts = [f'目标URL：{url}', f'页面快照：{page_info}']
    if case_driven:
        parts.append(f'功能用例（上传文件解析结果，请严格按此规划）：\n{case_content}')
        if intent:
            parts.append(f'用户意图（辅助参考）：{intent}')
    else:
        parts.append('数据来源：自主探索，只基于页面快照中真实出现的元素规划。')
        if intent:
            # 用户意图优先级最高：登录信息/重点功能必须最优先完成，随机侧重点让位
            parts.append(f'用户意图（最高优先级，必须最优先规划并完整覆盖，对应用例排在最前）：\n{intent}')
        else:
            # 无用户意图时才随机选侧重点，避免每轮矩阵雷同
            focus = '、'.join(random.sample(_EXPLORATION_FOCUS_HINTS, k=2))
            parts.append(f'本轮探索侧重点（优先覆盖这些方向，前提是快照中存在相关元素）：{focus}')
        if recent_case_names:
            parts.append(
                '近期已探索过的用例（本轮避免重复同名或同场景的用例，请挖掘其他功能场景；'
                '用户意图明确要求的场景除外，必须照常规划）：'
                + '、'.join(recent_case_names)
            )

    return [
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': '\n'.join(parts)},
    ]


def _normalize_step(s: dict[str, Any]) -> dict[str, Any]:
    """规范化单个步骤（规划与 re-plan 共用），保留结构化断言字段。"""
    return {
        'action': s.get('action', 'other'),
        'target': s.get('target', ''),
        'value': s.get('value', ''),
        'expect': (s.get('expect') or '').strip(),
        'expect_url': (s.get('expect_url') or '').strip(),
        'description': s.get('description', ''),
    }


def _compact_snapshot(snapshot: dict[str, Any], limit: int = 150) -> dict[str, Any]:
    """压缩快照供 LLM 规划：视口内元素优先，超出截断。"""
    els = snapshot.get('elements', [])
    ordered = sorted(els, key=lambda e: (0 if e.get('in_view', True) else 1, e.get('index', 0)))
    return {
        'url': snapshot.get('url', ''),
        'title': snapshot.get('title', ''),
        'elements': [
            {
                'text': e.get('text', ''),
                'tag': e.get('tag', ''),
                'type': e.get('type', ''),
                'placeholder': e.get('placeholder', ''),
                'role': e.get('role', ''),
            }
            for e in ordered[:limit]
        ],
    }


def _repair_json(text: str) -> str:
    """修复 LLM 输出中常见的 JSON 语法问题，尽量让 json.loads 能解析。

    处理：代码围栏、多余前后缀、尾随逗号、注释、单引号、未转义换行等。
    """
    s = _strip_code_fence(text)
    # 提取首个 { ... } 块（含嵌套，用括号配对）
    start = s.find('{')
    if start < 0:
        return s
    depth = 0
    in_str = False
    esc = False
    end = -1
    for i in range(start, len(s)):
        ch = s[i]
        if in_str:
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                end = i
                break
    if end < 0:
        end = len(s)
    s = s[start:end + 1]

    # 去掉 // 和 /* */ 注释（保留字符串内的）
    out = []
    in_str = False
    esc = False
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == '\\':
                esc = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
            continue
        if ch == '/' and i + 1 < n and s[i + 1] == '/':
            while i < n and s[i] != '\n':
                i += 1
            continue
        if ch == '/' and i + 1 < n and s[i + 1] == '*':
            i += 2
            while i + 1 < n and not (s[i] == '*' and s[i + 1] == '/'):
                i += 1
            i += 2
            continue
        out.append(ch)
        i += 1
    s = ''.join(out)

    # 去掉尾随逗号：,} 或 ,]
    s = re.sub(r',\s*([}\]])', r'\1', s)
    return s


def _parse_plan(raw: str) -> list[dict[str, Any]]:
    """解析 LLM 返回的探索步骤矩阵 JSON（含容错修复）。"""
    cleaned = _repair_json(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # 修复后仍失败：尝试逐条提取 cases 数组中的对象（容忍部分损坏）
        data = _parse_cases_fallback(cleaned)
    cases = data.get('cases') or []
    # 规范化
    result = []
    for c in cases:
        steps = c.get('steps') or []
        norm_steps = []
        for s in steps:
            norm_steps.append(_normalize_step(s))
        result.append({
            'id': c.get('id', f'EX-{len(result) + 1}'),
            'name': c.get('name', f'探索用例{len(result) + 1}'),
            'steps': norm_steps,
        })
    return result


def _parse_cases_fallback(text: str) -> dict:
    """容错解析：从文本中逐个提取 cases 数组里的用例对象。

    当整体 JSON 损坏时，用括号配对逐个提取 { ... } 对象，尽量保留可用用例。
    """
    cases: list[dict] = []
    i = 0
    n = len(text)
    while i < n:
        j = text.find('{', i)
        if j < 0:
            break
        depth = 0
        in_str = False
        esc = False
        k = j
        while k < n:
            ch = text[k]
            if in_str:
                if esc:
                    esc = False
                elif ch == '\\':
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    break
            k += 1
        obj_text = text[j:k + 1]
        i = k + 1
        try:
            obj = json.loads(obj_text)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        # 只接受含 name 或 steps 的用例对象
        if 'name' in obj or 'steps' in obj:
            cases.append(obj)
    return {'cases': cases}


def _parse_document_case_names(data_content: str) -> list[str]:
    """从功能用例文本（data_content）中按序号从小到大提取用例名称。

    文本由 case_file_parser._cases_to_text 生成，格式为：
        【用例1】用例名称
        【用例2】用例名称
    """
    names: list[tuple[int, str]] = []
    for m in re.finditer(r'【用例(\d+)】\s*(.+)', data_content or ''):
        try:
            idx = int(m.group(1))
        except ValueError:
            continue
        name = m.group(2).strip()
        if name:
            names.append((idx, name))
    # 按序号从小到大排序
    names.sort(key=lambda x: x[0])
    return [n for _, n in names]


def _reorder_cases_by_document(cases_plan: list[dict[str, Any]], data_content: str) -> list[dict[str, Any]]:
    """功能用例驱动模式下，按文档序号强制覆盖用例名称，并按文档顺序对齐。

    不以 LLM 返回的 name 做模糊匹配（LLM 常把名称写成"1""2"或 EX-001），
    直接按文档序号 i 把第 i 条规划用例的 name 强制设为文档中的真实用例名称。
    """
    doc_names = _parse_document_case_names(data_content)
    if not doc_names:
        return cases_plan

    result: list[dict[str, Any]] = []
    for i, case in enumerate(cases_plan):
        c = dict(case)
        if i < len(doc_names):
            c['name'] = doc_names[i]
            c['id'] = f'EX-{i + 1:03d}'
        else:
            # 超出文档条数的规划用例保留，但编号顺延
            c['id'] = c.get('id') or f'EX-{i + 1:03d}'
            if not (c.get('name') or '').strip() or re.fullmatch(r'\d+', str(c.get('name', '')).strip()):
                c['name'] = f'探索用例{i + 1}'
        result.append(c)

    # 文档中有、但 LLM 漏规划的用例：补空壳（仅名称），保证矩阵按文档序号完整展示
    if len(result) < len(doc_names):
        for i in range(len(result), len(doc_names)):
            result.append({
                'id': f'EX-{i + 1:03d}',
                'name': doc_names[i],
                'steps': [],
            })
    return result


async def _replan_remaining_steps(
    llm_config,
    task,
    case_plan: dict[str, Any],
    done_steps: list[dict[str, Any]],
    failed_step: dict[str, Any],
    failure_detail: str,
    page,
) -> list[dict[str, Any]] | None:
    """步骤失败/断言失败后，带当前页面快照让 LLM 重新规划"剩余步骤"（每用例最多一次）。

    对齐 skill heal 流程中"依据真实页面修正后续动作"的闭环，避免一次性规划在跨页面流程上连环跑偏。
    """
    try:
        snap = await _snapshot_page(page)
    except Exception:
        snap = {'url': page.url if page else '', 'title': '', 'elements': []}
    summary = json.dumps(_compact_snapshot(snap), ensure_ascii=False)[:12000]

    done_desc = '\n'.join(
        f"{i + 1}. [{s.get('action')}] {s.get('action_description', '')[:120]}"
        for i, s in enumerate(done_steps)
    ) or '（无）'

    system = (
        '你是 Playwright UI 自动化测试专家。探索执行偏离了预期，请依据"当前页面真实快照"修正剩余步骤。'
        '输出严格 JSON，不要 markdown 围栏：\n'
        '{"steps":[{"action":"navigate|click|fill|select|assert","target":"元素文本或定位器",'
        '"value":"fill时必填的输入值","expect":"assert时：页面必须出现的逐字文案",'
        '"expect_url":"assert时：URL必须包含的片段","description":"步骤说明"}]}\n'
        '规则：\n'
        '- target 必须逐字引用当前快照中元素的 text/placeholder 原文，严禁自造"账号输入框"类描述\n'
        '- 只规划当前快照真实存在的元素；若需要先导航/点击打开目标页面，把这些恢复步骤一并规划在最前面\n'
        '- assert 必须填 expect（快照中真实存在的逐字文案，禁止"列表""表单"类概括词）或 expect_url\n'
        '- fill 必须带 value；步骤数 3-8 步，从当前页面状态继续完成原用例目标'
    )
    user = (
        f'目标URL：{task.start_url}\n'
        f'用例名称：{case_plan.get("name", "")}\n'
        f'已完成步骤：\n{done_desc}\n'
        f'失败步骤：[{failed_step.get("action")}] {failed_step.get("target", "")}'
        f'（value={failed_step.get("value", "")}）\n'
        f'失败原因：{failure_detail[:300]}\n'
        f'当前URL：{snap.get("url", "")}\n'
        f'当前页面快照：{summary}'
    )
    try:
        raw = await _run_llm(llm_config, [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ], max_tokens=4096)
    except Exception as e:
        logger.warning(f're-plan LLM 调用失败: {e}')
        return None

    try:
        cleaned = _strip_code_fence(raw)
        start = cleaned.find('{')
        end = cleaned.rfind('}')
        if start >= 0 and end > start:
            cleaned = cleaned[start:end + 1]
        data = json.loads(cleaned)
        steps = [_normalize_step(s) for s in (data.get('steps') or [])]
        steps = [s for s in steps if s.get('action') and s.get('target')]
        return steps or None
    except Exception as e:
        logger.warning(f're-plan 结果解析失败: {e}; raw={raw[:200]}')
        return None


# ---------------------------------------------------------------------------
# 阶段 2：Playwright 探索界面
# ---------------------------------------------------------------------------

def _channel_layer():
    """获取 Django Channels 配置的 channel layer（与 WS consumer 共用同一实例）。"""
    try:
        from channels.layers import get_channel_layer
        return get_channel_layer()
    except Exception as e:
        logger.warning(f"探索投屏: get_channel_layer 失败: {e}")
        return None


async def _push_screenshot(page, channel, group_name: str, task_id: int):
    """截一帧推 WS。"""
    if not channel or not page or page.is_closed():
        return
    try:
        raw = await page.screenshot(type='jpeg', quality=70)
        img = 'data:image/jpeg;base64,' + base64.b64encode(raw).decode('ascii')
        await channel.group_send(group_name, {
            'type': 'screenshot_update',
            'image': img,
        })
    except Exception as e:
        logger.debug(f"探索投屏截图失败: {e}")


async def _save_screenshot_file(page) -> str:
    """截图保存到 media，返回 URL 路径。"""
    if not page or page.is_closed():
        return ''
    try:
        raw = await page.screenshot(type='png')
        folder = os.path.join(settings.MEDIA_ROOT, 'exploration_screenshots')
        os.makedirs(folder, exist_ok=True)
        fname = f"{uuid.uuid4().hex[:12]}.png"
        with open(os.path.join(folder, fname), 'wb') as f:
            f.write(raw)
        return f"{settings.MEDIA_URL}exploration_screenshots/{fname}"
    except Exception as e:
        logger.warning(f"⚠️ 探索截图保存失败: {e}")
        return ''


async def _snapshot_page(page) -> dict[str, Any]:
    """获取页面可交互元素快照（主文档 + 所有可访问 iframe/subframe）。"""
    if not page or page.is_closed():
        return {'url': '', 'title': '', 'elements': []}
    try:
        result = await page.evaluate(_SNAPSHOT_JS)
    except Exception as e:
        logger.warning(f"页面快照失败: {e}")
        return {'url': page.url if page else '', 'title': '', 'elements': []}

    result = result or {'url': '', 'title': '', 'elements': []}
    elements = result.get('elements', [])
    # 子 frame（iframe）内的可交互元素：逐个 frame 注入快照 JS，标记 frame_url
    try:
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            try:
                sub = await frame.evaluate(_SNAPSHOT_JS)
            except Exception:
                continue  # 跨源/已分离 frame 无法访问时跳过
            for el in (sub or {}).get('elements', []):
                el['frame_url'] = frame.url
                elements.append(el)
    except Exception as e:
        logger.debug(f"iframe 快照采集失败: {e}")

    # 统一重新编号
    for i, el in enumerate(elements):
        el['index'] = i
    result['elements'] = elements
    return result


# LLM target 中常见的自造描述后缀（匹配时剔除，如"账号输入框"→"账号"）
_GENERIC_SUFFIXES = (
    '输入框', '文本框', '下拉框', '复选框', '单选框', '按钮', '链接', '标签', '图标',
    '请输入', '请选择', '点击', '填写', '输入', '选择',
)

# 同义词扩展：一个业务词可能对应页面上不同的文案
_TARGET_SYNONYMS = {
    '账号': ('用户名', '手机号', '手机', '邮箱', '账户'),
    '账户': ('账号', '用户名', '手机号', '邮箱'),
    '用户名': ('账号', '手机号', '邮箱'),
    '搜索': ('search', '查找', '关键词', '关键字'),
}

# 断言描述中的噪声词（提取关键文本时剔除）
_ASSERT_NOISE = (
    '断言', '验证', '成功', '正确', '正常', '页面', '展示', '显示', '出现',
    '包含', '跳转到', '跳转', '可见', '文本', '了',
)

# 自主探索的随机侧重点（每轮随机抽 2 个，避免每轮规划出雷同矩阵）
_EXPLORATION_FOCUS_HINTS = [
    '导航菜单与页面跳转',
    '搜索与筛选',
    '商品/内容列表浏览与翻页',
    '详情页交互（查看、加入购物车等）',
    '购物车与下单流程',
    '注册/登录/退出',
    '表单校验与错误提示',
    '轮播图/广告位跳转',
    '分类目录浏览',
    '价格/优惠/活动信息展示',
    '下拉选择与筛选项组合',
]


def _keyword_candidates(target: str) -> list[str]:
    """从 LLM 生成的 target 中提取关键词候选（含同义词扩展），用于模糊匹配快照元素。"""
    t = (target or '').strip().lower()
    if not t:
        return []
    core = t
    for w in _GENERIC_SUFFIXES:
        core = core.replace(w, '')
    kws = [core] if len(core) >= 2 else []
    for key, syns in _TARGET_SYNONYMS.items():
        if key in t:
            kws.extend(syns)
    # 去重保序
    return list(dict.fromkeys(kws))


def _extract_assert_keyword(target: str) -> str:
    """从断言描述中提取要检查的关键文本。"""
    t = (target or '').strip()
    if not t:
        return ''
    # 1) 引号中的内容最可信
    m = re.search(r'["“\'「『《]([^"”\'」』》]+)["”\'」』》]', t)
    if m:
        return m.group(1).strip()
    # 2) 去掉常见噪声词后取最长的有效片段
    core = t
    for w in _ASSERT_NOISE:
        core = core.replace(w, '|')
    segs = [s.strip() for s in core.split('|') if len(s.strip()) >= 2]
    if segs:
        return max(segs, key=len)
    return ''


async def _verify_assertion(page, step: dict[str, Any]) -> tuple[bool, str]:
    """执行真实断言。

    优先使用 LLM 规划的结构化字段 expect（页面逐字文案）/ expect_url（URL 片段）；
    缺失时回退到从 target 描述句中提取关键词的旧逻辑。
    返回 (是否通过, 说明)。
    """
    target = step.get('target', '')
    expect_text = (step.get('expect') or '').strip()
    expect_url = (step.get('expect_url') or '').strip()

    # 1) 结构化：URL 片段断言
    if expect_url:
        if expect_url.lower() in (page.url or '').lower():
            return True, f'URL 包含 "{expect_url}"'
        return False, f'URL "{page.url}" 不包含 "{expect_url}"'

    try:
        body_text = await page.inner_text('body', timeout=5000)
    except Exception:
        body_text = ''

    # 2) 结构化：页面逐字文案断言
    if expect_text:
        if expect_text in (body_text or ''):
            return True, f'页面出现文本 "{expect_text}"'
        # 容错：空白归一化后再匹配一次（如"登 录"）
        if _normalize_text(expect_text) in _normalize_text(body_text or ''):
            return True, f'页面出现文本 "{expect_text}"（空白归一化匹配）'
        return False, f'页面未出现预期文本 "{expect_text}"（当前URL: {page.url}）'

    # 3) 回退：描述中明确提到 URL 时走 URL 断言
    if 'url' in (target or '').lower():
        kw = _extract_assert_keyword(re.sub(r'url', '', target, flags=re.I))
        if kw and kw.lower() in (page.url or '').lower():
            return True, f'URL 包含 "{kw}"'
        return False, f'URL "{page.url}" 不包含 "{kw}"'

    kw = _extract_assert_keyword(target)
    if not kw:
        # 无明确断言目标：仅验证页面已加载
        return (True, '无明确断言目标，页面已加载') if page.url else (False, '断言目标为空')

    # 文本可见性检查（body innerText 包含关键词）
    candidates = [kw]
    # 去掉结尾的"页面/页"再试一次（如"商品列表页"→"商品列表"）
    kw_alt = re.sub(r'(?:页面|页)$', '', kw).strip()
    if kw_alt and kw_alt != kw:
        candidates.append(kw_alt)
    for c in candidates:
        if c in (body_text or ''):
            return True, f'页面出现文本 "{c}"'

    # 兜底：关键词出现在 URL 中
    for c in candidates:
        if c.lower() in (page.url or '').lower():
            return True, f'URL 包含 "{c}"'
    return False, f'页面未出现文本 "{kw}"（当前URL: {page.url}）'


def _normalize_text(s: str) -> str:
    """归一化文本：去除全部空白字符并转小写（"登 录" → "登录"）。"""
    return re.sub(r'\s+', '', (s or '')).lower()


def _is_buttonish(el: dict) -> bool:
    """判断快照元素是否为按钮类元素（button/提交类 input/role=button/el-button）。"""
    tag = (el.get('tag') or '').lower()
    if tag == 'button':
        return True
    if tag == 'input' and (el.get('type') or '').lower() in ('button', 'submit'):
        return True
    if (el.get('role') or '').lower() == 'button':
        return True
    for loc in el.get('locators') or []:
        val = (loc.get('value') or '').lower()
        if 'el-button' in val or '.btn' in val:
            return True
    return False


def _find_element_by_target(elements: list[dict], target: str, action: str = 'other') -> dict | None:
    """根据 target 在快照元素中匹配最佳元素（动作感知评分），返回含首选 locator 的元素信息。

    评分规则：精确匹配 > 包含匹配 > 关键词命中；click 优先按钮类元素，fill/select 优先输入框，
    避免把"登录按钮"匹配到页面头部的登录链接。
    """
    if not target:
        return None
    tn = _normalize_text(target)
    if not tn:
        return None
    kws = [_normalize_text(k) for k in _keyword_candidates(target)]
    want_button = action == 'click'
    want_input = action in ('fill', 'select')
    best_el, best_score = None, 0
    for el in elements:
        text_n = _normalize_text(el.get('text'))
        ph_n = _normalize_text(el.get('placeholder'))
        score = 0
        if text_n:
            if text_n == tn:
                score = 100
            elif tn in text_n:
                score = 60
            elif len(text_n) >= 2 and text_n in tn:
                score = 40
        if ph_n:
            if ph_n == tn:
                score = max(score, 90)
            elif tn in ph_n or ph_n in tn:
                score = max(score, 55)
        if not score and kws:
            hay = text_n + '|' + ph_n
            hits = sum(1 for k in kws if k and k in hay)
            if hits:
                score = 20 + hits * 5
        if not score:
            continue
        # 动作偏好加分：点击优先真按钮，输入优先输入框
        if want_button and _is_buttonish(el):
            score += 15
        if want_input and (el.get('tag') or '').lower() in ('input', 'textarea'):
            score += 15
        if score > best_score:
            best_score, best_el = score, el
    return best_el


def _pick_best_locator(element: dict) -> dict[str, str]:
    """从元素 locators 选最佳定位器（优先级最低），返回 {strategy, api, value}。"""
    locators = element.get('locators') or []
    if not locators:
        return {'strategy': 'css', 'api': 'locator', 'value': ''}
    # 按优先级排序
    sorted_locs = sorted(locators, key=lambda x: x.get('priority', 99))
    best = sorted_locs[0]
    return {
        'strategy': best.get('strategy', 'css'),
        'api': best.get('api', 'locator'),
        'value': best.get('value', ''),
    }


def _build_playwright_locator(loc: dict[str, str]) -> tuple[str, str]:
    """将定位器 dict 转为 Playwright Python 代码片段，返回 (method, expression)。

    例如 ('get_by_role', 'button', name='登录') 或 ('locator', '#submit')
    """
    strategy = loc.get('strategy', '')
    value = loc.get('value', '')
    api = loc.get('api', 'locator')
    if api == 'getByTestId':
        return ('get_by_test_id', value)
    if api == 'getByRole':
        # 解析 role[name="..."]
        m = re.match(r'^(\w+)(?:\[name="(.+)"\])?$', value)
        if m:
            role = m.group(1)
            name = m.group(2)
            if name:
                return ('get_by_role', role, {'name': name})
            return ('get_by_role', role, {})
    if strategy == 'id':
        return ('locator', value)
    if strategy == 'xpath':
        return ('locator', f'xpath={value}')
    return ('locator', value)


async def _wait_page_settled(page, timeout: float = 6000):
    """状态型等待：等 DOM 加载与网络空闲（替代固定 sleep，SPA 跳转/弹窗渲染更可靠）。"""
    if not page or page.is_closed():
        return
    try:
        await page.wait_for_load_state('domcontentloaded', timeout=timeout)
    except Exception:
        pass
    try:
        await page.wait_for_load_state('networkidle', timeout=timeout)
    except Exception:
        pass
    await asyncio.sleep(0.3)


def _scope_for_element(page, element: dict | None):
    """元素位于 iframe 时返回对应 Frame，否则返回 Page（Frame/Page 均支持 locator/get_by_*）。"""
    if not element:
        return page
    fu = element.get('frame_url')
    if not fu:
        return page
    try:
        for frame in page.frames:
            if frame.url == fu:
                return frame
    except Exception:
        pass
    return page


async def _apply_action_to_handle(handle, action: str, value: str):
    """在已解析的 Locator 上执行 click/fill/select_option。"""
    if action == 'click':
        await handle.click(timeout=10000)
    elif action == 'fill':
        await handle.fill(value, timeout=10000)
    elif action == 'select':
        await handle.select_option(value, timeout=10000)
    else:
        raise RuntimeError(f'不支持的动作类型: {action}')


async def _perform_action(page, element: dict | None, action: str, target: str, value: str,
                          result: dict[str, Any]) -> None:
    """按匹配到的元素执行动作；element 为空或无定位器时走动作感知的语义回退。失败抛异常。"""
    if element and (result.get('locator') or {}).get('value'):
        scope = _scope_for_element(page, element)
        handle = _resolve_locator(scope, result['locator']).first
        if action == 'click':
            try:
                await handle.click(timeout=10000)
            except Exception as ce:
                # 弹窗遮罩拦截：匹配到遮罩后面的页面元素（如头部"登录"链接），
                # 改为在弹窗容器内按文本找按钮重试
                if 'intercepts pointer events' not in str(ce):
                    raise
                kw = _normalize_text(target)
                for w in _GENERIC_SUFFIXES:
                    kw = kw.replace(w, '')
                if not kw:
                    raise
                pattern = re.compile(r'\s*'.join(re.escape(ch) for ch in kw), re.I)
                modal = page.locator(
                    '[class*="dialog"], [class*="modal"], [class*="popup"], [class*="login"]'
                )
                cand = modal.locator(
                    'button:visible, [role="button"]:visible, a:visible, '
                    'input[type="submit"]:visible, input[type="button"]:visible'
                ).filter(has_text=pattern).first
                await cand.click(timeout=5000)
                result['action_description'] += ' (弹窗内按钮重试成功)'
        else:
            await _apply_action_to_handle(handle, action, value)
        return

    # 无匹配元素 / 无定位器：语义回退（动作感知，不再静默跳过）
    if action == 'click':
        # 允许文本内含空白，如"登 录"
        pattern = re.compile(r'\s*'.join(re.escape(ch) for ch in _normalize_text(target)), re.I)
        await page.get_by_text(pattern).first.click(timeout=5000)
    elif action == 'fill':
        try:
            await page.get_by_placeholder(target).first.fill(value, timeout=5000)
        except Exception:
            await page.get_by_label(target).first.fill(value, timeout=5000)
    elif action == 'select':
        await page.locator('select:visible').first.select_option(value, timeout=5000)
    else:
        raise RuntimeError(f'不支持的动作类型: {action}')


def _healed_strategy_locator(scope, strategy: str, value: str):
    """AI 自愈返回的 strategy/value 转为 Playwright Locator（strategy 取值见 ai_locator_healer）。"""
    s = (strategy or '').strip().lower()
    v = (value or '').strip()
    if not v:
        return None
    if s in ('test-id', 'testid', 'data-testid'):
        return scope.get_by_test_id(v).first
    if s == 'text':
        return scope.get_by_text(v).first
    if s == 'placeholder':
        return scope.get_by_placeholder(v).first
    if s == 'label':
        return scope.get_by_label(v).first
    if s == 'title':
        return scope.get_by_title(v).first
    if s == 'role':
        m = re.match(r'^(\w+)(?:\[[^\]]*name[=："\']+([^"\']+)["\']?\])?', v)
        if m:
            return scope.get_by_role(m.group(1), name=m.group(2)).first if m.group(2) \
                else scope.get_by_role(m.group(1)).first
        return None
    if s in ('css', 'class', 'name'):
        return scope.locator(v).first
    if s == 'id':
        return scope.locator(v if v.startswith('#') else f'#{v}').first
    if s == 'xpath':
        return scope.locator(v if v.startswith('xpath=') else f'xpath={v}').first
    return scope.locator(v).first


def _fill_element_into_result(result: dict[str, Any], element: dict | None):
    """把匹配元素的定位器/坐标写入步骤结果。"""
    if not element:
        return
    loc = _pick_best_locator(element)
    result['locator'] = loc
    result['locator_strategy'] = loc.get('strategy', '')
    result['locator_value'] = loc.get('value', '')
    result['rect'] = element.get('rect', {})
    rect = result['rect']
    result['click_point'] = {
        'x': rect.get('x', 0) + rect.get('width', 0) / 2,
        'y': rect.get('y', 0) + rect.get('height', 0) / 2,
    }


async def _execute_step(page, step: dict[str, Any], elements: list[dict],
                        llm_config=None) -> dict[str, Any]:
    """执行单个探索步骤，返回执行结果（含坐标、截图、定位器）。

    失败时执行两轮自愈（对齐 skill heal 流程）：
      1. 等页面稳定后刷新快照重新匹配元素（SPA 跳转/弹窗渲染滞后）；
      2. 调用 AI healer 根据当前 DOM 给出定位器建议并逐个探测。
    """
    action = step.get('action', 'other')
    target = step.get('target', '')
    value = step.get('value', '')
    description = step.get('description', '')

    result: dict[str, Any] = {
        'action_type': action,
        'action_description': description or f'{action} {target}',
        'element_text': target,
        'rect': {},
        'click_point': {},
        'locator': {},
        'locator_strategy': '',
        'locator_value': '',
        'page_url': '',
        'screenshot': '',
        'status': 'done',
        'healed': False,
    }

    if action == 'navigate':
        try:
            await page.goto(target, wait_until='domcontentloaded', timeout=30000)
            await _wait_page_settled(page)
            result['page_url'] = page.url
        except Exception as e:
            result['status'] = 'failed'
            result['action_description'] += f' (失败: {e})'
        result['screenshot'] = await _save_screenshot_file(page)
        return result

    if action == 'assert':
        # 断言步骤：按结构化 expect/expect_url 真实验证，失败记 failed（不假通过）
        ok, detail = await _verify_assertion(page, step)
        result['page_url'] = page.url
        if not ok:
            result['status'] = 'failed'
            result['action_description'] += f' (断言失败: {detail})'
        result['screenshot'] = await _save_screenshot_file(page)
        return result

    # 定位元素（P0：动作感知评分，click 优先按钮、fill 优先输入框）
    element = _find_element_by_target(elements, target, action)
    _fill_element_into_result(result, element)
    result['page_url'] = page.url

    # ---- 第 0 轮：按当前快照执行 ----
    try:
        await _perform_action(page, element, action, target, value, result)
        await _wait_page_settled(page)
        result['screenshot'] = await _save_screenshot_file(page)
        return result
    except Exception as e:
        last_err = str(e) or repr(e)

    # ---- 自愈第 1 轮：等页面稳定 → 刷新快照 → 重新匹配 ----
    await _wait_page_settled(page, timeout=5000)
    try:
        snap2 = await _snapshot_page(page)
        el2 = _find_element_by_target(snap2.get('elements', []), target, action)
        if el2 is not None:
            _fill_element_into_result(result, el2)
            await _perform_action(page, el2, action, target, value, result)
            result['status'] = 'done'
            result['healed'] = True
            result['action_description'] += ' (快照刷新后自愈成功)'
            await _wait_page_settled(page)
            result['screenshot'] = await _save_screenshot_file(page)
            return result
    except Exception as e:
        last_err = str(e) or repr(e)

    # ---- 自愈第 2 轮：AI healer 根据当前 DOM 给定位器建议 ----
    if llm_config is not None:
        try:
            from .ai_locator_healer import suggest_healed_locators
            failed_cands = []
            if result.get('locator_value'):
                failed_cands.append({
                    'strategy': result.get('locator_strategy', ''),
                    'value': result.get('locator_value', ''),
                })
            heal = await suggest_healed_locators(
                page,
                {'name': target, 'element_desc': description, 'element_type': action},
                failed_cands,
                last_err,
            )
            for sug in heal.get('locators') or []:
                loc = _healed_strategy_locator(page, sug.get('strategy', ''), sug.get('value', ''))
                if loc is None:
                    continue
                try:
                    await loc.wait_for(state='attached', timeout=3000)
                    await _apply_action_to_handle(loc, action, value)
                    result['status'] = 'done'
                    result['healed'] = True
                    result['locator_strategy'] = f"ai-heal:{sug.get('strategy', '')}"
                    result['locator_value'] = (sug.get('value', '') or '')[:500]
                    result['locator'] = {
                        'strategy': result['locator_strategy'],
                        'api': 'locator',
                        'value': sug.get('value', ''),
                    }
                    result['action_description'] += (
                        f" (AI自愈成功: {sug.get('strategy')}={str(sug.get('value'))[:40]})"
                    )
                    await _wait_page_settled(page)
                    result['screenshot'] = await _save_screenshot_file(page)
                    return result
                except Exception:
                    continue
        except Exception as e:
            logger.debug(f'AI 自愈调用失败: {e}')

    result['status'] = 'failed'
    result['action_description'] += f' (失败: {last_err})'
    result['screenshot'] = await _save_screenshot_file(page)
    return result


def _resolve_locator(page, loc: dict[str, str]):
    """将定位器 dict 转为 Playwright Locator 对象。"""
    parts = _build_playwright_locator(loc)
    method = parts[0]
    expr = parts[1]
    if method == 'get_by_test_id':
        return page.get_by_test_id(expr)
    if method == 'get_by_role':
        role = expr
        kwargs = parts[2] if len(parts) > 2 else {}
        return page.get_by_role(role, **kwargs)
    return page.locator(expr)


# ---------------------------------------------------------------------------
# 阶段 3：生成 Playwright 测试代码
# ---------------------------------------------------------------------------

def _js(s: Any) -> str:
    """把 Python 字符串安全转为 JS 字符串字面量（json.dumps 自动处理引号/换行/反斜杠转义）。"""
    return json.dumps(str(s if s is not None else ''), ensure_ascii=False)


def _locator_to_ts_code(loc: dict[str, str]) -> str:
    """将定位器转为 TypeScript Playwright 代码片段（字符串经 _js 转义）。"""
    api = loc.get('api', 'locator')
    value = loc.get('value', '')
    strategy = loc.get('strategy', '')
    if api == 'getByTestId':
        return f"page.getByTestId({_js(value)})"
    if api == 'getByRole':
        m = re.match(r'^(\w+)(?:\[name="(.+)"\])?$', value)
        if m:
            role = m.group(1)
            name = m.group(2)
            if name:
                return f"page.getByRole({_js(role)}, {{ name: {_js(name)} }})"
            return f"page.getByRole({_js(role)})"
    if strategy == 'xpath' or value.startswith('xpath='):
        v = value if value.startswith('xpath=') else f'xpath={value}'
        return f"page.locator({_js(v)})"
    return f"page.locator({_js(value)})"


def _generate_playwright_config(base_url: str) -> str:
    """生成 playwright.config.ts：强制 video/trace 录制（对齐 skill 合规要求）。"""
    return (
        "import { defineConfig } from '@playwright/test';\n"
        "\n"
        "export default defineConfig({\n"
        "  use: {\n"
        f"    baseURL: {_js(base_url)},\n"
        "    headless: true,\n"
        "    video: 'on',\n"
        "    trace: 'on',\n"
        "    screenshot: 'only-on-failure',\n"
        "  },\n"
        "  reporter: [['html', { open: 'never' }]],\n"
        "});\n"
    )


def _generate_test_code(task, cases_data: list[dict[str, Any]]) -> str:
    """根据探索结果生成 Playwright TypeScript 测试代码。

    - 每个用例一个 test()，步骤用 test.step 分「准备/操作/验证」AAA 结构；
    - 所有字符串经 json.dumps 转义，杜绝引号注入；
    - assert 使用规划阶段的结构化 expect/expect_url，与探索期真实断言一致。
    """
    base_url = task.start_url
    L: list[str] = [
        "import { test, expect } from '@playwright/test';",
        "",
        f"const BASE_URL = {_js(base_url)};",
        "",
        f"test.describe({_js(task.name)}, () => {{",
        "  test.beforeEach(async ({ page }) => {",
        "    await page.goto(BASE_URL);",
        "  });",
        "",
    ]

    for case in cases_data:
        case_id = case.get('id', 'EX-001')
        case_name_str = case.get('name', '探索用例')
        L.append(f"  test({_js(f'{case_id}: {case_name_str}')}, async ({{ page }}) => {{")

        for step in (case.get('steps') or []):
            action = step.get('action', 'other')
            target = step.get('target', '')
            value = step.get('value', '')
            desc = step.get('description') or f'{action} {target}'
            locator_code = step.get('locator_code', '')
            phase = '准备' if action == 'navigate' else ('验证' if action == 'assert' else '操作')
            L.append(f"    await test.step({_js(f'{phase}: {desc}')}, async () => {{")

            if action == 'navigate':
                L.append(f"      await page.goto({_js(target)});")
            elif action == 'click':
                if locator_code:
                    L.append(f"      // 定位优先级: {step.get('locator_priority', '?')}")
                    L.append(f"      await {locator_code}.click();")
                else:
                    L.append(f"      await page.getByText({_js(target)}).first().click();")
            elif action == 'fill':
                if locator_code:
                    L.append(f"      await {locator_code}.fill({_js(value)});")
                else:
                    L.append(f"      await page.getByPlaceholder({_js(target)}).first().fill({_js(value)});")
            elif action == 'select':
                if locator_code:
                    L.append(f"      await {locator_code}.selectOption({_js(value)});")
                else:
                    L.append(f"      await page.locator('select').first().selectOption({_js(value)});")
            elif action == 'assert':
                expect_url = (step.get('expect_url') or '').strip()
                expect_text = (step.get('expect') or '').strip()
                if expect_url:
                    L.append(f"      await expect(page).toHaveURL(new RegExp({_js(re.escape(expect_url))}));")
                elif expect_text:
                    L.append(f"      await expect(page.locator('body')).toContainText({_js(expect_text)});")
                else:
                    L.append(f"      await expect(page.getByText({_js(target)}).first()).toBeVisible();")
            L.append("    });")

        L.append("  });")
        L.append("")

    L.append("});")
    return '\n'.join(L)


# ---------------------------------------------------------------------------
# 阶段 4：主流程
# ---------------------------------------------------------------------------

async def run_playwright_exploration(task_id: int, stop_signals: dict):
    """Playwright 探索主流程。"""
    from .models import AIExplorationTask, AIExplorationCase, AIExplorationStep

    if async_playwright is None:
        raise RuntimeError('Playwright 未安装，请执行 pip install playwright && playwright install chromium')

    task = await _db(AIExplorationTask.objects.get)(id=task_id)

    # WebSocket 投屏
    channel = _channel_layer()
    group_name = f"ui_exploration_{task_id}"

    logs: list[str] = ['[Playwright 探索引擎] 启动...\n']

    async def append_log(msg: str):
        """追加日志并实时推送 WS。"""
        logs.append(msg + '\n')
        if channel:
            try:
                await channel.group_send(group_name, {
                    'type': 'log_update',
                    'log': msg,
                })
            except Exception:
                pass

    # ---- 阶段 1：打开页面获取快照 ----
    # 登录态复用：按站点 host 保存 storage_state（cookie/localStorage），后续同站探索免登录
    from urllib.parse import urlparse
    auth_host = urlparse(task.start_url).hostname or 'default'
    auth_dir = os.path.join(settings.MEDIA_ROOT, 'exploration_auth')
    os.makedirs(auth_dir, exist_ok=True)
    auth_file = os.path.join(auth_dir, f'{auth_host}.json')

    await append_log(f'打开页面: {task.start_url}')
    pw = await async_playwright().start()
    browser = None
    context = None
    page = None
    try:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--ignore-certificate-errors',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-gpu',
            ],
        )
        ctx_kwargs: dict[str, Any] = {'viewport': {'width': 1440, 'height': 900}}
        if os.path.exists(auth_file):
            ctx_kwargs['storage_state'] = auth_file
            await append_log(f'复用站点登录态: {auth_host}.json')
        context = await browser.new_context(**ctx_kwargs)
        page = await context.new_page()

        try:
            await page.goto(task.start_url, wait_until='domcontentloaded', timeout=30000)
            await _wait_page_settled(page)
        except Exception as e:
            await append_log(f'页面加载警告: {e}')

        await _push_screenshot(page, channel, group_name, task_id)

        # 页面快照
        snapshot = await _snapshot_page(page)
        elements = snapshot.get('elements', [])
        await append_log(f'页面快照: {len(elements)} 个可交互元素')

        # ---- 阶段 2：LLM 规划 ----
        llm_config = _get_llm_config(task)
        if not llm_config:
            raise RuntimeError('未配置可用的 AI 模型，请在配置中心启用 browser_use_text 角色')

        # 快照摘要传给 LLM（视口内元素优先，含 type 便于识别输入框）
        snapshot_summary = _compact_snapshot(snapshot)

        # 近期同 URL 的历史用例名（供规划去重，避免每轮矩阵雷同）
        def _load_recent_case_names(start_url: str) -> list[str]:
            return list(
                AIExplorationCase.objects.filter(task__start_url=start_url)
                .exclude(task_id=task.id)
                .order_by('-id')
                .values_list('name', flat=True)
                .distinct()[:30]
            )

        try:
            recent_case_names = await _db(_load_recent_case_names)(task.start_url)
        except Exception as e:
            logger.debug(f'加载历史用例名失败: {e}')
            recent_case_names = []

        await append_log('AI 规划探索步骤矩阵...')
        messages = _build_planning_prompt(task, snapshot_summary, recent_case_names)
        plan_raw = await _run_llm(llm_config, messages)
        cases_plan = _parse_plan(plan_raw)
        # 功能用例驱动：按文档序号强制覆盖用例名称（不依赖 LLM 返回的 name）
        if task.data_source == 'case_driven':
            doc_names = _parse_document_case_names(task.data_content or '')
            cases_plan = _reorder_cases_by_document(cases_plan, task.data_content or '')
            if doc_names:
                await append_log(
                    '按文档序号覆盖用例名称: '
                    + '、'.join(f'{i + 1}.{n}' for i, n in enumerate(doc_names[:20]))
                )
        # LLM 常把 name 写成 "1"/"2"，统一回退为可读名称
        for i, cp in enumerate(cases_plan):
            raw_name = str(cp.get('name') or '').strip()
            if not raw_name or re.fullmatch(r'\d+', raw_name):
                cp['name'] = f'探索用例{i + 1}'
        await append_log(f'AI 规划完成: {len(cases_plan)} 条用例')

        # ---- 推送用例矩阵给前端（探索前先展示）----
        if channel:
            try:
                await channel.group_send(group_name, {
                    'type': 'plan_update',
                    'cases': [
                        {
                            'id': cp.get('id', f'EX-{i + 1}'),
                            'name': cp.get('name', f'探索用例{i + 1}'),
                            'step_count': len(cp.get('steps', [])),
                            'steps': [
                                {
                                    'order': si + 1,
                                    'action': sp.get('action', ''),
                                    'target': sp.get('target', ''),
                                    'value': sp.get('value', ''),
                                    'expect': sp.get('expect', ''),
                                    'expect_url': sp.get('expect_url', ''),
                                    'description': sp.get('description', ''),
                                }
                                for si, sp in enumerate(cp.get('steps', []))
                            ],
                        }
                        for i, cp in enumerate(cases_plan)
                    ],
                })
            except Exception as e:
                logger.debug(f"推送 plan_update 失败: {e}")

        # ---- 阶段 3：逐步执行探索 + 采集 ----
        cases_data: list[dict[str, Any]] = []
        step_counter = 0

        for ci, case_plan in enumerate(cases_plan):
            if stop_signals.get(task_id, False):
                await append_log('收到停止信号，终止探索')
                break

            # 创建用例记录
            case_record = await _db(AIExplorationCase.objects.create)(
                task=task,
                name=case_plan.get('name', f'探索用例{ci + 1}'),
                description=f"AI 规划用例: {case_plan.get('id', '')}",
                order=ci,
                status='running',
            )

            case_steps_data: list[dict[str, Any]] = []
            # 每条用例前重新导航到起始 URL（状态型等待，确保 SPA 加载完成）
            try:
                await page.goto(task.start_url, wait_until='domcontentloaded', timeout=20000)
                await _wait_page_settled(page)
            except Exception:
                pass

            # 可变步骤队列：步骤失败后允许 LLM 带当前页面快照重新规划"剩余步骤"（每用例最多 1 次）
            pending_steps: list[dict[str, Any]] = [dict(s) for s in (case_plan.get('steps') or [])]
            replanned = False
            order = 0
            while pending_steps:
                if stop_signals.get(task_id, False):
                    break
                step_plan = pending_steps.pop(0)
                order += 1

                # 每步前刷新快照（页面可能已变化）
                current_snapshot = await _snapshot_page(page)
                current_elements = current_snapshot.get('elements', [])

                step_result = await _execute_step(page, step_plan, current_elements, llm_config)
                step_counter += 1

                # 结构化断言字段透传（供代码生成与结果核对）
                step_result['expect'] = step_plan.get('expect', '')
                step_result['expect_url'] = step_plan.get('expect_url', '')

                # 补充定位器代码
                loc = step_result.get('locator', {})
                if loc and loc.get('value'):
                    step_result['locator_code'] = _locator_to_ts_code(loc)
                    step_result['locator_priority'] = loc.get('strategy', '?')
                else:
                    step_result['locator_code'] = ''
                    step_result['locator_priority'] = ''

                # 写入步骤记录
                await _db(AIExplorationStep.objects.create)(
                    case=case_record,
                    order=order,
                    action_type=step_result.get('action_type', 'other'),
                    action_description=step_result.get('action_description', ''),
                    element_text=step_result.get('element_text', '')[:500],
                    locator_strategy=step_result.get('locator_strategy', ''),
                    locator_value=step_result.get('locator_value', '')[:500],
                    rect=step_result.get('rect', {}),
                    click_point=step_result.get('click_point', {}),
                    screenshot=step_result.get('screenshot', ''),
                    page_url=step_result.get('page_url', '')[:1000],
                    status=step_result.get('status', 'done'),
                )

                # 合并：计划字段（action/target/value/description/expect）+ 执行结果，
                # 供代码生成读取步骤语义；action_description 等执行态字段以 result 为准
                case_steps_data.append({
                    **step_plan,
                    **step_result,
                    'locator_code': step_result.get('locator_code', ''),
                    'locator_priority': step_result.get('locator_priority', ''),
                })

                heal_tag = ' [自愈]' if step_result.get('healed') else ''
                await append_log(
                    f'  [{case_plan.get("id")}] 步骤{order}{heal_tag}: '
                    f'{step_result.get("action_description", "")}'
                )
                await _push_screenshot(page, channel, group_name, task_id)

                # ---- 实时推送 step_update（右边显示点击的元素）----
                if channel:
                    try:
                        await channel.group_send(group_name, {
                            'type': 'step_update',
                            'case_id': case_record.id,
                            'case_name': case_plan.get('name', f'探索用例{ci + 1}'),
                            'step': {
                                'order': order,
                                'action_type': step_result.get('action_type', 'other'),
                                'action_description': step_result.get('action_description', ''),
                                'element_text': step_result.get('element_text', ''),
                                'locator_strategy': step_result.get('locator_strategy', ''),
                                'locator_value': step_result.get('locator_value', ''),
                                'locator_code': step_result.get('locator_code', ''),
                                'rect': step_result.get('rect', {}),
                                'click_point': step_result.get('click_point', {}),
                                'screenshot': step_result.get('screenshot', ''),
                                'page_url': step_result.get('page_url', ''),
                                'status': step_result.get('status', 'done'),
                            },
                        })
                    except Exception as e:
                        logger.debug(f"推送 step_update 失败: {e}")

                # ---- 失败后 AI 重新规划剩余步骤（对齐 skill heal：依据真实页面修正后续动作）----
                if (step_result.get('status') == 'failed' and not replanned
                        and not stop_signals.get(task_id, False)):
                    replanned = True
                    await append_log(f'  [{case_plan.get("id")}] 步骤失败，AI 依据当前页面重新规划剩余步骤...')
                    new_steps = await _replan_remaining_steps(
                        llm_config, task, case_plan,
                        case_steps_data, step_plan,
                        step_result.get('action_description', ''), page,
                    )
                    if new_steps:
                        pending_steps = new_steps  # 新规划从当前页面状态出发，替换原剩余步骤
                        await append_log(f'  [{case_plan.get("id")}] AI 已重新规划 {len(new_steps)} 个剩余步骤')
                    else:
                        await append_log(f'  [{case_plan.get("id")}] AI 重新规划无结果，继续原计划')

            case_status = 'passed'
            if any(s.get('status') == 'failed' for s in case_steps_data):
                case_status = 'failed'
            await _db(AIExplorationCase.objects.filter(id=case_record.id).update)(status=case_status)

            # ---- 推送 case_update ----
            if channel:
                try:
                    await channel.group_send(group_name, {
                        'type': 'case_update',
                        'case_id': case_record.id,
                        'case_name': case_plan.get('name', f'探索用例{ci + 1}'),
                        'status': case_status,
                        'step_count': len(case_steps_data),
                    })
                except Exception as e:
                    logger.debug(f"推送 case_update 失败: {e}")

            cases_data.append({
                'id': case_plan.get('id', f'EX-{ci + 1}'),
                'name': case_plan.get('name', f'探索用例{ci + 1}'),
                'steps': case_steps_data,
            })

        # ---- 阶段 4：生成测试代码 + 产物落盘 ----
        # P0：任务状态按用例真实结果聚合（有用例失败/无用例 → failed；停止 → stopped）
        stopped = bool(stop_signals.get(task_id, False))
        total_cases = len(cases_data)
        failed_cases = sum(
            1 for c in cases_data
            if any(s.get('status') == 'failed' for s in c.get('steps', []))
        )
        healed_steps = sum(
            1 for c in cases_data for s in c.get('steps', []) if s.get('healed')
        )
        task_status = 'stopped' if stopped else ('failed' if not cases_data or failed_cases else 'passed')

        await append_log('生成 Playwright 测试代码...')
        generated_code = _generate_test_code(task, cases_data)

        # 产物落盘：spec + playwright.config.ts（video/trace 全开，对齐 skill Step 4 合规要求）
        artifact_dir = os.path.join(settings.MEDIA_ROOT, 'exploration_tests', f'task_{task_id}')
        try:
            os.makedirs(artifact_dir, exist_ok=True)
            with open(os.path.join(artifact_dir, 'exploration.spec.ts'), 'w', encoding='utf-8') as f:
                f.write(generated_code)
            with open(os.path.join(artifact_dir, 'playwright.config.ts'), 'w', encoding='utf-8') as f:
                f.write(_generate_playwright_config(task.start_url))
            await append_log(f'测试工程已生成: {artifact_dir}（video/trace=on，可在 Node 环境执行 npx playwright test）')
        except Exception as e:
            logger.warning(f'测试产物落盘失败: {e}')

        # 保存到任务
        from django.utils import timezone
        t = await _db(AIExplorationTask.objects.get)(id=task_id)
        # generated_code 为 CharField(10000)，超长截断（完整代码见产物文件）
        if len(generated_code) > 9900:
            t.generated_code = (
                generated_code[:9900]
                + f'\n// ……完整代码见服务器 exploration_tests/task_{task_id}/exploration.spec.ts'
            )
        else:
            t.generated_code = generated_code
        t.status = task_status
        t.end_time = timezone.now()
        if t.start_time:
            t.duration = (t.end_time - t.start_time).total_seconds()
        t.logs = (t.logs or '') + ''.join(logs)
        await _db(t.save)()

        await append_log(
            f'探索结束: {total_cases} 条用例，失败 {failed_cases} 条，自愈步骤 {healed_steps} 个'
            + ('（已停止）' if stopped else '')
        )

        # ---- 推送最终测试用例结果 ----
        if channel:
            try:
                await channel.group_send(group_name, {
                    'type': 'test_result',
                    'status': task_status,
                    'cases': [
                        {'id': c.get('id'), 'name': c.get('name'), 'step_count': len(c.get('steps', []))}
                        for c in cases_data
                    ],
                    'generated_code': generated_code,
                })
            except Exception as e:
                logger.debug(f"推送 test_result 失败: {e}")

        return {
            'status': task_status,
            'cases': total_cases,
            'steps': step_counter,
            'failed_cases': failed_cases,
            'healed_steps': healed_steps,
        }

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        err_msg = f'{type(e).__name__}: {e}' if not str(e).strip() else str(e)
        logger.error(f"Playwright 探索失败: {err_msg}\n{tb}")
        await append_log(f'[错误] {err_msg}')

        from django.utils import timezone
        try:
            t = await _db(AIExplorationTask.objects.get)(id=task_id)
            t.status = 'failed'
            t.end_time = timezone.now()
            if t.start_time:
                t.duration = (t.end_time - t.start_time).total_seconds()
            t.logs = (t.logs or '') + ''.join(logs) + f"\n[错误] {err_msg}\n{tb}"
            await _db(t.save)()
        except Exception:
            pass
        return {'status': 'failed', 'error': err_msg}

    finally:
        # 保存登录态（cookie/localStorage）供后续同站探索复用，避免每轮重复登录
        if context is not None:
            try:
                await context.storage_state(path=auth_file)
            except Exception:
                pass
        # 清理浏览器
        for closer in (context, browser):
            try:
                if closer:
                    await closer.close()
            except Exception:
                pass
        try:
            await pw.stop()
        except Exception:
            pass

        # 推送结束状态
        if channel:
            try:
                await channel.group_send(group_name, {
                    'type': 'exploration_status',
                    'status': 'finished',
                    'message': '探索任务已结束',
                })
            except Exception:
                pass


def run_playwright_exploration_sync(task_id: int, stop_signals: dict):
    """同步入口（供后台线程调用）。"""
    import sys
    if sys.platform == 'win32':
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(run_playwright_exploration(task_id, stop_signals))
        finally:
            loop.close()
    return asyncio.run(run_playwright_exploration(task_id, stop_signals))