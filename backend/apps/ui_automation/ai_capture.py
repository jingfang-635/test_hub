"""
「用例详情 - AI生成步骤」执行过程中的元素采集（截图 + 多策略备用选择器）。

与手动录制（codegen_launcher._install_element_capture）产物格式保持一致：
每个真实交互元素采集 {locators: [{strategy, value}...], screenshot_b64, tag, ...}，
写入 sidecar JSON：media/ui-automation/ai-captures/{execution_id}.captures.json，
供 sync_ai_execution_to_cases 解析步骤时匹配消费并写入 Element。

browser-use 与 Playwright Recorder 不同，没有可注入的录制钩子，因此：
  - 挂在 ai_base.on_step_end 上，对每个真实交互动作（click/input/select/hover）
    通过 browser_session.get_element_by_index 取回 DOM 节点；
  - 由节点属性构建多策略定位器（规则对齐 codegen_launcher._CAPTURE_INIT_JS）；
  - 用 Page.get_element(backend_node_id).screenshot() 截取控件图；
  - 结果暂存内存并即时落盘，执行结束后按主定位器/交互元素匹配消费。
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from django.conf import settings

logger = logging.getLogger('django')

# 需要采集的「真实交互」动作名（兼容 browser-use 新旧版本命名）
TARGET_ACTIONS = (
    'click_element', 'click',
    'input_text', 'input', 'fill',
    'select_option', 'select', 'select_dropdown', 'select_dropdown_option',
    'hover_element', 'hover',
)

MAX_CAPTURES = 300

# 过滤常见动态/哈希 class（与 codegen_launcher._CAPTURE_INIT_JS 同规则）
_DYNAMIC_CLASS_RES = (
    re.compile(r'^[a-f0-9]{8,}$', re.I),
    re.compile(r'[_-][a-f0-9]{5,}$', re.I),
)


def ai_capture_root() -> Path:
    root = Path(settings.MEDIA_ROOT) / 'ui-automation' / 'ai-captures'
    root.mkdir(parents=True, exist_ok=True)
    return root


def _css_escape(s: Any) -> str:
    text = str(s or '')
    if re.fullmatch(r'-?[A-Za-z_][\w\u4e00-\u9fff\-]*', text):
        return text
    return re.sub(r'([^\w\u4e00-\u9fff\-])', r'\\\1', text)


def _build_locators_from_dom(el: Any) -> list[dict[str, str]]:
    """由 browser-use DOM 节点（EnhancedDOMTreeNode / DOMInteractedElement）构建多策略定位器。

    规则对齐 codegen_launcher._CAPTURE_INIT_JS 的 buildLocators：
    策略可重复；同一策略下同一表达式不重复。兼容对象与 dict 两种形态。
    """
    out: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    def push(strategy: str, value: Any) -> None:
        value = str(value or '').strip()
        if not value:
            return
        value = value[:500]
        key = (strategy, value)
        if key in seen:
            return
        seen.add(key)
        out.append({'strategy': strategy, 'value': value})

    def q(s: Any) -> str:
        return str(s or '').replace('"', '\\"')

    if isinstance(el, dict):
        attrs = el.get('attributes') or {}
        tag = (el.get('node_name') or '').lower()
        ax_name = el.get('ax_name') or ''
        xpath = el.get('x_path') or ''
    else:
        attrs = getattr(el, 'attributes', None) or {}
        tag = (getattr(el, 'node_name', '') or '').lower()
        ax_name = getattr(el, 'ax_name', None) or ''
        xpath = (getattr(el, 'x_path', '') or '').strip()
    if not isinstance(attrs, dict):
        attrs = {}
    attrs = {str(k): str(v) for k, v in attrs.items()}

    el_id = attrs.get('id')
    if el_id:
        push('id', el_id)
        push('css', '#' + _css_escape(el_id))
        push('css', f'{tag}#{_css_escape(el_id)}')
        push('xpath', f'//*[@id="{q(el_id)}"]')

    name_attr = attrs.get('name')
    if name_attr:
        push('name', name_attr)
        push('css', f'{tag}[name="{q(name_attr)}"]')
        push('xpath', f'//{tag}[@name="{q(name_attr)}"]')

    class_raw = attrs.get('class') or ''
    classes = [
        c for c in class_raw.strip().split()
        if c and len(c) <= 48 and ':' not in c
        and not any(rx.search(c) for rx in _DYNAMIC_CLASS_RES)
    ]
    if classes:
        push('class', ' '.join(classes))
        push('css', '.' + '.'.join(_css_escape(c) for c in classes))
        push('css', f'{tag}.' + '.'.join(_css_escape(c) for c in classes))

    placeholder = attrs.get('placeholder')
    if placeholder:
        push('placeholder', placeholder)
        push('css', f'{tag}[placeholder="{q(placeholder)}"]')

    title = attrs.get('title')
    if title:
        push('title', title)
        push('css', f'{tag}[title="{q(title)}"]')

    testid = attrs.get('data-testid') or attrs.get('data-test') or attrs.get('data-cy')
    if testid:
        push('test-id', testid)
        push('css', f'[data-testid="{q(testid)}"]')

    aria_label = attrs.get('aria-label')
    if aria_label:
        push('label', aria_label)

    role = attrs.get('role') or {
        'button': 'button', 'a': 'link',
        'input': ('checkbox' if attrs.get('type') == 'checkbox'
                  else 'radio' if attrs.get('type') == 'radio' else 'textbox'),
        'select': 'combobox', 'textarea': 'textbox',
    }.get(tag)
    accessible = (aria_label or placeholder or ax_name or attrs.get('value') or '').strip()[:40]
    if role and accessible:
        push('role', f'{role}[name="{q(accessible)}"]')
    elif role:
        push('role', role)

    text = (ax_name or '').strip()[:60]
    if text and len(text) <= 40 and tag not in ('input', 'textarea', 'select'):
        push('text', text)
        push('xpath', f'//{tag}[normalize-space()="{q(text)}"]')

    if xpath:
        push('xpath', xpath if xpath.startswith('/') else f'/{xpath}')

    return out


async def _capture_screenshot(session: Any, el: Any) -> str:
    """按 DOM 节点截取控件图：Page.get_element(backend_node_id).screenshot()。

    截不到（跨 frame / 已离开视口等）返回空串，不阻塞执行。
    """
    backend_node_id = _el_backend_id(el)
    if backend_node_id is None:
        return ''
    try:
        page = await session.get_current_page()
        if page is None:
            return ''
        el_actor = await asyncio.wait_for(page.get_element(backend_node_id), timeout=5)
        shot = await asyncio.wait_for(el_actor.screenshot(format='png'), timeout=5)
        return str(shot or '')
    except Exception as exc:  # noqa: BLE001
        logger.debug(f'[ai_capture] element screenshot failed: {exc}')
        return ''


def _action_dict_of(a: Any) -> dict[str, Any]:
    """把 browser-use 动作对象转为 dict（ActionModel → model_dump，兼容 _action_dict）。"""
    if hasattr(a, 'model_dump'):
        try:
            dump = a.model_dump(exclude_none=True, mode='json')
            if isinstance(dump, dict):
                return dump
        except Exception:  # noqa: BLE001
            pass
    adict = getattr(a, '_action_dict', None)
    return adict if isinstance(adict, dict) else {}


def _el_xpath(el: Any) -> str:
    if el is None:
        return ''
    if isinstance(el, dict):
        return str(el.get('x_path') or '')
    return str(getattr(el, 'x_path', '') or '')


def _el_tag(el: Any) -> str:
    if el is None:
        return ''
    if isinstance(el, dict):
        return str(el.get('node_name') or '').lower()
    return str(getattr(el, 'node_name', '') or '').lower()


def _el_backend_id(el: Any) -> Any:
    if el is None:
        return None
    if isinstance(el, dict):
        return el.get('backend_node_id')
    return getattr(el, 'backend_node_id', None)


class AiElementCaptureRecorder:
    """AI 执行期间的元素采集器：内存为主 + 即时落盘 sidecar。"""

    def __init__(self, execution_id: Any, max_captures: int = MAX_CAPTURES):
        self.execution_id = execution_id
        self.max_captures = max_captures
        self.captures: list[dict[str, Any]] = []
        self._keys: set[str] = set()

    @property
    def path(self) -> Path:
        return ai_capture_root() / f'{self.execution_id}.captures.json'

    def reset(self) -> None:
        self.captures = []
        self._keys = set()
        try:
            self.path.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def _key_of(locators: Any) -> str:
        return '|'.join(
            f"{l.get('strategy')}={l.get('value')}" for l in (locators or [])
        )

    async def record(
        self,
        agent_instance: Any,
        actions: Any,
        interacted_elements: Any = None,
    ) -> int:
        """对一个 step 的真实交互动作采集定位器 + 控件截图。

        interacted_elements: browser-use state.interacted_element（DOMInteractedElement 列表，
        与 actions 一一对应，动作执行时刻的精确节点）；为空时回退 get_element_by_index。
        """
        if not actions or len(self.captures) >= self.max_captures:
            return 0
        session = getattr(agent_instance, 'browser_session', None)
        if session is None:
            return 0

        interacted = list(interacted_elements or [])
        added = 0
        for pos, a in enumerate(actions or []):
            if len(self.captures) >= self.max_captures:
                break
            adict = _action_dict_of(a)
            if not adict:
                continue
            params: dict[str, Any] | None = None
            for k, v in adict.items():
                if k not in TARGET_ACTIONS:
                    continue
                if isinstance(v, dict):
                    params = v
                elif isinstance(v, int):
                    params = {'index': v}
                else:
                    continue
                if not isinstance(params.get('index'), int):
                    params = None
                    continue
                break
            if params is None:
                continue

            el = interacted[pos] if pos < len(interacted) else None
            if el is None:
                index = params.get('index')
                try:
                    el = await asyncio.wait_for(session.get_element_by_index(index), timeout=5)
                except Exception as exc:  # noqa: BLE001
                    logger.debug(f'[ai_capture] get_element_by_index({index}) failed: {exc}')
                    continue
            if el is None:
                continue

            locators = _build_locators_from_dom(el)
            if not locators:
                continue

            shot = await _capture_screenshot(session, el)
            key = self._key_of(locators)
            if key in self._keys:
                # 同一元素重复交互：补截图后去重
                for prev in self.captures:
                    if self._key_of(prev.get('locators')) == key and shot and not prev.get('screenshot_b64'):
                        prev['screenshot_b64'] = shot
                        self.flush()
                        break
                continue

            self._keys.add(key)
            self.captures.append({
                'ts': time.time(),
                'tag': _el_tag(el),
                'locators': locators,
                'screenshot_b64': shot,
                'x_path': _el_xpath(el),
                'backend_node_id': _el_backend_id(el),
            })
            added += 1
            logger.info(
                f"[ai_capture] #{len(self.captures)} tag={self.captures[-1]['tag']} "
                f"locators={len(locators)} shot={bool(shot)}"
            )

        if added:
            self.flush()
        return added

    def flush(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(self.captures, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f'[ai_capture] flush failed: {exc}')


def load_ai_captures(execution_id: Any) -> list[dict[str, Any]]:
    """读取执行期采集 sidecar：media/.../ai-captures/{execution_id}.captures.json。"""
    path = ai_capture_root() / f'{execution_id}.captures.json'
    try:
        if not path.is_file():
            return []
        data = json.loads(path.read_text(encoding='utf-8'))
        return data if isinstance(data, list) else []
    except Exception as exc:  # noqa: BLE001
        logger.warning('load_ai_captures(%s) failed: %s', execution_id, exc)
        return []


def _take_ai_capture(
    captures: list[dict[str, Any]],
    used: set[int],
    *,
    primary_strategy: str,
    primary_value: str,
    sequential_idx: int,
    el: Any = None,
) -> dict[str, Any] | None:
    """为步骤挑选采集结果：交互元素精确匹配 → 主定位器精确命中 → 启发式顺序匹配。

    前两级允许复用已消费的 capture（同一元素多次交互只采集一份）。
    """
    from .codegen_pipeline_service import (
        _capture_match_score,
        _is_junk_capture,
        _take_best_capture,
    )

    if not captures:
        return None

    # 1) 按 browser-use 交互元素的 x_path 精确匹配（最可靠）
    el_xpath = _el_xpath(el)
    if el_xpath:
        for i, cap in enumerate(captures):
            if (cap.get('x_path') or '') == el_xpath and not _is_junk_capture(cap):
                used.add(i)
                return cap

    # 2) 主定位器精确命中（score>=100 为完全一致）；允许复用同元素已用 capture
    if (primary_value or '').strip():
        best_i, best_score = -1, 0
        for i, cap in enumerate(captures):
            if _is_junk_capture(cap):
                continue
            score = _capture_match_score(cap, primary_strategy, primary_value)
            if score > best_score:
                best_score, best_i = score, i
        if best_i >= 0 and best_score >= 100:
            used.add(best_i)
            return captures[best_i]

    # 3) 与手动录制一致的启发式匹配（只取未使用的 capture）
    return _take_best_capture(
        captures, used,
        primary_strategy=primary_strategy,
        primary_value=primary_value,
        sequential_idx=sequential_idx,
    )


if __name__ == '__main__':
    # ponytail: 采集/匹配自检，改规则时应先挂这里
    # 直接脚本运行时无包上下文：注册伪包名，使 `from .codegen_pipeline_service import` 可解析
    import importlib.util
    import os
    import sys
    import types

    _here = os.path.dirname(os.path.abspath(__file__))
    _pkg = types.ModuleType('apps.ui_automation')
    _pkg.__path__ = [_here]
    sys.modules['apps.ui_automation'] = _pkg

    def _load_as(fullname: str, filename: str):
        spec = importlib.util.spec_from_file_location(fullname, filename)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[fullname] = mod
        spec.loader.exec_module(mod)
        return mod

    _cps = _load_as(
        'apps.ui_automation.codegen_pipeline_service',
        os.path.join(_here, 'codegen_pipeline_service.py'),
    )
    _mod = _load_as('apps.ui_automation.ai_capture', os.path.join(_here, 'ai_capture.py'))
    _build_locators_from_dom = _mod._build_locators_from_dom
    _take_ai_capture = _mod._take_ai_capture

    class _FakeEl:
        node_name = 'BUTTON'
        attributes = {'id': 'login-btn', 'class': 'btn primary', 'name': 'login'}
        x_path = '/html/body/div[1]/button'
        ax_name = '登录'
        backend_node_id = 42

    _locs = _build_locators_from_dom(_FakeEl())
    strategies = {l['strategy'] for l in _locs if (_locs := _locs)}
    # 策略可重复、同策略同表达式去重
    _pairs = [(l['strategy'], l['value']) for l in _locs]
    assert len(_pairs) == len(set(_pairs)), _pairs
    _strategies = {s for s, _ in _pairs}
    assert {'id', 'name', 'class', 'role', 'text', 'xpath', 'css'} <= _strategies, _strategies
    assert ('id', 'login-btn') == next((s, v) for s, v in _pairs if s == 'id')

    # 同一元素重复交互 → 去重并保留一份
    _caps = [{'locators': _locs, 'screenshot_b64': '', 'x_path': _FakeEl.x_path}]
    _used: set[int] = set()
    _first = _take_ai_capture(_caps, _used, primary_strategy='id', primary_value='login-btn', sequential_idx=0, el=_FakeEl())
    assert _first is _caps[0]
    # 已消费但 x_path 精确匹配 → 复用（同元素二次交互场景）
    _again = _take_ai_capture(_caps, _used, primary_strategy='id', primary_value='login-btn', sequential_idx=0, el=_FakeEl())
    assert _again is _caps[0]
    print('ai_capture selfcheck ok')