# -*- coding: utf-8 -*-
"""
AI 定位器自愈：主/备用定位器均失效时，分析页面并临时推荐定位器。
仅用于当次执行，不写回元素库或测试步骤。
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
) -> str:
    element_name = element_data.get('name') or '未知元素'
    element_desc = element_data.get('description') or ''
    element_type = element_data.get('element_type') or ''
    tried = [
        {'strategy': c.get('strategy'), 'value': c.get('value')}
        for c in (failed_candidates or [])
    ]
    return (
        '你是 UI 自动化定位器修复专家。主选择器和备用选择器均已失效，请分析原因并给出临时可用的新定位器。\n'
        '要求：\n'
        '1. 只根据当前页面 DOM 候选与元素语义推断，不要臆造不存在的属性。\n'
        '2. strategy 仅允许：css, xpath, id, name, text, role, placeholder, label, test-id, title, class。\n'
        '3. 优先稳定属性（data-testid / id / name / 语义文本），避免过长动态 class。\n'
        '4. 给出 1~5 个按置信度排序的定位器建议。\n'
        '5. failure_reason 用中文简要说明原定位器失效原因。\n'
        '6. 严格返回 JSON，不要其它说明文字，格式：\n'
        '{"failure_reason":"...","locators":[{"strategy":"css","value":"...","confidence":0.9,"note":"..."}]}\n\n'
        f'当前页面 URL: {page_url}\n'
        f'目标元素名称: {element_name}\n'
        f'目标元素描述: {element_desc}\n'
        f'目标元素类型: {element_type}\n'
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
        }
    """
    config = await _load_ai_config_async()
    if not config or not config.get('api_key'):
        logger.warning('AI healer skipped: no AI model config')
        return {
            'failure_reason': '未配置 AI 模型，无法自愈（请在「配置中心 → AI智能模式配置」启用 Browser Use 文本模型）',
            'locators': [],
            'raw': None,
        }

    dom_candidates = await extract_dom_candidates(page)
    page_url = ''
    try:
        page_url = page.url if page else ''
    except Exception:  # noqa: BLE001
        page_url = ''

    prompt = _build_prompt(element_data, failed_candidates, dom_candidates, page_url, last_error or '')
    messages = [
        {
            'role': 'system',
            'content': '你是资深测试自动化工程师，擅长根据 DOM 修复失效的 Playwright 定位器。只输出 JSON。',
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
        }

    parsed = _parse_heal_response(content)
    parsed['raw'] = content
    logger.info(
        'AI healer suggestions for "%s": %s locators, reason=%s',
        element_data.get('name'),
        len(parsed.get('locators') or []),
        (parsed.get('failure_reason') or '')[:120],
    )
    return parsed
