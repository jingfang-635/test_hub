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


async def run_codegen(
    url: str,
    output: str,
    browser_name: str,
    language: str,
    stop_file: str = '',
) -> None:
    from playwright.async_api import async_playwright

    output_path = str(Path(output).resolve())
    stop_path = Path(stop_file).resolve() if stop_file else Path(output_path + '.stop')
    screen_w, screen_h = _screen_size()

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

        page = await context.new_page()
        if url:
            target = url
            if (
                not target.startswith('http')
                and not target.startswith('file://')
                and not target.startswith('about:')
                and not target.startswith('data:')
            ):
                target = 'http://' + target
            await page.goto(target)

        # 立刻开始监听停止（与最大化并行），避免用户在最大化期间点停止导致永远无法收尾
        wait_task = asyncio.create_task(
            _wait_until_recording_done(browser, context, stop_path, initially_recording=True)
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
        except Exception as exc:  # noqa: BLE001
            print(f'[codegen_launcher] maximize skipped: {exc}', file=sys.stderr, flush=True)

        await wait_task

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
        """
        seen_recording = bool(initially_recording)
        false_streak = 0
        ticks = 0
        # 给悬浮条初始化留一点时间，避免刚启动误判
        armed_after_ticks = 4  # ~2s

        while not done.is_set():
            try:
                state = await _probe_recording_active_cdp(context)
            except Exception as exc:  # noqa: BLE001
                print(f'[codegen_launcher] probe error: {exc}', file=sys.stderr, flush=True)
                state = None

            ticks += 1
            if ticks == 1 or ticks % 5 == 0 or state is True:
                print(
                    f'[codegen_launcher] probe state={state} seen={seen_recording} false_streak={false_streak}',
                    flush=True,
                )

            if state is True:
                seen_recording = True
                false_streak = 0
            elif state is False:
                false_streak += 1
                if seen_recording and ticks >= armed_after_ticks and false_streak >= 2:
                    print(
                        '[codegen_launcher] stop recording confirmed, closing browser',
                        flush=True,
                    )
                    await asyncio.sleep(0.4)
                    await _close_browser_quiet()
                    return
            else:
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
    True=录制中, False=已停止, None=尚未出现悬浮条。
    任一页面为录制中即 True；仅当找到按钮且全部非录制才 False。
    """
    saw_button = False
    any_recording = False

    for page in list(getattr(context, 'pages', []) or []):
        client = None
        try:
            if page.is_closed():
                continue
            client = await page.context.new_cdp_session(page)

            # 1) Accessibility：最直观（Stop Recording / Start Recording）
            try:
                ax = await client.send('Accessibility.getFullAXTree')
                for node in ax.get('nodes') or []:
                    name = ((node.get('name') or {}).get('value')) or ''
                    if name == 'Stop Recording':
                        return True
                    if name == 'Start Recording':
                        saw_button = True
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
                    saw_button = True
                    attrs = snap_attrs
                    try:
                        live = await client.send('DOM.getAttributes', {'nodeId': node_id})
                        attrs = _attrs_list_to_dict(live.get('attributes') or [])
                    except Exception:  # noqa: BLE001
                        pass
                    cls = attrs.get('class') or ''
                    title = attrs.get('title') or ''
                    recording = ('toggled' in cls.split()) or title == 'Stop Recording'
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
    if saw_button:
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
    args = parser.parse_args(argv)

    try:
        asyncio.run(run_codegen(
            args.url,
            args.output,
            args.browser,
            args.target,
            stop_file=args.stop_file,
        ))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f'codegen launcher failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())