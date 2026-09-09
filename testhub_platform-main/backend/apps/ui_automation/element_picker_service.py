"""测试步骤「拾取」：无头浏览器投屏 + 检查元素（只读点选，不触发导航）。"""
from __future__ import annotations

import asyncio
import base64
import logging
import os
import threading
import time
import uuid
from typing import Any

logger = logging.getLogger(__name__)

# 使用默认浏览器路径（用户目录下 ms-playwright）
# 如需自定义路径，设置环境变量 PLAYWRIGHT_BROWSERS_PATH

# 用户维度单会话
_SESSIONS: dict[str, 'ElementPickerSession'] = {}
_LOCK = threading.Lock()

# 在页面内根据坐标解析元素并生成定位器 + 匹配数（不触发真实点击）
_INSPECT_JS = r"""
(coords) => {
  const x = coords.x, y = coords.y;
  const el0 = document.elementFromPoint(x, y);
  if (!el0) return null;
  let el = el0.nodeType === 3 ? el0.parentElement : el0;
  if (!el || el.nodeType !== 1) return null;

  const cssEscape = (s) => {
    if (window.CSS && CSS.escape) return CSS.escape(s);
    return String(s).replace(/[^a-zA-Z0-9_-]/g, (c) => '\\' + c);
  };

  function getCssPath(node, { stopAtId } = { stopAtId: true }) {
    const parts = [];
    let cur = node;
    while (cur && cur.nodeType === 1 && cur !== document.documentElement) {
      if (stopAtId && cur.id) {
        parts.unshift('#' + cssEscape(cur.id));
        break;
      }
      let part = cur.tagName.toLowerCase();
      const parent = cur.parentElement;
      if (parent) {
        const same = Array.from(parent.children).filter(c => c.tagName === cur.tagName);
        if (same.length > 1) {
          part += ':nth-of-type(' + (same.indexOf(cur) + 1) + ')';
        }
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
      while (sib) {
        if (sib.tagName === cur.tagName) ix++;
        sib = sib.previousElementSibling;
      }
      parts.unshift(cur.tagName.toLowerCase() + '[' + ix + ']');
      cur = cur.parentElement;
    }
    return '/' + parts.join('/');
  }

  function buildLocators(node) {
    const out = [];
    const push = (strategy, value) => {
      if (!value || !String(value).trim()) return;
      const v = String(value).trim().slice(0, 500);
      if (out.some(x => x.strategy === strategy && x.value === v)) return;
      out.push({ strategy, value: v });
    };
    const q = (s) => String(s).replace(/"/g, '\\"');
    const tag = (node.tagName || '').toLowerCase();

    if (node.id) {
      push('id', node.id);
      push('css', '#' + cssEscape(node.id));
      push('css', tag + '#' + cssEscape(node.id));
      push('xpath', '//*[@id="' + q(node.id) + '"]');
    }
    const nameAttr = node.getAttribute('name');
    if (nameAttr) {
      push('name', nameAttr);
      push('css', tag + '[name="' + q(nameAttr) + '"]');
      push('xpath', '//' + tag + '[@name="' + q(nameAttr) + '"]');
    }
    const classRaw = (typeof node.className === 'string' ? node.className : '') || '';
    const classes = classRaw.trim().split(/\s+/).filter((c) => {
      if (!c || c.length > 48 || c.includes(':')) return false;
      if (/^[a-f0-9]{8,}$/i.test(c)) return false;
      if (/[_-][a-f0-9]{5,}$/i.test(c)) return false;
      return true;
    });
    if (classes.length) {
      push('class', classes.join(' '));
      push('css', '.' + classes.map(cssEscape).join('.'));
      push('css', tag + '.' + classes.map(cssEscape).join('.'));
    }
    if (node.getAttribute('placeholder')) {
      const ph = node.getAttribute('placeholder');
      push('placeholder', ph);
      push('css', tag + '[placeholder="' + q(ph) + '"]');
    }
    if (node.getAttribute('title')) {
      const title = node.getAttribute('title');
      push('title', title);
      push('css', tag + '[title="' + q(title) + '"]');
    }
    if (node.getAttribute('data-testid')) {
      const tid = node.getAttribute('data-testid');
      push('test-id', tid);
      push('css', '[data-testid="' + q(tid) + '"]');
    }
    if (node.getAttribute('aria-label')) {
      push('label', node.getAttribute('aria-label'));
    }
    if (node.id) {
      const lab = document.querySelector('label[for="' + cssEscape(node.id) + '"]');
      if (lab && lab.textContent) push('label', lab.textContent.trim().slice(0, 80));
    }
    // 邻近 label（Element UI 等无 for 关联时）
    try {
      const wrap = node.closest('.el-form-item, .el-input, .form-item, label');
      if (wrap) {
        const labEl = wrap.querySelector('.el-form-item__label, label, .label');
        const t = (labEl && labEl.textContent || '').trim().slice(0, 80);
        if (t) push('label', t);
      }
    } catch (e) {}

    const role = node.getAttribute('role') || ({
      button: 'button', a: 'link',
      input: (node.type === 'checkbox' ? 'checkbox' : node.type === 'radio' ? 'radio' : 'textbox'),
      select: 'combobox', textarea: 'textbox',
    })[tag];
    const accessibleName = (node.getAttribute('aria-label')
      || node.getAttribute('placeholder')
      || (node.innerText || '').trim().slice(0, 40)
      || node.getAttribute('value') || '').trim();
    if (role && accessibleName) {
      push('role', role + '[name="' + q(accessibleName) + '"]');
    } else if (role) {
      push('role', role);
    }

    const text = (node.innerText || node.textContent || '').trim().slice(0, 60);
    if (text && text.length <= 40 && !/^(input|textarea|select)$/i.test(tag)) {
      push('text', text);
      push('xpath', '//' + tag + '[normalize-space()="' + q(text) + '"]');
    }

    push('css', getCssPath(node, { stopAtId: true }));
    push('css', getCssPath(node, { stopAtId: false }));
    push('xpath', getXPath(node, { preferId: true }));
    push('xpath', getXPath(node, { preferId: false }));
    return out;
  }

  function countMatches(strategy, value) {
    try {
      const s = (strategy || '').toLowerCase();
      if (s === 'css') return document.querySelectorAll(value).length;
      if (s === 'id') {
        const sel = value.startsWith('#') ? value : ('#' + cssEscape(value));
        return document.querySelectorAll(sel).length;
      }
      if (s === 'xpath') {
        const r = document.evaluate(value, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
        return r.snapshotLength;
      }
      if (s === 'name') return document.querySelectorAll('[name="' + value.replace(/"/g, '\\"') + '"]').length;
      if (s === 'class') {
        const sel = '.' + String(value).trim().split(/\s+/).map(cssEscape).join('.');
        return document.querySelectorAll(sel).length;
      }
      if (s === 'placeholder') {
        return document.querySelectorAll('[placeholder="' + value.replace(/"/g, '\\"') + '"]').length;
      }
      if (s === 'title') {
        return document.querySelectorAll('[title="' + value.replace(/"/g, '\\"') + '"]').length;
      }
      if (s === 'test-id') {
        return document.querySelectorAll('[data-testid="' + value.replace(/"/g, '\\"') + '"]').length;
      }
      if (s === 'label') {
        const v = value.replace(/"/g, '\\"');
        let n = document.querySelectorAll('[aria-label="' + v + '"]').length;
        const labs = Array.from(document.querySelectorAll('label'));
        for (const lab of labs) {
          if ((lab.textContent || '').trim() === value) {
            if (lab.htmlFor) {
              const t = document.getElementById(lab.htmlFor);
              if (t) n++;
            } else {
              const t = lab.querySelector('input,textarea,select');
              if (t) n++;
            }
          }
        }
        return n;
      }
      if (s === 'text') {
        const all = Array.from(document.querySelectorAll('button,a,span,div,li,p,h1,h2,h3,h4,h5,h6,label'));
        return all.filter(e => (e.innerText || '').trim() === value).length;
      }
      if (s === 'role') {
        const m = value.match(/^(\w+)(?:\[name="([\s\S]*)"\])?$/);
        if (!m) return 0;
        const role = m[1], name = m[2];
        const nodes = Array.from(document.querySelectorAll('[role="' + role + '"],' + (
          role === 'button' ? 'button' : role === 'link' ? 'a' : role === 'textbox' ? 'input,textarea' : ''
        )));
        if (!name) return nodes.length;
        return nodes.filter(e => {
          const n = (e.getAttribute('aria-label') || e.getAttribute('placeholder')
            || (e.innerText || '').trim() || e.getAttribute('value') || '').trim();
          return n === name;
        }).length;
      }
    } catch (e) { return -1; }
    return -1;
  }

  const STRATEGY_PRIORITY = [
    'placeholder', 'label', 'test-id', 'id', 'role', 'name', 'text', 'title', 'class', 'css', 'xpath'
  ];
  const locators = buildLocators(el).map(l => {
    const match_count = countMatches(l.strategy, l.value);
    return {
      strategy: l.strategy,
      value: l.value,
      match_count,
      unique: match_count === 1,
    };
  });
  // 唯一匹配优先展示；同组内按语义策略优先于 css/xpath
  locators.sort((a, b) => {
    if (a.unique !== b.unique) return a.unique ? -1 : 1;
    const ra = STRATEGY_PRIORITY.indexOf(String(a.strategy).toLowerCase());
    const rb = STRATEGY_PRIORITY.indexOf(String(b.strategy).toLowerCase());
    return (ra < 0 ? 99 : ra) - (rb < 0 ? 99 : rb);
  });

  const rect = el.getBoundingClientRect();
  const classRaw = (typeof el.className === 'string' ? el.className : '') || '';
  return {
    tag: (el.tagName || '').toLowerCase(),
    class_name: classRaw.trim().split(/\s+/).filter(Boolean)[0] || '',
    locators,
    rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height },
    viewport: { w: window.innerWidth, h: window.innerHeight },
  };
}
"""


