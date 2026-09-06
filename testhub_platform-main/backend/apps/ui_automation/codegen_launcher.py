"""
最大化窗口的 Playwright Codegen 启动器。

官方 `playwright codegen` CLI 无法传入有效的 --start-maximized
（Playwright 默认带 --no-startup-window，该参数只作用于启动默认窗，对新开 page 无效）。
本脚本用 enableRecorder 录制，并在页面创建后通过 CDP / Win32 将窗口最大化
（保留地址栏等浏览器 UI，不做 F11 页面全屏）。
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
from pathlib import Path
from typing import Any

def _screen_size() -> tuple[int, int]:
    """获取主屏分辨率，失败时回退 1920x1080。"""
    try:
        if sys.platform == 'win32':
            import ctypes

            user32 = ctypes.windll.user32
            width = int(user32.GetSystemMetrics(0))
            height = int(user32.GetSystemMetrics(1))
            if width > 0 and height > 0:
                return width, height
    except Exception:  # noqa: BLE001
        pass
    return 1920, 1080


async def _force_window_maximized(page: Any, browser_name: str) -> dict[str, Any]:
    """将录制浏览器窗口最大化（保留地址栏/标签栏等浏览器 UI，不做 F11 页面全屏）。"""
    screen_w, screen_h = _screen_size()
    result: dict[str, Any] = {'ok': False, 'bounds': None, 'via': ''}

    if browser_name == 'chromium':
        try:
            client = await page.context.new_cdp_session(page)
            info = await client.send('Browser.getWindowForTarget')
            window_id = info.get('windowId')
            if window_id is not None:
                # 若当前是 fullscreen，先退回 normal，再 maximized，才能露出地址栏
                try:
                    await client.send(
                        'Browser.setWindowBounds',
                        {'windowId': window_id, 'bounds': {'windowState': 'normal'}},
                    )
                except Exception:  # noqa: BLE001
                    pass

                applied = False
                try:
                    await client.send(
                        'Browser.setWindowBounds',
                        {'windowId': window_id, 'bounds': {'windowState': 'maximized'}},
                    )
                    applied = True
                    result['via'] = 'cdp:maximized'
                except Exception:  # noqa: BLE001
                    pass

                if not applied:
                    # 工作区近似最大化（留出任务栏空间时用整屏亦可）
                    await client.send(
                        'Browser.setWindowBounds',
                        {
                            'windowId': window_id,
                            'bounds': {
                                'left': 0,
                                'top': 0,
                                'width': screen_w,
                                'height': screen_h,
                                'windowState': 'normal',
                            },
                        },
                    )
                    result['via'] = 'cdp:bounds'

                bounds = await client.send('Browser.getWindowBounds', {'windowId': window_id})
                result['bounds'] = bounds.get('bounds')
                result['ok'] = True
                print(f'[codegen_launcher] window -> {result}', flush=True)
                return result
        except Exception as exc:  # noqa: BLE001
            print(f'[codegen_launcher] CDP maximize failed: {exc}', file=sys.stderr, flush=True)

    # 非 Chromium 或 CDP 失败：Win32 最大化可见浏览器窗口
    if sys.platform == 'win32':
        await asyncio.to_thread(_win32_maximize_browser_windows)
        result.update({'ok': True, 'via': 'win32'})
        print(f'[codegen_launcher] window -> {result}', flush=True)
        return result

    # 最后兜底：至少把视口拉到主屏大小
    try:
        await page.set_viewport_size({'width': screen_w, 'height': screen_h})
        result.update({'ok': True, 'via': 'viewport'})
    except Exception:  # noqa: BLE001
        pass
    print(f'[codegen_launcher] window -> {result}', flush=True)
    return result


async def _fit_page_to_window(page: Any, browser_name: str) -> None:
    """清除固定视口/设备指标，让页面内容跟随窗口大小（解决“窗口大、页面小”）。"""
    if browser_name == 'chromium':
        try:
            client = await page.context.new_cdp_session(page)
            await client.send('Emulation.clearDeviceMetricsOverride')
            inner = await page.evaluate('() => ({ w: window.innerWidth, h: window.innerHeight })')
            print(f'[codegen_launcher] fit page inner={inner}', flush=True)
            return
        except Exception as exc:  # noqa: BLE001
            print(f'[codegen_launcher] fit page failed: {exc}', file=sys.stderr, flush=True)

    # 非 Chromium：直接把视口拉到主屏大小
    screen_w, screen_h = _screen_size()
    try:
        await page.set_viewport_size({'width': screen_w, 'height': screen_h})
    except Exception:  # noqa: BLE001
        pass


def _win32_maximize_browser_windows() -> None:
    """枚举可见顶层窗口，最大化疑似浏览器窗口（排除 Playwright Inspector）。"""
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    SW_MAXIMIZE = 3
    GW_OWNER = 4

    EnumWindows = user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    IsWindowVisible = user32.IsWindowVisible
    GetWindow = user32.GetWindow
    GetWindowTextLengthW = user32.GetWindowTextLengthW
    GetWindowTextW = user32.GetWindowTextW
    ShowWindow = user32.ShowWindow
    GetClassNameW = user32.GetClassNameW

    browser_class_hints = (
        'Chrome_WidgetWin',  # Chromium / Chrome / Edge
        'MozillaWindowClass',  # Firefox
        'Chrome_WidgetWin_1',
    )
    browser_title_hints = (
        'chromium',
        'chrome',
        'msedge',
        'firefox',
        'webkit',
        'example',
        'http',
        'about:',
    )
    skip_title_hints = (
        'playwright inspector',
        'playwright',
        'codegen_launcher',
        'python',
    )

    def _text(hwnd: int) -> str:
        length = GetWindowTextLengthW(hwnd) + 1
        buf = ctypes.create_unicode_buffer(length)
        GetWindowTextW(hwnd, buf, length)
        return buf.value or ''

    def _class_name(hwnd: int) -> str:
        buf = ctypes.create_unicode_buffer(256)
        GetClassNameW(hwnd, buf, 256)
        return buf.value or ''

    matched: list[int] = []

    def _callback(hwnd: int, _lparam: int) -> bool:
        if not IsWindowVisible(hwnd):
            return True
        if GetWindow(hwnd, GW_OWNER):
            return True
        title = _text(hwnd)
        cls = _class_name(hwnd)
        title_l = title.lower()
        if any(s in title_l for s in skip_title_hints) and 'inspector' in title_l:
            return True
        class_hit = any(h in cls for h in browser_class_hints)
        title_hit = bool(title) and (
            any(h in title_l for h in browser_title_hints) or class_hit
        )
        if class_hit or title_hit:
            matched.append(hwnd)
        return True

    EnumWindows(EnumWindowsProc(_callback), 0)
    for hwnd in matched:
        ShowWindow(hwnd, SW_MAXIMIZE)
    # 给窗口管理器一点时间完成布局
    time.sleep(0.2)


def _normalize_url(url: str) -> str:
    target = (url or '').strip()
    if not target:
        return ''
    if (
        not target.startswith('http')
        and not target.startswith('file://')
        and not target.startswith('about:')
        and not target.startswith('data:')
    ):
        return 'http://' + target
    return target


# 录制时采集多策略定位器 + 控件截图（写入 *.captures.json）
# 不用 expose_binding：Playwright Recorder 下 binding 调用经常丢；改为页面队列 + Python 轮询。
_CAPTURE_INIT_JS = r"""
(() => {
  // 允许重复安装：先卸旧监听，避免 SPA/录制重注入后失效
  try {
    if (window.__testhubCaptureHandler) {
      document.removeEventListener('click', window.__testhubCaptureHandler, true);
      document.removeEventListener('pointerdown', window.__testhubCaptureHandler, true);
      document.removeEventListener('focusin', window.__testhubFocusHandler, true);
    }
  } catch (e) {}

  window.__testhubCaptures = window.__testhubCaptures || [];
  window.__testhubCaptureEnabled = window.__testhubCaptureEnabled !== false;
  let lastKey = '';
  let lastAt = 0;

  function cssEscape(s) {
    if (window.CSS && CSS.escape) return CSS.escape(s);
    return String(s).replace(/[^a-zA-Z0-9_-]/g, '\\$&');
  }

  function getCssPath(el, { stopAtId } = { stopAtId: true }) {
    const parts = [];
    let cur = el;
    while (cur && cur.nodeType === 1 && parts.length < 10) {
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

  function getXPath(el, { preferId } = { preferId: true }) {
    if (preferId && el.id) return '//*[@id="' + el.id.replace(/"/g, '\\"') + '"]';
    const parts = [];
    let cur = el;
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

  function buildLocators(el) {
    const out = [];
    // 策略可重复；同一策略下同一表达式不可重复
    const push = (strategy, value) => {
      if (!value || !String(value).trim()) return;
      const v = String(value).trim().slice(0, 500);
      if (out.some(x => x.strategy === strategy && x.value === v)) return;
      out.push({ strategy, value: v });
    };
    const q = (s) => String(s).replace(/"/g, '\\"');

    const tag = (el.tagName || '').toLowerCase();
    if (el.id) {
      push('id', el.id);
      push('css', '#' + cssEscape(el.id));
      push('css', tag + '#' + cssEscape(el.id));
      push('xpath', '//*[@id="' + q(el.id) + '"]');
    }

    const nameAttr = el.getAttribute('name');
    if (nameAttr) {
      push('name', nameAttr);
      push('css', tag + '[name="' + q(nameAttr) + '"]');
      push('xpath', '//' + tag + '[@name="' + q(nameAttr) + '"]');
    }

    const classRaw = (typeof el.className === 'string' ? el.className : '') || '';
    const classes = classRaw.trim().split(/\s+/).filter((c) => {
      if (!c || c.length > 48 || c.includes(':')) return false;
      // 过滤常见动态/哈希 class
      if (/^[a-f0-9]{8,}$/i.test(c)) return false;
      if (/[_-][a-f0-9]{5,}$/i.test(c)) return false;
      return true;
    });
    if (classes.length) {
      push('class', classes.join(' '));
      push('css', '.' + classes.map(cssEscape).join('.'));
      push('css', tag + '.' + classes.map(cssEscape).join('.'));
    }

    if (el.getAttribute('placeholder')) {
      const ph = el.getAttribute('placeholder');
      push('placeholder', ph);
      push('css', tag + '[placeholder="' + q(ph) + '"]');
    }
    if (el.getAttribute('title')) {
      const title = el.getAttribute('title');
      push('title', title);
      push('css', tag + '[title="' + q(title) + '"]');
    }
    if (el.getAttribute('data-testid')) {
      const tid = el.getAttribute('data-testid');
      push('test-id', tid);
      push('css', '[data-testid="' + q(tid) + '"]');
    }
    if (el.getAttribute('aria-label')) {
      push('label', el.getAttribute('aria-label'));
    }

    if (el.id) {
      const lab = document.querySelector('label[for="' + cssEscape(el.id) + '"]');
      if (lab && lab.textContent) push('label', lab.textContent.trim().slice(0, 80));
    }

    const role = el.getAttribute('role') || ({
      button: 'button', a: 'link',
      input: (el.type === 'checkbox' ? 'checkbox' : el.type === 'radio' ? 'radio' : 'textbox'),
      select: 'combobox', textarea: 'textbox',
    })[tag];
    const accessibleName = (el.getAttribute('aria-label')
      || el.getAttribute('placeholder')
      || (el.innerText || '').trim().slice(0, 40)
      || el.getAttribute('value') || '').trim();
    if (role && accessibleName) {
      push('role', role + '[name="' + q(accessibleName) + '"]');
    } else if (role) {
      push('role', role);
    }

    const text = (el.innerText || el.textContent || '').trim().slice(0, 60);
    if (text && text.length <= 40 && !/^(input|textarea|select)$/i.test(tag)) {
      push('text', text);
      push('xpath', '//' + tag + '[normalize-space()="' + q(text) + '"]');
      if (text.length >= 2) {
        push('xpath', '//' + tag + '[contains(normalize-space(),"' + q(text) + '")]');
      }
    }

    // 路径类表达式：短路径（遇 id 截断）+ 全路径，作为同策略多表达式
    push('css', getCssPath(el, { stopAtId: true }));
    push('css', getCssPath(el, { stopAtId: false }));
    push('xpath', getXPath(el, { preferId: true }));
    push('xpath', getXPath(el, { preferId: false }));
    return out;
  }

  function capture(el) {
    if (!window.__testhubCaptureEnabled) return;
    if (!el || el.nodeType !== 1) return;
    // 点到文本节点时上溯到元素
    if (el.nodeType === 3) el = el.parentElement;
    if (!el || el.nodeType !== 1) return;
    const tag = (el.tagName || '').toLowerCase();
    if (tag === 'x-pw-glass' || tag.startsWith('x-pw-')) return;
    if (el.closest && el.closest('#playwright-inspector, .playwright-inspector, [class*="pw-"], x-pw-glass')) return;
    const locators = buildLocators(el);
    if (!locators.length) return;
    const key = locators.map(l => l.strategy + '=' + l.value).join('|');
    const now = Date.now();
    if (key === lastKey && now - lastAt < 500) return;
    lastKey = key;
    lastAt = now;
    try {
      const rect = el.getBoundingClientRect();
      window.__testhubCaptures.push({
        locators,
        tag: (el.tagName || '').toLowerCase(),
        rect: { x: rect.x, y: rect.y, w: rect.width, h: rect.height },
        ts: now,
      });
    } catch (e) { /* ignore */ }
  }

  window.__testhubCaptureHandler = (e) => {
    let t = e.target;
    if (t && t.nodeType === 3) t = t.parentElement;
    capture(t);
  };
  window.__testhubFocusHandler = (e) => {
    const t = e.target;
    if (t && /^(INPUT|TEXTAREA|SELECT)$/i.test(t.tagName)) capture(t);
  };

  document.addEventListener('click', window.__testhubCaptureHandler, true);
  document.addEventListener('pointerdown', window.__testhubCaptureHandler, true);
  document.addEventListener('focusin', window.__testhubFocusHandler, true);
  window.__testhubCaptureInstalled = true;
})();
"""


def _captures_path_for(output_path: str) -> Path:
    return Path(str(output_path) + '.captures.json')


async def _install_element_capture(context: Any, output_path: str) -> dict[str, Any]:
    """录制过程中采集多策略定位器与控件截图，落到 *.captures.json。

    页面把定位器推进 window.__testhubCaptures，Python 轮询取出并截图。
    返回 {'enable', 'disable', 'start_poll', 'stop_poll', 'path'}。
    """
    import base64
    import json

    captures_path = _captures_path_for(output_path)
    captures: list[dict[str, Any]] = []
    lock = asyncio.Lock()
    enabled = {'on': False}
    poll_stop = asyncio.Event()
    poll_task: dict[str, Any] = {'task': None}

    try:
        if captures_path.exists():
            captures_path.unlink()
    except Exception:  # noqa: BLE001
        pass

    async def _flush() -> None:
        try:
            captures_path.write_text(
                json.dumps(captures, ensure_ascii=False, indent=2),
                encoding='utf-8',
            )
        except Exception as exc:  # noqa: BLE001
            print(f'[codegen_launcher] flush captures failed: {exc}', file=sys.stderr, flush=True)

    async def _screenshot_for(page: Any, locators: list[dict[str, Any]]) -> str:
        for loc in locators:
            strategy = (loc.get('strategy') or '').lower()
            value = loc.get('value') or ''
            if not value:
                continue
            try:
                if strategy == 'id':
                    handle = page.locator(f'#{value}').first
                elif strategy == 'css':
                    handle = page.locator(value).first
                elif strategy == 'xpath':
                    handle = page.locator(f'xpath={value}').first
                elif strategy == 'name':
                    handle = page.locator(f'[name="{value}"]').first
                elif strategy == 'placeholder':
                    handle = page.get_by_placeholder(value).first
                else:
                    continue
                raw = await handle.screenshot(timeout=1500)
                return base64.b64encode(raw).decode('ascii')
            except Exception:  # noqa: BLE001
                continue
        return ''

    async def _drain_page(page: Any) -> int:
        try:
            batch = await page.evaluate(
                '''() => {
                  const q = window.__testhubCaptures || [];
                  window.__testhubCaptures = [];
                  return q;
                }'''
            )
        except Exception:  # noqa: BLE001
            return 0
        if not batch:
            return 0
        added = 0
        for data in batch:
            if not isinstance(data, dict):
                continue
            locators = data.get('locators') or []
            if not locators:
                continue
            shot = await _screenshot_for(page, locators)
            entry = {
                'ts': data.get('ts') or time.time(),
                'tag': data.get('tag') or '',
                'locators': locators,
                'screenshot_b64': shot,
            }
            async with lock:
                captures.append(entry)
                await _flush()
            added += 1
            print(
                f'[codegen_launcher] capture #{len(captures)} locators={len(locators)} shot={bool(shot)}',
                flush=True,
            )
        return added

    async def _ensure_script(page: Any) -> None:
        try:
            await page.evaluate(_CAPTURE_INIT_JS)
            if enabled['on']:
                await page.evaluate('() => { window.__testhubCaptureEnabled = true; }')
            else:
                await page.evaluate('() => { window.__testhubCaptureEnabled = false; }')
        except Exception:  # noqa: BLE001
            pass

    async def _poll_loop() -> None:
        print('[codegen_launcher] capture poll started', flush=True)
        ticks = 0
        while not poll_stop.is_set():
            if enabled['on']:
                for page in list(context.pages):
                    try:
                        if page.is_closed():
                            continue
                    except Exception:  # noqa: BLE001
                        continue
                    # 每 ~2s 重装一次监听，防止 Recorder/SPA 冲掉
                    if ticks % 7 == 0:
                        await _ensure_script(page)
                    await _drain_page(page)
            ticks += 1
            try:
                await asyncio.wait_for(poll_stop.wait(), timeout=0.35)
            except asyncio.TimeoutError:
                pass
        # 收尾再扫一次
        for page in list(context.pages):
            try:
                if not page.is_closed():
                    await _drain_page(page)
            except Exception:  # noqa: BLE001
                pass
        print(f'[codegen_launcher] capture poll stopped total={len(captures)}', flush=True)

    try:
        await context.add_init_script(_CAPTURE_INIT_JS)
    except Exception as exc:  # noqa: BLE001
        print(f'[codegen_launcher] add_init_script: {exc}', file=sys.stderr, flush=True)

    for p in list(context.pages):
        await _ensure_script(p)

    def _on_page(p: Any) -> None:
        async def _install() -> None:
            await _ensure_script(p)
        asyncio.create_task(_install())

    context.on('page', _on_page)
    print(f'[codegen_launcher] element capture -> {captures_path}', flush=True)

    def enable() -> None:
        enabled['on'] = True
        print('[codegen_launcher] element capture enabled', flush=True)
        for p in list(context.pages):
            asyncio.create_task(_ensure_script(p))

    def disable() -> None:
        enabled['on'] = False

    def start_poll() -> None:
        if poll_task['task'] is None or poll_task['task'].done():
            poll_stop.clear()
            poll_task['task'] = asyncio.create_task(_poll_loop())

    async def stop_poll() -> None:
        poll_stop.set()
        task = poll_task.get('task')
        if task is not None:
            try:
                await asyncio.wait_for(task, timeout=3)
            except Exception:  # noqa: BLE001
                task.cancel()

    return {
        'enable': enable,
        'disable': disable,
        'start_poll': start_poll,
        'stop_poll': stop_poll,
        'path': captures_path,
    }


async def run_codegen(
    url: str,
    output: str,
    browser_name: str,
    language: str,
    stop_file: str = '',
    login_username: str = '',
    login_password: str = '',
) -> None:
    from playwright.async_api import async_playwright

    # 本文件常作为独立脚本启动，需把同目录加入 path
    _here = Path(__file__).resolve().parent
    if str(_here) not in sys.path:
        sys.path.insert(0, str(_here))
    from auth_state import (
        load_path_if_exists,
        load_path_if_fresh,
        save_storage_state,
        try_auto_login,
    )

    output_path = str(Path(output).resolve())
    stop_path = Path(stop_file).resolve() if stop_file else Path(output_path + '.stop')
    screen_w, screen_h = _screen_size()
    login_username = (login_username or os.environ.get('CODEGEN_LOGIN_USERNAME', '')).strip()
    login_password = login_password or os.environ.get('CODEGEN_LOGIN_PASSWORD', '')
    auth_path = (os.environ.get('CODEGEN_AUTH_STATE_PATH') or '').strip()
    reuse_auth_only = os.environ.get('CODEGEN_REUSE_AUTH_ONLY', '').strip().lower() in {
        '1', 'true', 'yes', 'on',
    }
    # 复用登录态：只加载已由 ensure_project_auth_state 准备好的文件，绝不在录制窗表单登录
    if reuse_auth_only:
        storage_to_load = load_path_if_exists(auth_path) if auth_path else None
    else:
        storage_to_load = load_path_if_fresh(auth_path) if auth_path else None

    # 清理上次残留的停止标记
    try:
        if stop_path.exists():
            stop_path.unlink()
    except Exception:  # noqa: BLE001
        pass

    async with async_playwright() as p:
        browser_type = getattr(p, browser_name, None)
        if browser_type is None:
            raise RuntimeError(f'不支持的浏览器: {browser_name}')

        launch_options: dict[str, Any] = {
            'headless': False,
            'handle_sigint': False,
        }
        # 注意：Python API 里 viewport=None 表示“未指定”，仍会用默认 1280x720。
        # 要让页面随窗口铺满，必须 no_viewport=True（协议字段 noDefaultViewport）。
        context_options: dict[str, Any] = {'no_viewport': True}
        if storage_to_load:
            context_options['storage_state'] = storage_to_load
            print(f'[codegen_launcher] reuse auth state: {storage_to_load}', flush=True)
        elif auth_path and reuse_auth_only:
            raise RuntimeError(
                f'复用登录态已开启但未找到登录态文件: {auth_path}'
            )

        if browser_name == 'chromium':
            # --start-maximized 对 Playwright 新开 page 基本无效，仍保留作辅助；
            # 真正最大化依赖后面的 CDP setWindowBounds(maximized)。
            launch_options['args'] = [
                '--start-maximized',
                f'--window-size={screen_w},{screen_h}',
                '--window-position=0,0',
            ]

        browser = await browser_type.launch(**launch_options)
        context = await browser.new_context(**context_options)

        # 先装采集钩子，再开页面/录制（登录阶段保持关闭）
        capture_ctl = await _install_element_capture(context, output_path)

        page = await context.new_page()
        target = _normalize_url(url)
        if target:
            await page.goto(target, wait_until='domcontentloaded')

        # 复用登录态：只注入 storage_state，绝不走表单自动登录
        logged_in = bool(storage_to_load)
        if reuse_auth_only or auth_path:
            if storage_to_load:
                print('[codegen_launcher] reuse auth: loaded, skip form login', flush=True)
            else:
                print('[codegen_launcher] reuse auth: no state file, skip form login', flush=True)
        elif login_username and login_password:
            # 仅显式 FORCE 时才表单登录（默认录制链路不再走这里）
            force = os.environ.get('CODEGEN_FORCE_FORM_LOGIN', '').strip().lower() in {
                '1', 'true', 'yes', 'on',
            }
            if force:
                logged_in = await try_auto_login(page, login_username, login_password)
                if logged_in and auth_path:
                    saved = await save_storage_state(context, auth_path)
                    print(f'[codegen_launcher] auth state saved={saved} path={auth_path!r}', flush=True)
            else:
                print('[codegen_launcher] form login disabled (set CODEGEN_FORCE_FORM_LOGIN=1 to enable)', flush=True)
        else:
            print('[codegen_launcher] no auth reuse / no credentials', flush=True)

        recorder_launch_options: dict[str, Any] = {'headless': False}
        if launch_options.get('args'):
            recorder_launch_options['args'] = launch_options['args']

        # 写入生成脚本的上下文选项：禁用固定视口，回放时页面也会随窗口变化
        recorder_context_options: dict[str, Any] = {'noViewport': True}

        await context._impl_obj._channel.send(
            'enableRecorder',
            None,
            {
                'language': language,
                'launchOptions': recorder_launch_options,
                'contextOptions': recorder_context_options,
                'mode': 'recording',
                'outputFile': output_path,
                'handleSIGINT': False,
            },
            True,
        )

        # 开录后再采集，避免登录点击进入 captures；并重装页面监听（Recorder 可能冲掉）
        capture_ctl['enable']()
        capture_ctl['start_poll']()
        try:
            await page.evaluate(_CAPTURE_INIT_JS)
            await page.evaluate('() => { window.__testhubCaptureEnabled = true; }')
        except Exception as exc:  # noqa: BLE001
            print(f'[codegen_launcher] reinject capture failed: {exc}', file=sys.stderr, flush=True)

        # 未登录时再 goto 一次，让脚本有起始导航；已登录则禁止刷新，避免 SPA 丢登录态
        if not logged_in and target:
            try:
                await page.goto(target, wait_until='domcontentloaded')
                await page.evaluate(_CAPTURE_INIT_JS)
                await page.evaluate('() => { window.__testhubCaptureEnabled = true; }')
            except Exception as exc:  # noqa: BLE001
                print(f'[codegen_launcher] seed goto skipped: {exc}', file=sys.stderr, flush=True)

        # 立刻开始监听停止（与最大化并行），避免用户在最大化期间点停止导致永远无法收尾
        async def _flush_auth_before_close() -> None:
            if not auth_path:
                return
            try:
                saved = await save_storage_state(context, auth_path)
                print(f'[codegen_launcher] auth state flushed={saved} path={auth_path!r}', flush=True)
            except Exception as exc:  # noqa: BLE001
                print(f'[codegen_launcher] auth state flush failed: {exc}', file=sys.stderr, flush=True)

        wait_task = asyncio.create_task(
            _wait_until_recording_done(
                browser, context, stop_path,
                initially_recording=True,
                before_close=_flush_auth_before_close,
            )
        )

        try:
            await _force_window_maximized(page, browser_name)
            await _fit_page_to_window(page, browser_name)
            for delay in (0.5, 1.0, 2.0):
                if wait_task.done():
                    break
                await asyncio.sleep(delay)
                await _force_window_maximized(page, browser_name)
                await _fit_page_to_window(page, browser_name)
                try:
                    await page.evaluate(_CAPTURE_INIT_JS)
                    await page.evaluate('() => { window.__testhubCaptureEnabled = true; }')
                except Exception:  # noqa: BLE001
                    pass
        except Exception as exc:  # noqa: BLE001
            print(f'[codegen_launcher] maximize skipped: {exc}', file=sys.stderr, flush=True)

        await wait_task
        await capture_ctl['stop_poll']()

        # 给 Recorder 一点时间把 ThrottledFile 刷盘
        await asyncio.sleep(0.3)
        try:
            if stop_path.exists():
                stop_path.unlink()
        except Exception:  # noqa: BLE001
            pass


async def _wait_until_recording_done(
    browser: Any,
    context: Any,
    stop_path: Path,
    initially_recording: bool = True,
    before_close: Any = None,
) -> None:
    """等待：Inspector/悬浮条停止录制、关浏览器、或后端停止标记。"""
    done = asyncio.Event()

    def _mark_done() -> None:
        if not done.is_set():
            done.set()

    def _on_disconnect() -> None:
        print('[codegen_launcher] browser disconnected', flush=True)
        _mark_done()

    async def _close_browser_quiet() -> None:
        if before_close is not None:
            try:
                await before_close()
            except Exception as exc:  # noqa: BLE001
                print(f'[codegen_launcher] before_close failed: {exc}', file=sys.stderr, flush=True)
        try:
            if browser.is_connected():
                await browser.close()
        except Exception as exc:  # noqa: BLE001
            print(f'[codegen_launcher] browser.close failed: {exc}', file=sys.stderr, flush=True)
        _mark_done()

    def _on_page_close() -> None:
        try:
            has_page = any(ctx.pages for ctx in browser.contexts)
        except Exception:  # noqa: BLE001
            has_page = False
        if not has_page:
            print('[codegen_launcher] last page closed, stopping', flush=True)
            asyncio.create_task(_close_browser_quiet())

    def _bind_page(p: Any) -> None:
        p.on('close', _on_page_close)

    browser.on('disconnected', _on_disconnect)
    context.on('page', _bind_page)
    for p in context.pages:
        _bind_page(p)

    async def _watch_stop_file() -> None:
        while not done.is_set():
            if stop_path.exists():
                print('[codegen_launcher] stop file detected, closing browser', flush=True)
                await _close_browser_quiet()
                return
            await asyncio.sleep(0.4)

    async def _watch_inspector_stop() -> None:
        """
        用 CDP 实时属性 + Accessibility 检测停止。
        启动时 mode=recording，因此 initially_recording=True，避免从未看到 True 而无法收尾。

        注意：页面跳转时悬浮条会短暂重建，探针可能闪 False；
        必须连续稳定一段时间才确认停止，否则会误关浏览器。
        """
        seen_recording = bool(initially_recording)
        false_streak = 0
        ticks = 0
        # 给悬浮条初始化留一点时间，避免刚启动误判
        armed_after_ticks = 12  # ~6s
        # ~4s 连续 False 才确认（导航闪断通常 <1–2s）
        confirm_false_ticks = 8

        while not done.is_set():
            try:
                state = await _probe_recording_active_cdp(context)
            except Exception as exc:  # noqa: BLE001
                print(f'[codegen_launcher] probe error: {exc}', file=sys.stderr, flush=True)
                state = None

            ticks += 1
            if ticks == 1 or ticks % 5 == 0 or state is True or state is False:
                print(
                    f'[codegen_launcher] probe state={state} seen={seen_recording} false_streak={false_streak}',
                    flush=True,
                )

            if state is True:
                seen_recording = True
                false_streak = 0
            elif state is False:
                false_streak += 1
                if (
                    seen_recording
                    and ticks >= armed_after_ticks
                    and false_streak >= confirm_false_ticks
                ):
                    print(
                        '[codegen_launcher] stop recording confirmed, closing browser',
                        flush=True,
                    )
                    await asyncio.sleep(0.4)
                    await _close_browser_quiet()
                    return
            else:
                # 不确定（导航中悬浮条暂不可见）→ 清空，避免跨闪断累计
                false_streak = 0

            await asyncio.sleep(0.5)

    watcher = asyncio.create_task(_watch_stop_file())
    mode_watcher = asyncio.create_task(_watch_inspector_stop())
    try:
        await done.wait()
    finally:
        for task in (watcher, mode_watcher):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


def _attrs_list_to_dict(attrs_list: list[Any]) -> dict[str, str]:
    return {str(attrs_list[i]): str(attrs_list[i + 1]) for i in range(0, len(attrs_list), 2)}


def _walk_cdp_node_for_record(node: dict[str, Any], found: list[tuple[int, dict[str, str]]]) -> None:
    name = (node.get('localName') or node.get('nodeName') or '').lower()
    attrs = _attrs_list_to_dict(node.get('attributes') or [])
    node_id = node.get('nodeId')
    if (
        name == 'x-pw-tool-item'
        and 'record' in (attrs.get('class') or '').split()
        and isinstance(node_id, int)
    ):
        found.append((node_id, attrs))
    for child in node.get('children') or []:
        _walk_cdp_node_for_record(child, found)
    for root in node.get('shadowRoots') or []:
        _walk_cdp_node_for_record(root, found)


async def _probe_recording_active_cdp(context: Any) -> bool | None:
    """
    CDP 检测录制状态。
    True=录制中, False=已停止, None=尚未出现悬浮条/不确定。
    任一页面为录制中即 True；仅当 DOM 明确找到录制按钮且全部非录制才 False。
    AX 的 Start Recording  alone 不够可靠（导航闪断时会误报），不单独作为 False。
    """
    saw_dom_button = False
    any_recording = False

    for page in list(getattr(context, 'pages', []) or []):
        client = None
        try:
            if page.is_closed():
                continue
            client = await page.context.new_cdp_session(page)

            # 1) Accessibility：只采信「正在录制」正信号
            try:
                ax = await client.send('Accessibility.getFullAXTree')
                for node in ax.get('nodes') or []:
                    name = ((node.get('name') or {}).get('value')) or ''
                    if name in {'Stop Recording', '停止录制'}:
                        return True
            except Exception:  # noqa: BLE001
                pass

            # 2) DOM pierce + 实时 getAttributes（避免 describeNode 缓存）
            doc = await client.send('DOM.getDocument', {'depth': 0})
            root_id = doc['root']['nodeId']
            glasses = await client.send('DOM.querySelectorAll', {
                'nodeId': root_id,
                'selector': 'x-pw-glass',
            })
            for glass_id in glasses.get('nodeIds') or []:
                desc = await client.send('DOM.describeNode', {
                    'nodeId': glass_id,
                    'depth': -1,
                    'pierce': True,
                })
                found: list[tuple[int, dict[str, str]]] = []
                _walk_cdp_node_for_record(desc.get('node') or {}, found)
                for node_id, snap_attrs in found:
                    saw_dom_button = True
                    attrs = snap_attrs
                    try:
                        live = await client.send('DOM.getAttributes', {'nodeId': node_id})
                        attrs = _attrs_list_to_dict(live.get('attributes') or [])
                    except Exception:  # noqa: BLE001
                        pass
                    cls = attrs.get('class') or ''
                    title = attrs.get('title') or ''
                    recording = (
                        ('toggled' in cls.split())
                        or title in {'Stop Recording', '停止录制'}
                    )
                    if recording:
                        any_recording = True
        except Exception as exc:  # noqa: BLE001
            print(f'[codegen_launcher] cdp probe page failed: {exc}', file=sys.stderr, flush=True)
            continue
        finally:
            if client is not None:
                try:
                    await client.detach()
                except Exception:  # noqa: BLE001
                    pass

    if any_recording:
        return True
    if saw_dom_button:
        return False
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Maximized Playwright codegen launcher')
    parser.add_argument('url', nargs='?', default='', help='起始 URL')
    parser.add_argument('-o', '--output', required=True, help='录制脚本输出路径')
    parser.add_argument(
        '-b', '--browser',
        default='chromium',
        choices=('chromium', 'firefox', 'webkit'),
        help='浏览器类型',
    )
    parser.add_argument(
        '--target',
        default='python-pytest',
        help='代码语言目标，如 python-pytest / javascript / playwright-test',
    )
    parser.add_argument(
        '--stop-file',
        default='',
        help='停止标记文件；后端结束录制时创建该文件以优雅退出',
    )
    parser.add_argument(
        '--login-username',
        default='',
        help='录制前自动登录账号（也可设环境变量 CODEGEN_LOGIN_USERNAME）',
    )
    # 密码优先走环境变量，避免出现在进程命令行 / 日志里
    parser.add_argument(
        '--login-password',
        default='',
        help='一般不要用；请设 CODEGEN_LOGIN_PASSWORD',
    )
    args = parser.parse_args(argv)

    try:
        asyncio.run(run_codegen(
            args.url,
            args.output,
            args.browser,
            args.target,
            stop_file=args.stop_file,
            login_username=args.login_username,
            login_password=args.login_password,
        ))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f'codegen launcher failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    # 轻量自检：文案常量与 URL 规范化
    if os.environ.get('CODEGEN_LAUNCHER_SELFCHECK') == '1':
        assert _normalize_url('example.com') == 'http://example.com'
        from auth_state import _PASSWORD_FIELD_NAMES, _USER_FIELD_NAMES
        assert '请输入手机号/用户名' in _USER_FIELD_NAMES
        assert '请输入密码' in _PASSWORD_FIELD_NAMES
        print('codegen_launcher selfcheck ok')
        raise SystemExit(0)
    raise SystemExit(main())