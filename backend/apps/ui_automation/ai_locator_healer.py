# -*- coding: utf-8 -*-
"""
AI 定位器自愈：主/备用定位器均失效时，分析页面并临时推荐定位器。
仅用于当次执行，不写回元素库或测试步骤。

约束：必须锚定步骤描述 / 元素名称的语义（可参考控件文案）；
页面上找不到对应意图时禁止自愈，该失败就失败。
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_MAX_DOM_CANDIDATES = 100
_MAX_SUGGESTIONS = 5

# 步骤描述里的目标文案：「加入购物车」 / 【删除】 / "搜索"
_INTENT_QUOTE_RE = re.compile(r'[「『【《"\']([^」』】》"\']{1,40})[」』】》"\']')
# 过于宽泛、几乎必然误点的定位器
_GENERIC_LOCATOR_RE = re.compile(
    r'^(?:'
    r'a|button|div|span|input|li|img|label'
    r'|(?:a|button|div|span|input)\.[a-zA-Z][\w-]{0,12}'
    r'|\.[a-zA-Z][\w-]{0,12}'
    r')$',
    re.I,
)
_GENERIC_EXACT = {
    'a', 'button', 'div', 'span', 'input', 'a.btn', 'button.btn', '.btn',
    '.el-button', 'a.el-button', 'button.el-button', '.van-button',
}


def _intent_phrases(element_data: Dict) -> List[str]:
    """从步骤说明 / 元素名提取必须命中的语义短语。"""
    phrases: List[str] = []
    seen: set[str] = set()

    def _add(p: str) -> None:
        p = (p or '').strip()
        if len(p) < 2 or p in seen:
            return
        # 过滤定位器噪声名
        if re.search(r'xpath|locator|get_by_|css=|/html|nth=', p, re.I):
            return
        seen.add(p)
        phrases.append(p)

    for key in ('step_description', 'name', 'description'):
        text = str(element_data.get(key) or '').strip()
        if not text:
            continue
        for m in _INTENT_QUOTE_RE.finditer(text):
            _add(m.group(1))
        if key == 'name':
            # recorded_加入购物车 → 加入购物车
            cleaned = re.sub(r'^(recorded_|element_|el_|auto_)+', '', text, flags=re.I).strip('_ ')
            _add(cleaned or text)
            # 名称里的中文片段也作为意图（避免 recorded_xxx 整串匹配失败）
            for zh in re.findall(r'[\u4e00-\u9fff]{2,20}', cleaned or text):
                _add(zh)

    return phrases


def _candidate_blob(c: Dict[str, Any]) -> str:
    parts = [
        c.get('text'), c.get('placeholder'), c.get('ariaLabel'), c.get('title'),
        c.get('name'), c.get('id'), c.get('class'), c.get('dataTestId'), c.get('value'),
    ]
    return ' '.join(str(p or '') for p in parts)


def _phrase_in_text(phrase: str, hay: str) -> bool:
    if not phrase or not hay:
        return False
    if phrase in hay or phrase.lower() in hay.lower():
        return True
    # 去掉空白后再比（「加 入 购 物 车」类）
    compact_p = re.sub(r'\s+', '', phrase)
    compact_h = re.sub(r'\s+', '', hay)
    return bool(compact_p) and compact_p in compact_h


def dom_matches_intent(dom_candidates: List[Dict], phrases: List[str]) -> bool:
    """当前 DOM 候选中是否出现步骤意图文案；无短语时不做拦截。"""
    if not phrases:
        return True
    for phrase in phrases:
        for c in dom_candidates or []:
            if _phrase_in_text(phrase, _candidate_blob(c)):
                return True
    return False


def is_too_generic_locator(strategy: str, value: str) -> bool:
    """拒绝 a.btn / button / .btn 等无语义锚点的宽泛定位。"""
    s = (strategy or '').strip().lower()
    v = (value or '').strip()
    if not v:
        return True
    if s in ('css', 'class'):
        raw = v[1:] if v.startswith('.') and s == 'class' else v
        if v.lower() in _GENERIC_EXACT or raw.lower() in _GENERIC_EXACT:
            return True
        if _GENERIC_LOCATOR_RE.match(v) or _GENERIC_LOCATOR_RE.match(raw):
            # 带语义 class（add-cart / search-btn）放行
            if re.search(r'(cart|search|login|submit|delete|del|confirm|cancel|primary)', v, re.I):
                return False
            return True
    if s == 'xpath':
        if re.match(r'^//?(a|button|div|span)(\[\d+\])?$', v, re.I):
            return True
    return False


def filter_heal_suggestions(
    locators: List[Dict],
    *,
    phrases: Optional[List[str]] = None,
) -> List[Dict]:
    """过滤臆想/过宽建议；text 策略必须命中意图短语。"""
    out: List[Dict] = []
    phrases = phrases or []
    for item in locators or []:
        strategy = (item.get('strategy') or '').strip()
        value = (item.get('value') or '').strip()
        if not strategy or not value:
            continue
        if is_too_generic_locator(strategy, value):
            logger.info('AI healer drop generic locator %s=%s', strategy, value[:80])
            continue
        if phrases and strategy.lower() == 'text':
            if not any(_phrase_in_text(p, value) for p in phrases):
                logger.info('AI healer drop text locator off-intent %s', value[:80])
                continue
        out.append(item)
        if len(out) >= _MAX_SUGGESTIONS:
            break
    return out


def _load_ai_config() -> Optional[Dict[str, Any]]:
    """从 AIModelConfig(browser_use_text) 或环境变量读取模型配置。"""
    try:
        # Playwright 执行在独立线程/异步事件循环中，需先清理旧连接再查库
        from django.db import close_old_connections

        close_old_connections()
        from apps.requirement_analysis.models import AIModelConfig

        config_obj = (
            AIModelConfig.objects
            .filter(role='browser_use_text', is_active=True)
            .order_by('-updated_at', '-id')
            .first()
        )
        if config_obj:
            api_key = (config_obj.api_key or '').strip()
            base_url = (config_obj.base_url or '').strip()
            model_name = (config_obj.model_name or '').strip()
            if not api_key:
                logger.warning(
                    'AIModelConfig id=%s active but api_key empty',
                    config_obj.id,
                )
            else:
                return {
                    'api_key': api_key,
                    'base_url': base_url,
                    'model_name': model_name,
                    'temperature': getattr(config_obj, 'temperature', 0.2) or 0.2,
                }
        else:
            logger.warning('No active AIModelConfig with role=browser_use_text')
    except Exception as exc:  # noqa: BLE001
        logger.warning('load AIModelConfig failed: %s', exc, exc_info=True)

    api_key = os.getenv('AUTH_TOKEN') or os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('BASE_URL') or os.getenv('OPENAI_BASE_URL')
    model_name = os.getenv('MODEL_NAME') or os.getenv('OPENAI_MODEL')
    if api_key and base_url and model_name:
        return {
            'api_key': api_key,
            'base_url': base_url,
            'model_name': model_name,
            'temperature': 0.2,
        }
    return None


async def _load_ai_config_async() -> Optional[Dict[str, Any]]:
    """在异步上下文中安全加载 AI 配置（避免 SynchronousOnlyOperation）。"""
    import asyncio

    return await asyncio.to_thread(_load_ai_config)


async def extract_dom_candidates(page, limit: int = _MAX_DOM_CANDIDATES) -> List[Dict[str, Any]]:
    """从当前页面抽取可交互节点摘要，供 AI 分析。"""
    if not page:
        return []
    try:
        return await page.evaluate(
            """(limit) => {
              const out = [];
              const sels = [
                'a', 'button', 'input', 'select', 'textarea',
                '[role="button"]', '[role="link"]', '[role="textbox"]',
                '[onclick]', '[data-testid]', '.el-button', '.van-button',
                '.el-input__inner', '.el-select', 'label'
              ].join(',');
              const seen = new Set();
              document.querySelectorAll(sels).forEach((el) => {
                if (out.length >= limit) return;
                const rect = el.getBoundingClientRect();
                if (rect.width < 2 || rect.height < 2) return;
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden') return;
                const tag = (el.tagName || '').toLowerCase();
                const id = el.id || '';
                const name = el.getAttribute('name') || '';
                const cls = (el.className || '').toString().trim().slice(0, 140);
                const text = (el.innerText || el.value || el.placeholder || '').trim().slice(0, 80);
                const key = [tag, id, name, cls, text].join('|');
                if (seen.has(key)) return;
                seen.add(key);
                out.push({
                  tag,
                  id,
                  name,
                  class: cls,
                  text,
                  type: el.getAttribute('type') || '',
                  placeholder: el.getAttribute('placeholder') || '',
                  ariaLabel: el.getAttribute('aria-label') || '',
                  title: el.getAttribute('title') || '',
                  dataTestId: el.getAttribute('data-testid') || '',
                  href: (el.getAttribute('href') || '').slice(0, 100),
                });
              });
              return out;
            }""",
            limit,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning('extract_dom_candidates failed: %s', exc)
        return []


def _chat_completions(config: Dict[str, Any], messages: List[Dict], timeout: int = 60) -> str:
    base = (config.get('base_url') or '').rstrip('/')
    url = f'{base}/chat/completions'
    # 部分网关已带 /v1
    if base.endswith('/v1'):
        url = f'{base}/chat/completions'
    elif '/chat/completions' not in base:
        if not base.endswith('/v1'):
            # 兼容只配到 host 的情况
            pass

    temperature = config.get('temperature', 0.2)
    model_lower = str(config.get('model_name') or '').lower()
    if 'kimi' in model_lower:
        temperature = 1.0

    payload = {
        'model': config['model_name'],
        'messages': messages,
        'temperature': temperature,
    }
    headers = {
        'Authorization': f"Bearer {config['api_key']}",
        'Content-Type': 'application/json',
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    choices = data.get('choices') or []
    if not choices:
        raise RuntimeError(f'empty LLM choices: {data}')
    message = choices[0].get('message') or {}
    content = message.get('content') or ''
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get('type') == 'text':
                parts.append(item.get('text') or '')
            elif isinstance(item, str):
                parts.append(item)
        content = '\n'.join(parts)
    return str(content).strip()


def _parse_heal_response(content: str) -> Dict[str, Any]:
    """解析模型返回的 JSON：failure_reason + locators。"""
    text = (content or '').strip()
    if not text:
        return {'failure_reason': 'AI 未返回有效分析', 'locators': []}

    # 去掉 markdown 代码块
    fence = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if fence:
        text = fence.group(1).strip()

    data = None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{[\s\S]*\}', text)
        if match:
            try:
                data = json.loads(match.group(0))
            except json.JSONDecodeError:
                data = None

    if not isinstance(data, dict):
        return {'failure_reason': text[:500], 'locators': []}

    reason = (
        data.get('failure_reason')
        or data.get('reason')
        or data.get('analysis')
        or data.get('fail_reason')
        or ''
    )
    raw_locators = data.get('locators') or data.get('suggestions') or []
    locators: List[Dict[str, str]] = []
    if isinstance(raw_locators, dict):
        raw_locators = [raw_locators]
    for item in raw_locators:
        if not isinstance(item, dict):
            continue
        strategy = (item.get('strategy') or item.get('type') or item.get('locator_strategy') or '').strip()
        value = (item.get('value') or item.get('locator') or item.get('locator_value') or '').strip()
        if not strategy or not value:
            continue
        locators.append({
            'strategy': strategy,
            'value': value,
            'confidence': item.get('confidence'),
            'note': item.get('note') or item.get('explanation') or '',
        })
        if len(locators) >= _MAX_SUGGESTIONS:
            break

    return {
        'failure_reason': str(reason).strip() or '主/备用定位器均未匹配到目标元素',
        'locators': locators,
    }


def _build_prompt(
    element_data: Dict,
    failed_candidates: List[Dict],
    dom_candidates: List[Dict],
    page_url: str,
    last_error: str,
    intent_phrases: List[str],
) -> str:
    element_name = element_data.get('name') or '未知元素'
    element_desc = element_data.get('description') or ''
    element_type = element_data.get('element_type') or ''
    step_desc = element_data.get('step_description') or ''
    tried = [
        {'strategy': c.get('strategy'), 'value': c.get('value')}
        for c in (failed_candidates or [])
    ]
    intent_line = '、'.join(intent_phrases) if intent_phrases else '（无明确引号文案，以元素名为准）'
    return (
        '你是 UI 自动化定位器修复专家。主/备用选择器均已失效。\n'
        '硬性约束（违反则 locators 必须为空数组）：\n'
        '1. 只能修复「步骤说明/元素名」所指的同一个控件，禁止臆造无关按钮。\n'
        f'2. 目标语义必须命中：{intent_line}。若当前 DOM 候选中看不到该文案/语义，'
        'locators 必须返回 []，在 failure_reason 说明「页面上找不到步骤目标」。\n'
        '3. 禁止宽泛定位：a.btn、button、.btn、无文本的 icon 按钮等。\n'
        '4. strategy 仅允许：css, xpath, id, name, text, role, placeholder, label, test-id, title, class。\n'
        '5. 优先 text / role(name=...) / placeholder / data-testid；css 须含稳定语义 class。\n'
        '6. 严格返回 JSON：'
        '{"failure_reason":"...","locators":[{"strategy":"text","value":"...","confidence":0.9,"note":"..."}]}\n\n'
        f'当前页面 URL: {page_url}\n'
        f'步骤说明: {step_desc or "（无）"}\n'
        f'目标元素名称: {element_name}\n'
        f'目标元素描述: {element_desc}\n'
        f'目标元素类型: {element_type}\n'
        f'必须命中的语义: {json.dumps(intent_phrases, ensure_ascii=False)}\n'
        f'已失败定位器: {json.dumps(tried, ensure_ascii=False)}\n'
        f'最后错误: {last_error}\n'
        f'页面可交互节点候选(JSON): {json.dumps(dom_candidates[:_MAX_DOM_CANDIDATES], ensure_ascii=False)}\n'
    )


async def suggest_healed_locators(
    page,
    element_data: Dict,
    failed_candidates: List[Dict],
    last_error: str = '',
) -> Dict[str, Any]:
    """
    调用 AI 分析并返回临时定位器建议。

    Returns:
        {
          'failure_reason': str,
          'locators': [{'strategy','value',...}, ...],
          'raw': str|None,
          'intent_phrases': list[str],
        }
    """
    phrases = _intent_phrases(element_data or {})
    config = await _load_ai_config_async()
    if not config or not config.get('api_key'):
        logger.warning('AI healer skipped: no AI model config')
        return {
            'failure_reason': '未配置 AI 模型，无法自愈（请在「配置中心 → 模型配置」启用 Browser Use 文本模型）',
            'locators': [],
            'raw': None,
            'intent_phrases': phrases,
        }

    dom_candidates = await extract_dom_candidates(page)
    page_url = ''
    try:
        page_url = page.url if page else ''
    except Exception:  # noqa: BLE001
        page_url = ''

    # 步骤有明确语义，但当前页完全看不到 → 禁止臆想自愈
    if phrases and not dom_matches_intent(dom_candidates, phrases):
        reason = (
            f'页面上找不到步骤目标「{" / ".join(phrases)}」，拒绝自愈（该失败）'
        )
        logger.info('AI healer refuse: intent not on page | %s', reason)
        return {
            'failure_reason': reason,
            'locators': [],
            'raw': None,
            'intent_phrases': phrases,
        }

    prompt = _build_prompt(
        element_data, failed_candidates, dom_candidates, page_url, last_error or '', phrases,
    )
    messages = [
        {
            'role': 'system',
            'content': (
                '你是资深测试自动化工程师。只根据步骤说明与 DOM 修复定位器；'
                '找不到步骤目标时 locators 必须为 []。只输出 JSON。'
            ),
        },
        {'role': 'user', 'content': prompt},
    ]

    import asyncio

    try:
        content = await asyncio.to_thread(_chat_completions, config, messages, 60)
    except Exception as exc:  # noqa: BLE001
        logger.warning('AI healer LLM call failed: %s', exc)
        return {
            'failure_reason': f'AI 分析调用失败: {exc}',
            'locators': [],
            'raw': None,
            'intent_phrases': phrases,
        }

    parsed = _parse_heal_response(content)
    parsed['locators'] = filter_heal_suggestions(parsed.get('locators') or [], phrases=phrases)
    parsed['raw'] = content
    parsed['intent_phrases'] = phrases
    if phrases and not parsed['locators']:
        base = (parsed.get('failure_reason') or '').rstrip('；; ')
        parsed['failure_reason'] = f'{base}；建议定位器均因过宽或偏离步骤语义被拒绝' if base else (
            '建议定位器均因过宽或偏离步骤语义被拒绝'
        )
    logger.info(
        'AI healer suggestions for "%s": %s locators, reason=%s',
        element_data.get('name'),
        len(parsed.get('locators') or []),
        (parsed.get('failure_reason') or '')[:120],
    )
    return parsed


if __name__ == '__main__':
    # ponytail: 自愈约束自检
    assert _intent_phrases({'step_description': '点击「加入购物车」链接', 'name': 'x'}) == ['加入购物车']
    assert '加入购物车' in _intent_phrases({'name': 'recorded_加入购物车'})
    assert dom_matches_intent([{'text': '加入购物车', 'class': 'add-cart'}], ['加入购物车'])
    assert not dom_matches_intent([{'text': '', 'class': 'btn'}], ['加入购物车'])
    assert is_too_generic_locator('css', 'a.btn')
    assert is_too_generic_locator('css', '.btn')
    assert not is_too_generic_locator('css', 'a.add-cart')
    assert not is_too_generic_locator('text', '加入购物车')
    filtered = filter_heal_suggestions(
        [{'strategy': 'css', 'value': 'a.btn'}, {'strategy': 'text', 'value': '加入购物车'}],
        phrases=['加入购物车'],
    )
    assert len(filtered) == 1 and filtered[0]['value'] == '加入购物车'
    print('ai_locator_healer selfcheck ok')