def _channel_layer():
    try:
        from channels_redis.core import RedisChannelLayer
        from django.conf import settings

        hosts = settings.CHANNEL_LAYERS['default']['CONFIG'].get(
            'hosts', ['redis://127.0.0.1:6379/0']
        )
        return RedisChannelLayer(hosts=hosts)
    except Exception as exc:  # noqa: BLE001
        logger.warning('element_picker channel layer failed: %s', exc)
        return None


def _normalize_strategy(name: str) -> str:
    """对齐库内 LocatorStrategy.name 大小写。"""
    key = (name or '').strip().lower()
    mapping = {
        'id': 'ID',
        'css': 'CSS',
        'xpath': 'XPath',
        'test-id': 'test-id',
        'testid': 'test-id',
    }
    return mapping.get(key, key if key in ('name', 'class', 'tag', 'text', 'placeholder', 'role', 'label', 'title', 'test-id') else name)


def _tag_to_element_type(tag: str) -> str:
    t = (tag or '').lower()
    return {
        'button': 'BUTTON',
        'a': 'LINK',
        'input': 'INPUT',
        'textarea': 'INPUT',
        'select': 'DROPDOWN',
        'img': 'IMAGE',
        'table': 'TABLE',
        'form': 'FORM',
        'span': 'TEXT',
        'p': 'TEXT',
        'label': 'TEXT',
        'h1': 'TEXT',
        'h2': 'TEXT',
        'h3': 'TEXT',
        'li': 'TEXT',
        'div': 'CONTAINER',
    }.get(t, 'BUTTON')


def _suggest_element_name(tag: str, locators: list[dict[str, Any]], fallback: str) -> str:
    kind = {
        'button': '按钮',
        'a': '链接',
        'input': '输入框',
        'textarea': '输入框',
        'select': '下拉框',
        'img': '图片',
        'span': '文本',
        'label': '文本',
        'p': '文本',
        'div': '容器',
    }.get((tag or '').lower(), '元素')
    prefer = ('label', 'placeholder', 'text', 'title', 'name', 'test-id', 'id')
    by_s = {(loc.get('strategy') or '').lower(): (loc.get('value') or '').strip() for loc in (locators or [])}
    label = ''
    for key in prefer:
        if by_s.get(key):
            label = by_s[key][:40]
            break
    if not label:
        label = (fallback or tag or '元素')[:40]
    name = f'{label}{kind}' if label and not label.endswith(kind) else (label or kind)
    return name[:200]


class ElementPickerSession:
    def __init__(self, session_id: str, user_id: int, project_id: int, start_url: str):
        self.session_id = session_id
        self.user_id = user_id
        self.project_id = project_id
        self.start_url = start_url
        self.status = 'starting'
        self.error = ''
        self.page_url = ''
        self._stop = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._pw = None
        self._browser = None
        self._context = None
        self._page = None
        self._ready = threading.Event()
        self._wake: asyncio.Event | None = None
        self._channel = None
        self._last_image = ''
        self._last_inspect: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            'session_id': self.session_id,
            'project_id': self.project_id,
            'status': self.status,
            'error': self.error,
            'page_url': self.page_url,
            'start_url': self.start_url,
        }

    def start_background(self, storage_state: str | None) -> None:
        self._thread = threading.Thread(
            target=self._thread_main,
            args=(storage_state,),
            name=f'element-picker-{self.session_id[:8]}',
            daemon=True,
        )
        self._thread.start()

    def _thread_main(self, storage_state: str | None) -> None:
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._run(storage_state))
        except Exception as exc:  # noqa: BLE001
            self.status = 'error'
            self.error = str(exc)
            logger.exception('element_picker session failed: %s', exc)
        finally:
            self._ready.set()
            try:
                if self._loop and not self._loop.is_closed():
                    self._loop.close()
            except Exception:  # noqa: BLE001
                pass

    async def _run(self, storage_state: str | None) -> None:
        from playwright.async_api import async_playwright

        t0 = time.monotonic()
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--ignore-certificate-errors',
                '--disable-web-security',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-gpu',
            ],
        )
        ctx_kwargs: dict[str, Any] = {
            # 略高于面板宽度，缩放时更清晰
            'viewport': {'width': 1440, 'height': 900},
            'device_scale_factor': 1,
        }
        if storage_state:
            ctx_kwargs['storage_state'] = storage_state
        self._context = await self._browser.new_context(**ctx_kwargs)
        self._page = await self._context.new_page()
        # 投屏目标 ~10s：domcontentloaded 即可，不 tip networkidle
        try:
            await self._page.goto(self.start_url, wait_until='domcontentloaded', timeout=15000)
        except Exception as exc:  # noqa: BLE001
            logger.warning('element_picker goto failed: %s', exc)
        self.page_url = self._page.url
        self._wake = asyncio.Event()
        self._channel = _channel_layer()
        # 首帧先截再 ready，避免 HTTP 已返回但 WS 尚未入组导致白屏
        try:
            await self._capture_and_push()
        except Exception as exc:  # noqa: BLE001
            logger.warning('element_picker first frame failed: %s', exc)
        self.status = 'ready'
        self._ready.set()
        logger.info(
            'element_picker ready in %.1fs session=%s url=%s',
            time.monotonic() - t0,
            self.session_id[:8],
            self.page_url,
        )
        await self._screenshot_loop()

    async def _capture_and_push(self) -> str:
        """截一帧并推 WS；返回 data-url。"""
        page = self._page
        if not page or page.is_closed():
            return self._last_image
        # quality 72：投屏够用，首帧 HTTP/WS 传输更快
        raw = await page.screenshot(type='jpeg', quality=72, full_page=False)
        img = 'data:image/jpeg;base64,' + base64.b64encode(raw).decode('ascii')
        self._last_image = img
        self.page_url = page.url
        layer = self._channel
        if layer:
            try:
                await layer.group_send(
                    f'ui_element_picker_{self.session_id}',
                    {'type': 'screenshot_update', 'image': img, 'page_url': self.page_url},
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug('element_picker push failed: %s', exc)
        return img

    def _wake_loop(self) -> None:
        if self._wake and self._loop:
            self._loop.call_soon_threadsafe(self._wake.set)

    async def _screenshot_loop(self) -> None:
        while not self._stop.is_set():
            try:
                await self._capture_and_push()
            except Exception as exc:  # noqa: BLE001
                if not self._stop.is_set():
                    logger.debug('element_picker screenshot: %s', exc)
            if self._wake:
                self._wake.clear()
                try:
                    # ~8fps；操作后 _wake 可立刻打断等待
                    await asyncio.wait_for(self._wake.wait(), timeout=0.12)
                except asyncio.TimeoutError:
                    pass
            else:
                await asyncio.sleep(0.12)
        await self._cleanup_async()

    async def _cleanup_async(self) -> None:
        for closer in (self._context, self._browser, self._pw):
            try:
                if closer:
                    await closer.close()
            except Exception:  # noqa: BLE001
                pass
        self.status = 'stopped'

    def _call(self, coro, timeout: float = 15.0):
        if not self._loop or self.status not in ('ready', 'starting'):
            raise RuntimeError('拾取会话未就绪')
        fut = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return fut.result(timeout=timeout)

    def inspect(self, x: float, y: float, img_w: float, img_h: float) -> dict[str, Any]:
        return self._call(self._inspect_async(x, y, img_w, img_h))

    def _map_point(
        self, x: float, y: float, img_w: float, img_h: float
    ) -> tuple[float, float]:
        vp = (self._page.viewport_size if self._page else None) or {'width': 1440, 'height': 900}
        sx = (x / img_w) * vp['width'] if img_w else x
        sy = (y / img_h) * vp['height'] if img_h else y
        return sx, sy

    async def _inspect_async(
        self, x: float, y: float, img_w: float, img_h: float
    ) -> dict[str, Any]:
        page = self._page
        if not page or page.is_closed():
            raise RuntimeError('页面已关闭')
        sx, sy = self._map_point(x, y, img_w, img_h)
        result = await page.evaluate(_INSPECT_JS, {'x': sx, 'y': sy})
        if not result:
            self._last_inspect = None
            return {'tag': '', 'class_name': '', 'locators': [], 'rect': None}
        for loc in result.get('locators') or []:
            loc['strategy'] = _normalize_strategy(loc.get('strategy') or '')
        # 控件截图：按高亮矩形裁切
        shot_b64 = ''
        rect = result.get('rect') or {}
        try:
            w = float(rect.get('w') or 0)
            h = float(rect.get('h') or 0)
            if w >= 1 and h >= 1:
                clip = {
                    'x': max(0.0, float(rect.get('x') or 0)),
                    'y': max(0.0, float(rect.get('y') or 0)),
                    'width': w,
                    'height': h,
                }
                raw = await page.screenshot(type='png', clip=clip)
                shot_b64 = base64.b64encode(raw).decode('ascii')
        except Exception as exc:  # noqa: BLE001
            logger.debug('element_picker clip screenshot failed: %s', exc)
        result['screenshot_b64'] = shot_b64
        self.page_url = page.url
        self._last_inspect = result
        return result

    def save_element(
        self,
        *,
        strategy: str,
        value: str,
        backup_locators: list[dict[str, Any]] | None = None,
        tag: str = '',
        user=None,
    ) -> dict[str, Any]:
        """根据当前检查结果创建/复用元素，附带控件截图（同步，供请求线程调用）。"""
        from django.contrib.auth import get_user_model
        from django.core.files.base import ContentFile
        from django.utils import timezone

        from .codegen_pipeline_service import (
            _element_screenshot_url,
            _page_name_from_url,
            _resolve_locator_strategy,
            _resolve_page_group,
        )
        from .models import Element, UiProject
        from .serializers import ElementSerializer

        strategy_name = _normalize_strategy(strategy or 'css')
        locator_value = (value or '').strip()[:500]
        if not locator_value:
            raise ValueError('缺少定位表达式')

        project = UiProject.objects.filter(pk=self.project_id).first()
        if not project:
            raise ValueError('项目不存在')

        loc_strategy = _resolve_locator_strategy(strategy_name)
        if not loc_strategy:
            raise ValueError(f'未找到定位策略: {strategy_name}')

        page_url = self.page_url or self.start_url
        page_name = _page_name_from_url(page_url)
        page_group = _resolve_page_group(project, page_name)

        inspect = self._last_inspect or {}
        tag_l = (tag or inspect.get('tag') or '').strip().lower()
        el_type = _tag_to_element_type(tag_l)
        name = _suggest_element_name(tag_l, inspect.get('locators') or [], locator_value)

        element = Element.objects.filter(
            project=project,
            locator_value=locator_value,
            locator_strategy=loc_strategy,
        ).first()
        created = False
        if not element:
            base = name
            n = 1
            while Element.objects.filter(project=project, name=name).exists():
                name = f'{base}_{n}'[:200]
                n += 1
            element = Element(
                project=project,
                name=name,
                description='拾取自动创建',
                element_type=el_type,
                locator_strategy=loc_strategy,
                locator_value=locator_value,
                page=(page_name or '')[:200],
                group=page_group,
                is_unique=True,
                validation_status='UNKNOWN',
            )
            if user is not None:
                element.created_by = user
            elif self.user_id:
                User = get_user_model()
                element.created_by = User.objects.filter(pk=self.user_id).first()
            created = True
        else:
            if page_name:
                element.page = page_name[:200]
            if page_group:
                element.group = page_group

        seen = {(strategy_name.lower(), locator_value)}
        backups: list[dict[str, str]] = []
        for b in backup_locators or []:
            bs = _normalize_strategy((b.get('strategy') or '').strip())
            bv = (b.get('value') or '').strip()[:500]
            if not bs or not bv:
                continue
            key = (bs.lower(), bv)
            if key in seen:
                continue
            seen.add(key)
            backups.append({'strategy': bs, 'value': bv})
        element.backup_locators = backups

        shot_b64 = (inspect.get('screenshot_b64') or '').strip()
        if not shot_b64:
            try:
                shot_b64 = self._call(
                    self._screenshot_by_locator(strategy_name, locator_value),
                    timeout=5,
                ) or ''
            except Exception:  # noqa: BLE001
                shot_b64 = ''
        if shot_b64:
            try:
                raw = base64.b64decode(shot_b64)
                element.screenshot.save(
                    f'element_pick_{int(timezone.now().timestamp())}.png',
                    ContentFile(raw),
                    save=False,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning('save picker element screenshot failed: %s', exc)

        element.save()

        data = ElementSerializer(element).data
        if not data.get('screenshot'):
            data['screenshot'] = _element_screenshot_url(element)
        return {'element': data, 'created': created, 'page': element.page}

    async def _screenshot_by_locator(self, strategy: str, value: str) -> str:
        page = self._page
        if not page or page.is_closed() or not value:
            return ''
        s = (strategy or '').strip().lower()
        try:
            if s == 'id':
                handle = page.locator(f'#{value}').first
            elif s == 'css':
                handle = page.locator(value).first
            elif s == 'xpath':
                handle = page.locator(f'xpath={value}').first
            elif s == 'name':
                handle = page.locator(f'[name="{value}"]').first
            elif s == 'placeholder':
                handle = page.get_by_placeholder(value).first
            elif s == 'label':
                handle = page.get_by_label(value).first
            elif s == 'text':
                handle = page.get_by_text(value, exact=True).first
            elif s == 'title':
                handle = page.get_by_title(value).first
            elif s == 'test-id':
                handle = page.get_by_test_id(value).first
            elif s == 'role':
                import re
                m = re.match(r'^(\w+)(?:\[name="([\s\S]*)"\])?$', value)
                if not m:
                    return ''
                role, accessible = m.group(1), m.group(2)
                kwargs = {'name': accessible} if accessible else {}
                handle = page.get_by_role(role, **kwargs).first
            elif s == 'class':
                sel = '.' + '.'.join(str(value).strip().split())
                handle = page.locator(sel).first
            else:
                return ''
            raw = await handle.screenshot(timeout=2000)
            return base64.b64encode(raw).decode('ascii')
        except Exception as exc:  # noqa: BLE001
            logger.debug('element_picker locator screenshot failed: %s', exc)
            return ''

    def click(
        self,
        x: float,
        y: float,
        img_w: float,
        img_h: float,
        button: str = 'left',
        click_count: int = 1,
    ) -> str:
        return self._call(self._click_async(x, y, img_w, img_h, button, click_count), timeout=10)

    async def _click_async(
        self,
        x: float,
        y: float,
        img_w: float,
        img_h: float,
        button: str,
        click_count: int,
    ) -> str:
        page = self._page
        if not page or page.is_closed():
            raise RuntimeError('页面已关闭')
        sx, sy = self._map_point(x, y, img_w, img_h)
        btn = button if button in ('left', 'right', 'middle') else 'left'
        await page.mouse.click(sx, sy, button=btn, click_count=max(1, int(click_count or 1)))
        await asyncio.sleep(0.05)  # 等页面开始响应再截
        img = await self._capture_and_push()
        self._wake_loop()
        return img

    def type_text(self, text: str) -> str:
        return self._call(self._type_async(text), timeout=10)

    async def _type_async(self, text: str) -> str:
        page = self._page
        if not page or page.is_closed():
            raise RuntimeError('页面已关闭')
        await page.keyboard.type(text or '', delay=0)
        img = await self._capture_and_push()
        self._wake_loop()
        return img

    def press(self, key: str) -> str:
        return self._call(self._press_async(key), timeout=5)

    async def _press_async(self, key: str) -> str:
        page = self._page
        if not page or page.is_closed():
            raise RuntimeError('页面已关闭')
        await page.keyboard.press(key)
        img = await self._capture_and_push()
        self._wake_loop()
        return img

    def scroll(self, delta_y: float) -> str:
        return self._call(self._scroll_async(delta_y), timeout=5)

    async def _scroll_async(self, delta_y: float) -> str:
        if self._page and not self._page.is_closed():
            await self._page.mouse.wheel(0, delta_y)
            img = await self._capture_and_push()
            self._wake_loop()
            return img
        return self._last_image

    def navigate(self, url: str) -> dict[str, str]:
        return self._call(self._navigate_async(url), timeout=60)

    async def _navigate_async(self, url: str) -> dict[str, str]:
        if not self._page or self._page.is_closed():
            raise RuntimeError('页面已关闭')
        await self._page.goto(url, wait_until='domcontentloaded', timeout=60000)
        self.page_url = self._page.url
        img = await self._capture_and_push()
        self._wake_loop()
        return {'page_url': self.page_url, 'image': img}

    def stop(self) -> None:
        self._stop.set()
        self._wake_loop()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=8)
        self.status = 'stopped'


def _session_key(user_id: int) -> str:
    return f'user_{user_id}'


def get_session_for_user(user_id: int) -> ElementPickerSession | None:
    with _LOCK:
        return _SESSIONS.get(_session_key(user_id))


def stop_for_user(user_id: int) -> ElementPickerSession | None:
    with _LOCK:
        sess = _SESSIONS.pop(_session_key(user_id), None)
    if sess:
        sess.stop()
    return sess


def start_for_user(user_id: int, project_id: int, url: str = '') -> ElementPickerSession:
    from .auth_state import (
        auth_path_for_project,
        ensure_project_auth_state,
        load_path_if_exists,
    )
    from .codegen_service import codegen_recorder

    t0 = time.monotonic()
    stop_for_user(user_id)

    start_url = (url or '').strip() or codegen_recorder._resolve_project_base_url(project_id)
    if not start_url:
        raise ValueError('项目未配置环境 base_url，无法启动拾取')

    # 快路径：已有登录态文件直接注入，不再另起浏览器做 ensure/探测（可省 5～20s）
    auth_file = auth_path_for_project(project_id)
    storage = load_path_if_exists(auth_file)
    if not storage:
        username, password = codegen_recorder._resolve_project_login(project_id)
        try:
            ensured = ensure_project_auth_state(
                project_id,
                base_url=start_url,
                username=username,
                password=password,
            )
            storage = ensured or load_path_if_exists(auth_file)
        except Exception as exc:  # noqa: BLE001
            logger.warning('element_picker auth ensure failed: %s', exc)
            storage = load_path_if_exists(auth_file)

    session_id = uuid.uuid4().hex
    sess = ElementPickerSession(session_id, user_id, project_id, start_url)
    with _LOCK:
        _SESSIONS[_session_key(user_id)] = sess
    sess.start_background(storage)
    # 目标约 10s 出首帧；上限 18s 避免长时间挂死
    if not sess._ready.wait(timeout=18):
        stop_for_user(user_id)
        raise RuntimeError('启动拾取浏览器超时（约18s），请检查目标站点是否可达')
    if sess.status == 'error':
        stop_for_user(user_id)
        raise RuntimeError(sess.error or '启动拾取失败')
    logger.info(
        'element_picker start_for_user done in %.1fs has_image=%s',
        time.monotonic() - t0,
        bool(sess._last_image),
    )
    return sess
