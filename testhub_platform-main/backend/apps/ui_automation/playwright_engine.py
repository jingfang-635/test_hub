"""
Playwright自动化测试执行引擎
用于驱动真实浏览器执行UI自动化测试
"""
import asyncio
import base64
import time
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# 设置 Playwright 浏览器安装路径（自定义路径）
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'ms-playwright'))

# playwright 是 optional 依赖，Vercel 等 Serverless 环境可能未安装
try:
    from playwright.async_api import async_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeout
except ImportError:
    async_playwright = None
    Page = None
    Browser = None
    BrowserContext = None
    PlaywrightTimeout = None
import logging
from .variable_resolver import resolve_variables

logger = logging.getLogger(__name__)

class PlaywrightTestEngine:
    """Playwright测试执行引擎"""

    def __init__(self, browser_type='chromium', headless=True):
        """
        初始化测试引擎

        Args:
            browser_type: 浏览器类型 (chromium, firefox, webkit)
            headless: 是否无头模式
        """
        self.browser_type = browser_type
        self.headless = headless
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def _dismiss_blocking_overlays(self, timeout_ms: int = 2000) -> None:
        """关闭拦截点击的常见遮罩（如登录弹窗 .popup-mask）。"""
        if not self.page:
            return
        selectors = ('.popup-mask', '.el-overlay', '.modal-backdrop', '.van-overlay')
        for sel in selectors:
            try:
                loc = self.page.locator(sel).first
                if await loc.count() == 0:
                    continue
                if not await loc.is_visible():
                    continue
                try:
                    await loc.wait_for(state='hidden', timeout=timeout_ms)
                    continue
                except Exception:
                    pass
                try:
                    await self.page.keyboard.press('Escape')
                    await loc.wait_for(state='hidden', timeout=800)
                    continue
                except Exception:
                    pass
                # 仍可见则禁用指针拦截，避免挡住后续业务点击
                await loc.evaluate(
                    """el => {
                        el.style.pointerEvents = 'none';
                        el.style.display = 'none';
                    }"""
                )
            except Exception:
                continue

    @staticmethod
    def _collect_link_target(element_name: str, locator_value: str) -> Optional[str]:
        """识别收藏相关链接目标：'已收藏' | '收藏商品' | None。"""
        text = f'{element_name or ""} {locator_value or ""}'
        if '已收藏' in text:
            return '已收藏'
        if '收藏商品' in text:
            return '收藏商品'
        return None

    @staticmethod
    def _is_goods_entry_locator(locator_value: str) -> bool:
        """是否为商城商品入口（列表点进详情），点击后需确认完成跳转。"""
        v = (locator_value or '').lower()
        return 'goods-img' in v or 'goods-list' in v or 'goods-item' in v

    def _is_on_goods_detail(self) -> bool:
        url = (self.page.url if self.page else '') or ''
        return '/detail/' in url or '/secdetail/' in url

    async def _wait_for_goods_detail(self, timeout_ms: int) -> bool:
        """等待进入商品详情（/detail/ 或 /secdetail/），或出现收藏控件。"""
        import re

        if self._is_on_goods_detail():
            return True
        try:
            await self.page.wait_for_url(
                re.compile(r'.*/(sec)?detail/\d+'),
                timeout=max(timeout_ms, 1000),
            )
            return True
        except Exception:
            pass
        either = self.page.get_by_role('link', name=re.compile(r'^(收藏商品|已收藏)$'))
        try:
            await either.first.wait_for(state='visible', timeout=min(2000, max(timeout_ms, 1000)))
            return True
        except Exception:
            return self._is_on_goods_detail()

    async def _click_goods_entry(
        self,
        locator,
        timeout_ms: int,
        force_action: bool = False,
    ) -> Tuple[bool, str]:
        """
        点击商品入口并确认进入详情。
        列表页 .goods-img 点击偶发不触发路由（仍停在 /list），需等待结果并重试。
        """
        await self._dismiss_blocking_overlays()
        await locator.wait_for(state='visible', timeout=timeout_ms)
        # 搜索结果刚渲染时立刻点可能无效，稍候再点
        await asyncio.sleep(0.6)

        attempts_desc = []
        for attempt in range(1, 4):
            await self._dismiss_blocking_overlays()
            try:
                if attempt == 1:
                    await locator.click(timeout=timeout_ms, force=force_action)
                    attempts_desc.append('img')
                elif attempt == 2:
                    parent = self.page.locator('.goods-img').first
                    await parent.wait_for(state='visible', timeout=timeout_ms)
                    await parent.click(timeout=timeout_ms, force=force_action)
                    attempts_desc.append('goods-img')
                else:
                    await locator.evaluate('el => el.click()')
                    attempts_desc.append('js-click')
            except Exception as e:
                attempts_desc.append(f'fail:{e}')
                await asyncio.sleep(0.3)
                continue

            nav_timeout = min(max(timeout_ms, 3000), 8000)
            if await self._wait_for_goods_detail(nav_timeout):
                return True, (
                    f'进入商品详情成功（第{attempt}次，方式={"/".join(attempts_desc)}，'
                    f'URL={self.page.url}）'
                )
            await asyncio.sleep(0.4)

        return False, (
            f'点击商品后未进入详情页（当前URL: {self.page.url}，'
            f'尝试: {"/".join(attempts_desc)}）'
        )

    async def _click_collect_link(
        self,
        target: str,
        timeout_ms: int,
        force_action: bool = False,
    ) -> Tuple[bool, str]:
        """
        幂等处理商品详情收藏开关。
        详情页可能显示「收藏商品」或「已收藏」，录制脚本硬点其一会因状态不稳定超时。
        - 目标「已收藏」：若当前已收藏则点击取消；若已是未收藏则跳过。
        - 目标「收藏商品」：若当前未收藏则点击收藏；若已是已收藏则跳过。
        """
        import re

        await self._dismiss_blocking_overlays()

        # 若仍停在列表页（商品点击未跳转），先补点进入详情再等收藏控件
        if not self._is_on_goods_detail():
            goods = self.page.locator('.goods-img > img').first
            try:
                if await goods.count() > 0 and await goods.is_visible():
                    ok, detail = await self._click_goods_entry(
                        goods, timeout_ms, force_action=force_action
                    )
                    if not ok:
                        return False, f'收藏前未能进入详情: {detail}'
            except Exception as e:
                logger.warning(f'收藏前补点商品详情失败: {e}')

        either = self.page.get_by_role('link', name=re.compile(r'^(收藏商品|已收藏)$'))
        try:
            await either.first.wait_for(state='visible', timeout=timeout_ms)
        except Exception as e:
            return False, f'等待收藏控件超时: {e}'

        fav = self.page.get_by_role('link', name='收藏商品')
        collected = self.page.get_by_role('link', name='已收藏')

        async def _visible(loc) -> bool:
            try:
                return (await loc.count()) > 0 and await loc.first.is_visible()
            except Exception:
                return False

        if target == '已收藏':
            if await _visible(collected):
                await collected.first.click(timeout=timeout_ms, force=force_action)
                return True, '点击「已收藏」取消收藏'
            return True, '当前已是未收藏态，跳过点击「已收藏」'

        if target == '收藏商品':
            if await _visible(fav):
                await fav.first.click(timeout=timeout_ms, force=force_action)
                return True, '点击「收藏商品」完成收藏'
            return True, '当前已是收藏态，跳过点击「收藏商品」'

        return False, f'未知收藏目标: {target}'

    async def start(self, storage_state: str | None = None):
        """启动浏览器。storage_state 为已保存的登录态 JSON 路径（可选）。"""
        try:
            self.playwright = await async_playwright().start()

            # 根据浏览器类型选择启动方式
            if self.browser_type == 'chromium':
                browser_launcher = self.playwright.chromium
            elif self.browser_type == 'firefox':
                browser_launcher = self.playwright.firefox
            elif self.browser_type == 'webkit':
                browser_launcher = self.playwright.webkit
            else:
                browser_launcher = self.playwright.chromium

            # 启动浏览器
            self.browser = await browser_launcher.launch(
                headless=self.headless,
                args=[
                    '--disable-blink-features=AutomationControlled',  # 避免被检测
                    '--ignore-certificate-errors',  # 忽略证书错误
                    '--allow-insecure-localhost',  # 允许不安全localhost
                    '--disable-web-security',  # 禁用web安全限制（跨域）
                ]
            )

            context_kwargs = {
                'viewport': {'width': 1920, 'height': 1080},
                'user_agent': (
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36'
                ),
            }
            if storage_state:
                context_kwargs['storage_state'] = storage_state

            self.context = await self.browser.new_context(**context_kwargs)

            # 创建页面
            self.page = await self.context.new_page()

            logger.info(
                "浏览器启动成功: %s, headless=%s, storage_state=%s",
                self.browser_type,
                self.headless,
                bool(storage_state),
            )

        except Exception as e:
            logger.error(f"启动浏览器失败: {str(e)}")
            raise

    async def stop(self):
        """关闭浏览器"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("浏览器已关闭")
        except Exception as e:
            logger.error(f"关闭浏览器失败: {str(e)}")

    def _build_locator(self, locator_strategy: str, locator_value: str):
        """按策略构造 Playwright locator（不做 wait）。"""
        strategy = (locator_strategy or 'css').lower()
        value = locator_value or ''

        _has_explicit_index = False
        if any(x in value for x in [
            '>> nth=', ':nth-child(', ':nth-of-type(', ':first-child', ':last-child', '>> first', '>> last'
        ]):
            _has_explicit_index = True

        if strategy == 'id':
            locator = self.page.locator(f'#{value}')
            return locator if _has_explicit_index else locator.first
        if strategy in ['class', 'class name']:
            classes = [c.strip() for c in value.split() if c.strip()]
            locator = self.page.locator('.' + '.'.join(classes)) if classes else self.page.locator(value)
            return locator if _has_explicit_index else locator.first
        if strategy in ['css', 'css selector']:
            if any(keyword in value.lower() for keyword in ['dropdown', 'el-select', ':has(', 'li']):
                if 'visible=true' not in value:
                    return self.page.locator(f"{value} >> visible=true").first
                return self.page.locator(value).first
            locator = self.page.locator(value)
            return locator if _has_explicit_index else locator.first
        if strategy == 'xpath':
            if any(keyword in value.lower() for keyword in ['dropdown', 'el-select', ':has(', 'li']):
                if 'visible=true' not in value:
                    return self.page.locator(f"xpath={value} >> visible=true").first
                return self.page.locator(f"xpath={value}").first
            if '[' in value and ']' in value:
                return self.page.locator(f'xpath={value}')
            return self.page.locator(f'xpath={value}').first
        if strategy == 'label':
            locator = self.page.get_by_label(value.split(' >> ')[0])
            return locator if _has_explicit_index else locator.first
        if strategy == 'placeholder':
            locator = self.page.get_by_placeholder(value.split(' >> ')[0])
            return locator if _has_explicit_index else locator.first
        if strategy == 'role':
            role_sel = value if value.startswith('role=') else f'role={value}'
            locator = self.page.locator(role_sel)
            return locator if _has_explicit_index else locator.first
        if strategy == 'text':
            text_sel = value if value.startswith('text=') else f'text={value}'
            locator = self.page.locator(text_sel)
            return locator if _has_explicit_index else locator.first
        if strategy == 'name':
            locator = self.page.locator(f'[name="{value}"]')
            return locator if _has_explicit_index else locator.first
        if strategy == 'title':
            return self.page.get_by_title(value).first
        if strategy == 'test-id':
            locator = self.page.get_by_test_id(value)
            return locator if _has_explicit_index else locator.first
        locator = self.page.locator(value)
        return locator if _has_explicit_index else locator.first

    @staticmethod
    def _is_junk_locator(strategy: str, value: str) -> bool:
        """过滤 Playwright Inspector 遮罩等无效定位器。"""
        v = (value or '').lower()
        s = (strategy or '').lower()
        if 'x-pw-glass' in v or 'playwright-inspector' in v:
            return True
        if s in ('css', 'css selector', 'xpath') and 'pw-glass' in v:
            return True
        return False

    def _build_locator_candidates(self, element_data: Dict) -> List[Dict]:
        primary_strategy = element_data.get('locator_strategy', 'css')
        primary_value = element_data.get('locator_value', '')
        candidates: List[Dict] = []
        seen = set()

        def _add(strategy: str, value: str):
            strategy = (strategy or '').strip()
            value = (value or '').strip()
            if not strategy or not value:
                return
            if self._is_junk_locator(strategy, value):
                return
            key = (strategy.lower(), value)
            if key in seen:
                return
            seen.add(key)
            candidates.append({'strategy': strategy, 'value': value})

        _add(primary_strategy, primary_value)
        for backup in element_data.get('backup_locators') or []:
            _add(backup.get('strategy') or '', backup.get('value') or '')
        return candidates

    @staticmethod
    def _format_tried_locators(candidates: List[Dict]) -> str:
        if not candidates:
            return ''
        lines = ['  - 已尝试定位器:']
        for i, cand in enumerate(candidates):
            tag = '主' if i == 0 else f'备{i}'
            lines.append(f"    [{tag}] {cand['strategy']}={cand['value']}")
        return '\n'.join(lines)

    @staticmethod
    def append_heal_note(log: str, element_data: Optional[Dict]) -> str:
        """在步骤日志中追加 AI 自愈说明（不修改元素库）。"""
        if not element_data or not element_data.get('_healed'):
            return log or ''
        if log and 'AI自愈' in log:
            return log
        healed_loc = element_data.get('_healed_locator') or {}
        reason = element_data.get('_healing_reason') or ''
        note = (
            f"\n  ★ AI自愈执行通过（未修改原元素/步骤）\n"
            f"  - 临时定位器: {healed_loc.get('strategy')}={healed_loc.get('value')}\n"
            f"  - AI分析原失败原因: {reason}"
        )
        return (log or '') + note

    async def _try_ai_heal_locator(
        self,
        element_data: Dict,
        failed_candidates: List[Dict],
        last_error,
        timeout_ms: int,
    ):
        """
        主/备用定位器均失效后，调用 AI 分析并临时尝试推荐定位器。
        仅当次执行生效，不写回元素库/步骤。
        成功返回 (locator, strategy, value)，失败返回 None。
        """
        # 清理上次自愈痕迹
        element_data.pop('_healed', None)
        element_data.pop('_healed_locator', None)
        element_data.pop('_healing_reason', None)

        try:
            from .ai_locator_healer import suggest_healed_locators

            heal = await suggest_healed_locators(
                self.page,
                element_data,
                failed_candidates,
                last_error=str(last_error or ''),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning('AI locator heal failed to start: %s', exc)
            return None

        failure_reason = (heal or {}).get('failure_reason') or '主/备用定位器均失效'
        suggestions = (heal or {}).get('locators') or []
        if not suggestions:
            element_data['_healing_reason'] = failure_reason
            element_data['_healed'] = False
            logger.info('AI healer returned no locator suggestions')
            return None

        probe_timeout = min(3000, max(timeout_ms, 1))
        for sug in suggestions:
            strategy = (sug.get('strategy') or '').strip()
            value = (sug.get('value') or '').strip()
            if not strategy or not value:
                continue
            if self._is_junk_locator(strategy, value):
                continue
            # 跳过与已失败定位器完全相同的建议
            dup = any(
                (c.get('strategy') or '').lower() == strategy.lower()
                and (c.get('value') or '') == value
                for c in (failed_candidates or [])
            )
            if dup:
                continue
            try:
                locator = self._build_locator(strategy, value)
                await locator.wait_for(state='attached', timeout=probe_timeout)
                element_data['_healed'] = True
                element_data['_healed_locator'] = {
                    'strategy': strategy,
                    'value': value,
                    'note': sug.get('note') or '',
                }
                element_data['_healing_reason'] = failure_reason
                element_data['_candidate_index'] = -1
                logger.info(
                    'AI healed locator for "%s": %s=%s | reason=%s',
                    element_data.get('name'),
                    strategy,
                    value[:80],
                    failure_reason[:120],
                )
                return locator, strategy, value
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    'AI suggested locator failed probe %s=%s: %s',
                    strategy, value[:80], exc,
                )
                continue

        element_data['_healing_reason'] = failure_reason
        element_data['_healed'] = False
        logger.info('AI healer suggestions all failed for "%s"', element_data.get('name'))
        return None

    async def _resolve_locator_with_backups(self, element_data: Dict, timeout_ms: int):
        """主定位器失败时依次尝试备用定位器；全部失败则尝试 AI 自愈，仍失败再抛错。"""
        candidates = self._build_locator_candidates(element_data)
        element_data['_locator_candidates'] = candidates
        # 非自愈路径清理标记
        element_data.pop('_healed', None)
        element_data.pop('_healed_locator', None)
        element_data.pop('_healing_reason', None)

        if not candidates:
            raise PlaywrightTimeout('无可用定位器（主/备用均为空或已过滤）')

        has_backups = len(candidates) > 1
        last_error = None
        for i, cand in enumerate(candidates):
            try:
                locator = self._build_locator(cand['strategy'], cand['value'])
                # 有备用时主定位器短探测，失败再试备用，避免每次空等满超时
                if i == 0:
                    probe_timeout = min(2500, timeout_ms) if has_backups else timeout_ms
                else:
                    probe_timeout = min(2000, max(timeout_ms, 1))
                await locator.wait_for(state='attached', timeout=probe_timeout)
                element_data['_candidate_index'] = i
                if i > 0:
                    logger.info(
                        'primary locator failed, using backup #%s %s=%s',
                        i, cand['strategy'], cand['value'][:80],
                    )
                return locator, cand['strategy'], cand['value']
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue

        # 主/备用均失败 → AI 自愈（仅当次执行，不修改元素/步骤）
        healed = await self._try_ai_heal_locator(
            element_data, candidates, last_error, timeout_ms
        )
        if healed:
            return healed

        tried = self._format_tried_locators(candidates)
        detail = f'{last_error}' if last_error else ''
        heal_reason = element_data.get('_healing_reason')
        heal_note = f'\n  - AI自愈分析: {heal_reason}' if heal_reason else ''
        raise PlaywrightTimeout(
            f'所有定位器均未找到元素（已尝试 {len(candidates)} 个）\n{tried}\n  - 最后错误: {detail}{heal_note}'
        )

    async def _retry_action_on_backups(self, element_data: Dict, timeout_ms: int, action):
        """主定位器已 attached 但操作失败时，继续试后续备用。action(locator) 为 async。"""
        candidates = element_data.get('_locator_candidates') or self._build_locator_candidates(element_data)
        start = int(element_data.get('_candidate_index') or 0) + 1
        last_error = None
        for i in range(start, len(candidates)):
            cand = candidates[i]
            locator = self._build_locator(cand['strategy'], cand['value'])
            try:
                await locator.wait_for(state='attached', timeout=min(2000, max(timeout_ms, 1)))
                await action(locator)
                element_data['_candidate_index'] = i
                logger.info(
                    'action failed on prior locator, using backup #%s %s=%s',
                    i, cand['strategy'], cand['value'][:80],
                )
                return locator, cand['strategy'], cand['value']
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                continue
        return None, last_error

    async def execute_step(self, step, element_data: Dict) -> Tuple[bool, str, Optional[str]]:
        """
        执行单个测试步骤

        Args:
            step: 测试步骤对象
            element_data: 元素数据字典 {locator_strategy, locator_value, name}

        Returns:
            (是否成功, 日志信息, 截图base64)
        """
        action_type = step.action_type
        
        # 预先解析变量
        resolved_input_value = step.input_value
        if step.input_value:
            resolved_input_value = resolve_variables(step.input_value)
            
        resolved_assert_value = step.assert_value
        if step.assert_value:
            resolved_assert_value = resolve_variables(step.assert_value)
            
        start_time = time.time()
        screenshot_base64 = None

        try:
            # wait和screenshot操作不需要元素定位器
            if action_type == 'wait':
                wait_seconds = step.wait_time / 1000 if step.wait_time else 1
                await asyncio.sleep(wait_seconds)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 固定等待 {wait_seconds} 秒完成 - 耗时 {execution_time}秒"
                return True, log, None

            elif action_type == 'navigateUrl':
                if not resolved_input_value:
                    execution_time = round(time.time() - start_time, 2)
                    log = "✗ 跳转URL失败: URL为空"
                    return False, log, None
                await self.page.goto(resolved_input_value, wait_until='domcontentloaded', timeout=30000)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 跳转URL成功\n"
                log += f"  - 目标URL: {resolved_input_value}\n"
                log += f"  - 页面标题: {await self.page.title()}\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, screenshot_base64

            elif action_type == 'screenshot':
                screenshot = await self.page.screenshot()
                screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 截图成功\n"
                log += f"  - 截图范围: 整个页面\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, screenshot_base64

            elif action_type == 'switchTab':
                # 切换标签页
                # 获取超时时间
                if step.wait_time:
                    timeout = step.wait_time / 1000
                else:
                    timeout = 5.0
                
                start_wait = time.time()
                current_page = self.page
                target_index = -1
                
                while True:
                    pages = self.context.pages
                    target_index = -1  # 默认切换到最新标签页
                    should_switch = False
                    
                    if resolved_input_value and str(resolved_input_value).isdigit():
                        # 指定索引的情况
                        idx = int(resolved_input_value)
                        if 0 <= idx < len(pages):
                            target_index = idx
                            should_switch = True
                    else:
                        # 切换到最新的情况
                        target_index = -1
                        # 如果最新的页面不是当前页面，说明有新标签页，或者是切换到其他已存在的标签页
                        if pages[-1] != current_page:
                            should_switch = True
                        # 如果只有一个页面，且就是当前页，可能是在等待新标签页打开
                        elif len(pages) == 1 and pages[0] == current_page:
                            should_switch = False
                        # 如果有多个页面，但最新的就是当前页，可能是想留在当前页，也可能是等待更新的
                        else:
                            should_switch = False

                    if should_switch:
                        break
                    
                    if time.time() - start_wait > timeout:
                        # 超时了，就切换到当前能找到的那个（Best Effort）
                        break
                        
                    await asyncio.sleep(0.5)
                
                # 获取目标页面
                if target_index == -1:
                    target_page = pages[-1]
                    final_target_index = len(pages) - 1
                else:
                    target_page = pages[target_index]
                    final_target_index = target_index

                # 将目标页面设为当前活动页面
                await target_page.bring_to_front()
                # 更新引擎的当前页面引用
                self.page = target_page
                
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 切换标签页成功\n"
                log += f"  - 目标索引: {final_target_index}\n"
                log += f"  - 页面标题: {await self.page.title()}\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, None

            # URL包含断言不需要元素定位器，提前处理
            if action_type == 'assert' and step.assert_type == 'urlContains':
                current_url = self.page.url
                execution_time = round(time.time() - start_time, 2)
                if resolved_assert_value in current_url:
                    log = f"✓ 断言通过: URL包含 '{resolved_assert_value}'\n"
                    log += f"  - 实际URL: '{current_url}'\n"
                    log += f"  - 执行时间: {execution_time}秒"
                    return True, log, None
                else:
                    log = f"✗ 断言失败: URL不包含 '{resolved_assert_value}'\n"
                    log += f"  - 期望包含: '{resolved_assert_value}'\n"
                    log += f"  - 实际URL: '{current_url}'"
                    screenshot = await self.page.screenshot()
                    screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                    return False, log, screenshot_base64

            # 其他操作需要元素定位器
            # 获取元素定位器
            locator_strategy = element_data.get('locator_strategy', 'css')
            locator_value = element_data.get('locator_value', '')
            element_name = element_data.get('name', '未知元素')

            # 获取强制操作选项（用于visibility:hidden的元素）
            force_action = element_data.get('force_action', False)

            # 计算超时时间：优先使用元素的wait_timeout（秒），其次使用步骤的wait_time（毫秒）
            # 如果元素有wait_timeout，转换为毫秒；否则使用步骤的wait_time
            element_wait_timeout = element_data.get('wait_timeout')  # 秒
            if element_wait_timeout is not None and element_wait_timeout > 0:
                timeout_ms = element_wait_timeout * 1000  # 转换为毫秒
            elif step.wait_time:
                timeout_ms = step.wait_time
            else:
                timeout_ms = 5000  # 默认5秒

            # 根据定位策略获取元素（主定位失败时尝试备用）
            locator, locator_strategy, locator_value = await self._resolve_locator_with_backups(
                element_data, timeout_ms
            )

            # 执行操作
            execution_time = 0

            if action_type == 'click':
                # 检测是否是原生HTML select的option元素（优先检测，因为option元素特殊）
                is_native_select_option = (
                    ('option[' in locator_value or ' > option' in locator_value or '//option' in locator_value) or
                    ('select' in locator_value.lower() and 'option' in locator_value.lower())
                )

                # 对于原生HTML select的option，使用select_option方法
                if is_native_select_option:
                    logger.info(f"检测到原生HTML select元素，使用select_option方法...")

                    # 提取select的定位器和option的value
                    # 例如：select[name="my-select"] option[value="1"]
                    # 需要提取：select[name="my-select"] 和 value="1"

                    import re

                    # 提取option的value值
                    option_value_match = re.search(r'option\[value=["\']([^"\']+)["\']\]', locator_value)
                    option_value_xpath_match = re.search(r'option\[@value=["\']([^"\']+)["\']\]', locator_value)

                    option_value = None
                    if option_value_match:
                        option_value = option_value_match.group(1)
                    elif option_value_xpath_match:
                        option_value = option_value_xpath_match.group(1)
                    else:
                        # 尝试其他格式
                        option_value = '1'  # 默认值

                    # 构造select元素的定位器（去掉option部分）
                    select_locator_value = re.sub(r'\s*>\s*option\[.*?\]', '', locator_value)
                    select_locator_value = re.sub(r'\s+option\[.*?\]', '', select_locator_value)
                    select_locator_value = re.sub(r'//option\[.*?\]', '', select_locator_value)

                    logger.info(f"Select定位器: {select_locator_value}, Option值: {option_value}")

                    try:
                        # 构造select元素的locator
                        if locator_strategy.lower() == 'xpath':
                            # XPath: //select[@name='my-select']/option[@value='1']
                            # 提取select部分
                            select_match = re.match(r'^(//.*?select)(?:/option)?', locator_value)
                            if select_match:
                                select_locator_value = select_match.group(1)
                            else:
                                select_locator_value = locator_value.split('/')[0]
                            select_locator = self.page.locator(f"xpath={select_locator_value}")
                        else:
                            # CSS: select[name="my-select"] option[value="1"]
                            select_locator = self.page.locator(select_locator_value)

                        # 使用select_option方法
                        await select_locator.select_option(value=option_value, timeout=timeout_ms)

                        execution_time = round(time.time() - start_time, 2)
                        log = f"✓ 选择下拉框选项 '{element_name}' 成功\n"
                        log += f"  - Select定位器: {select_locator_value}\n"
                        log += f"  - 选中值: {option_value}\n"
                        log += f"  - 方法: select_option() (原生HTML select)\n"
                        log += f"  - 执行时间: {execution_time}秒"
                        return True, log, None

                    except Exception as e:
                        logger.error(f"select_option失败: {e}")
                        # 如果失败，继续尝试普通点击
                        pass

                # 对于下拉框选项，需要特殊处理
                # 通过定位器特征自动识别下拉框选项
                is_dropdown_option = (
                    'dropdown' in locator_value.lower() or
                    'el-select' in locator_value.lower() or
                    '下拉' in element_name or
                    '选项' in element_name or
                    'role="option"' in locator_value.lower() or
                    'el-select-dropdown__item' in locator_value.lower() or  # Element Plus 下拉框
                    ('//li' in locator_value and 'span=' in locator_value)  # XPath 下拉框模式
                )
                
                # 检测是否是点击 el-select 容器（下拉框触发器）
                is_select_trigger = ('el-select' in locator_value.lower() and 
                                    'ancestor::' in locator_value.lower() and
                                    'el-select-dropdown' not in locator_value.lower())
                
                if is_select_trigger:
                    # el-select 容器：点击内部的真正触发器，触发完整事件链
                    logger.info(f"检测到 el-select 容器，使用 Playwright 原生点击...")
                    try:
                        # 等待容器出现
                        await locator.wait_for(state='visible', timeout=timeout_ms)
                        # 点击内部的 wrapper 或 input（使用 Playwright 原生点击，会触发完整事件）
                        wrapper_locator = locator.locator('.el-select__wrapper, input').first
                        await wrapper_locator.click(timeout=timeout_ms, no_wait_after=False)
                        # 等待下拉框展开动画
                        await asyncio.sleep(0.5)
                        
                        execution_time = round(time.time() - start_time, 2)
                        log = f"✓ 点击下拉框触发器 '{element_name}' 成功\n"
                        log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                        log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                        log += f"  - 特殊处理: Playwright原生点击内部触发器 + 等待展开\n"
                        log += f"  - 执行时间: {execution_time}秒"
                        return True, log, None
                    except Exception as e:
                        logger.warning(f"Playwright 点击失败，尝试其他方法: {e}")
                        
                        # 备用方案：使用完整的事件链
                        try:
                            await locator.locator('.el-select__wrapper, input').first.evaluate("""
                                element => {
                                    const events = [
                                        new MouseEvent('mousedown', { bubbles: true, cancelable: true, view: window }),
                                        new MouseEvent('mouseup', { bubbles: true, cancelable: true, view: window }),
                                        new MouseEvent('click', { bubbles: true, cancelable: true, view: window })
                                    ];
                                    events.forEach(event => element.dispatchEvent(event));
                                }
                            """)
                            await asyncio.sleep(0.5)
                            execution_time = round(time.time() - start_time, 2)
                            log = f"✓ 点击下拉框触发器 '{element_name}' 成功（事件链）\n"
                            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                            log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                            log += f"  - 执行时间: {execution_time}秒"
                            return True, log, None
                        except Exception as e2:
                            logger.error(f"所有点击方法都失败: {e2}")
                            raise
                
                elif is_dropdown_option:
                    # 下拉框选项：需要特殊处理，确保能正确触发 Vue/Element Plus 的 v-model 更新
                    logger.info(f"检测到下拉框选项，使用 Playwright + Vue 数据更新策略...")
                    
                    # 等待下拉框完全展开并渲染
                    await asyncio.sleep(0.8)
                    
                    try:
                        # 等待元素在 DOM 中（不要求可见）
                        await locator.wait_for(state='attached', timeout=timeout_ms)
                        logger.info(f"元素已在 DOM 中，执行 Vue 数据更新...")
                        
                        # 策略：直接通过 page.evaluate() 操作，绕过 locator 的 actionability 检查
                        # locator.evaluate() 会等待元素可见，但下拉框选项可能是隐藏的
                        # 所以我们使用 page.evaluate() 并传递定位器表达式
                        
                        # 根据定位策略构造 JavaScript 选择器
                        if locator_strategy.lower() == 'xpath':
                            js_selector_code = f"""
                                const xpath = {repr(locator_value)};
                                const result = document.evaluate(xpath, document, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
                                let element = null;
                                for (let i = 0; i < result.snapshotLength; i++) {{
                                    const node = result.snapshotItem(i);
                                    // 检查可见性: offsetParent 不为 null (且不是 fixed 定位) 或者 getComputedStyle display != none
                                    if (node.offsetParent !== null || window.getComputedStyle(node).display !== 'none') {{
                                        element = node;
                                        break;
                                    }}
                                }}
                            """
                        elif locator_strategy.lower() == 'css selector':
                            js_selector_code = f"""
                                const elements = document.querySelectorAll({repr(locator_value)});
                                let element = null;
                                for (const el of elements) {{
                                    if (el.offsetParent !== null || window.getComputedStyle(el).display !== 'none') {{
                                        element = el;
                                        break;
                                    }}
                                }}
                            """
                        else:
                            # 其他策略：尝试作为 CSS 选择器
                            js_selector_code = f"""
                                const elements = document.querySelectorAll({repr(locator_value)});
                                let element = null;
                                for (const el of elements) {{
                                    if (el.offsetParent !== null || window.getComputedStyle(el).display !== 'none') {{
                                        element = el;
                                        break;
                                    }}
                                }}
                            """
                        
                        # 构造基础定位器（不带 visible=true，因为我们要手动遍历）
                        base_locator_value = locator_value.replace(' >> visible=true', '')
                        
                        if locator_strategy.lower() == 'xpath':
                            if not base_locator_value.startswith('xpath='):
                                candidates = self.page.locator(f"xpath={base_locator_value}")
                            else:
                                candidates = self.page.locator(base_locator_value)
                        elif locator_strategy.lower() == 'css selector':
                            candidates = self.page.locator(base_locator_value)
                        else:
                            # 其他策略暂按 CSS 处理
                            candidates = self.page.locator(base_locator_value)
                        
                        # 获取匹配元素数量
                        count = await candidates.count()
                        logger.info(f"找到 {count} 个匹配元素，开始寻找可见元素...")
                        
                        found_visible = False
                        for i in range(count):
                            candidate = candidates.nth(i)
                            if await candidate.is_visible():
                                logger.info(f"找到第 {i+1} 个元素是可见的，执行点击...")
                                try:
                                    await candidate.click(timeout=timeout_ms)
                                    found_visible = True
                                    method_desc = f"iterative-click(index={i})"
                                    break
                                except Exception as e:
                                    logger.warning(f"点击第 {i+1} 个元素失败: {e}")
                        
                        if not found_visible:
                            logger.warning("未找到可见的下拉框选项元素，尝试点击第一个...")
                            try:
                                await candidates.first.click(force=True, timeout=timeout_ms)
                                method_desc = "fallback-force-click"
                            except Exception as e:
                                logger.error(f"强制点击失败: {e}")
                                raise e

                        # 检查并关闭多选下拉框
                        try:
                            await asyncio.sleep(0.5)
                            dropdown = self.page.locator('.el-select-dropdown').first
                            if await dropdown.is_visible():
                                logger.info(f"多选下拉框未自动关闭，点击空白处关闭...")
                                await self.page.click('body', position={'x': 10, 'y': 10}, timeout=3000)
                                auto_close_msg = " + 自动关闭"
                            else:
                                auto_close_msg = ""
                        except:
                            auto_close_msg = ""
                        
                        execution_time = round(time.time() - start_time, 2)
                        log = f"✓ 点击下拉框选项 '{element_name}' 成功（{method_desc}）\n"
                        log += f"  - 定位器: {locator_strategy}={base_locator_value}\n"
                        log += f"  - 匹配数量: {count}\n"
                        log += f"  - 执行方法: {method_desc}{auto_close_msg}\n"
                        log += f"  - 执行时间: {execution_time}秒"
                        return True, log, None
                        
                        logger.info(f"JS执行结果: {js_result}")
                        
                        # 等待 Vue 响应式更新完成
                        await asyncio.sleep(0.8)
                        
                        # 检查并关闭多选下拉框
                        try:
                            dropdown = self.page.locator('.el-select-dropdown').first
                            if await dropdown.is_visible():
                                logger.info(f"多选下拉框未自动关闭，点击空白处关闭...")
                                await self.page.click('body', position={'x': 10, 'y': 10}, timeout=3000)
                                await asyncio.sleep(0.5)
                                auto_close_msg = " + 自动关闭"
                            else:
                                auto_close_msg = ""
                        except:
                            auto_close_msg = ""
                        
                        execution_time = round(time.time() - start_time, 2)
                        method_desc = js_result.get('method', 'unknown') if isinstance(js_result, dict) else 'unknown'
                        log = f"✓ 点击下拉框选项 '{element_name}' 成功（{method_desc})\n"
                        log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                        log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                        log += f"  - 更新方法: {method_desc}{auto_close_msg}\n"
                        if isinstance(js_result, dict) and 'allValues' in js_result:
                            log += f"  - 当前选中值: {js_result['allValues']}\n"
                        log += f"  - 执行时间: {execution_time}秒"
                        return True, log, None
                    except Exception as e:
                        logger.error(f"下拉框选项点击失败: {e}")
                        execution_time = round(time.time() - start_time, 2)

                        # 构建详细的错误日志
                        error_log = f"✗ 点击下拉框选项 '{element_name}' 失败\n"
                        error_log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                        error_log += f"  - 执行时间: {execution_time}秒\n"
                        error_log += f"  - 错误: {str(e)}\n\n"
                        error_log += "建议解决方案:\n"
                        error_log += "1. 检查元素是否在下拉框展开后才出现在 DOM 中\n"
                        error_log += "2. 尝试在点击下拉框后增加等待时间（添加 wait 步骤，等待2000ms）\n"
                        error_log += "3. 使用 Playwright get_by_text 定位：文本=无忧行-鸿蒙APP\n"
                        error_log += "4. 检查 Vue DevTools 确认组件结构是否与代码匹配"

                        # 尝试捕获截图
                        screenshot_base64 = None
                        try:
                            screenshot = await self.page.screenshot()
                            screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        except:
                            pass

                        # 返回: (是否成功, 日志信息, 截图base64)
                        return False, error_log, screenshot_base64
                else:
                    # 普通元素：正常点击
                    # 登录弹窗等遮罩会拦截 pointer events，先尝试关闭
                    await self._dismiss_blocking_overlays()

                    collect_target = self._collect_link_target(element_name, locator_value)
                    if collect_target:
                        ok, detail = await self._click_collect_link(
                            collect_target, timeout_ms, force_action=force_action
                        )
                        execution_time = round(time.time() - start_time, 2)
                        if ok:
                            log = f"✓ 点击元素 '{element_name}' 成功\n"
                            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                            log += f"  - 收藏处理: {detail}\n"
                            log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                            log += f"  - 执行时间: {execution_time}秒"
                            return True, log, None
                        error_log = f"✗ 操作超时\n  - 元素: '{element_name}'\n"
                        error_log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                        error_log += f"  - 超时时间: {timeout_ms/1000}秒\n"
                        error_log += f"  - 错误: {detail}\n"
                        screenshot_base64 = None
                        try:
                            screenshot = await self.page.screenshot()
                            screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        except Exception:
                            pass
                        return False, error_log, screenshot_base64

                    # 商品列表入口：点击成功不等于已进详情，需确认 URL / 控件
                    if self._is_goods_entry_locator(locator_value):
                        ok, detail = await self._click_goods_entry(
                            locator, timeout_ms, force_action=force_action
                        )
                        execution_time = round(time.time() - start_time, 2)
                        if ok:
                            log = f"✓ 点击元素 '{element_name}' 成功\n"
                            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                            log += f"  - 商品跳转: {detail}\n"
                            log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                            log += f"  - 执行时间: {execution_time}秒"
                            return True, log, None
                        error_log = f"✗ 点击商品未进入详情\n  - 元素: '{element_name}'\n"
                        error_log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                        error_log += f"  - 错误: {detail}\n"
                        screenshot_base64 = None
                        try:
                            screenshot = await self.page.screenshot()
                            screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        except Exception:
                            pass
                        return False, error_log, screenshot_base64

                    # 如果启用了强制操作，先等待元素在 DOM 中，不要求可见
                    if force_action:
                        try:
                            await locator.wait_for(state='attached', timeout=timeout_ms)
                        except:
                            pass  # 如果已经在 DOM 中，继续

                    async def _do_click(loc):
                        if force_action:
                            try:
                                await loc.wait_for(state='attached', timeout=min(2000, timeout_ms))
                            except Exception:  # noqa: BLE001
                                pass
                        await loc.click(timeout=timeout_ms, force=force_action)

                    try:
                        await _do_click(locator)
                    except Exception:
                        nxt, _ = await self._retry_action_on_backups(
                            element_data, timeout_ms, _do_click
                        )
                        if not nxt:
                            raise
                        locator, locator_strategy, locator_value = nxt

                    execution_time = round(time.time() - start_time, 2)
                    log = f"✓ 点击元素 '{element_name}' 成功\n"
                    log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                    log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                    if force_action:
                        log += f"  - 强制操作: 是（跳过可见性检查，等待attached）\n"
                    log += f"  - 执行时间: {execution_time}秒"
                    return True, log, None

            elif action_type == 'fill':
                async def _do_fill(loc):
                    await loc.fill(resolved_input_value, timeout=timeout_ms, force=force_action)

                try:
                    await _do_fill(locator)
                except Exception:
                    nxt, _ = await self._retry_action_on_backups(
                        element_data, timeout_ms, _do_fill
                    )
                    if not nxt:
                        raise
                    locator, locator_strategy, locator_value = nxt
                execution_time = round(time.time() - start_time, 2)

                # 输入成功后短暂等待，确保表单验证生效
                # 特别是在服务器环境下，需要给Vue/React等框架时间处理
                await asyncio.sleep(0.3)

                log = f"✓ 在元素 '{element_name}' 中输入文本成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                if resolved_input_value != step.input_value:
                    log += f"  - 变量解析: '{step.input_value}' => '{resolved_input_value}'\n"
                log += f"  - 输入内容: '{resolved_input_value}'\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                if force_action:
                    log += f"  - 强制操作: 是（忽略可见性检查）\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, None

            elif action_type == 'getText':
                text = await locator.inner_text(timeout=timeout_ms)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 获取元素 '{element_name}' 的文本成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                log += f"  - 文本内容: '{text}'\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, None

            elif action_type == 'waitFor':
                await locator.wait_for(state='visible', timeout=timeout_ms)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 等待元素 '{element_name}' 出现成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                log += f"  - 等待时间: {execution_time}秒"
                return True, log, None

            elif action_type == 'hover':
                await locator.hover(timeout=timeout_ms, force=force_action)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 在元素 '{element_name}' 上悬停成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                if force_action:
                    log += f"  - 强制操作: 是（忽略可见性检查）\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, None

            elif action_type == 'scroll':
                await locator.scroll_into_view_if_needed(timeout=timeout_ms)
                execution_time = round(time.time() - start_time, 2)
                log = f"✓ 滚动到元素 '{element_name}' 成功\n"
                log += f"  - 定位器: {locator_strategy}={locator_value}\n"
                log += f"  - 超时设置: {timeout_ms/1000}秒\n"
                log += f"  - 执行时间: {execution_time}秒"
                return True, log, None

            elif action_type == 'assert':
                # 根据断言类型执行不同的断言
                # 注意：urlContains 已在元素定位器之前提前处理
                if step.assert_type == 'textContains':
                    text = await locator.inner_text(timeout=timeout_ms)
                    if resolved_assert_value in text:
                        log = f"✓ 断言通过: 文本包含 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                             log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 实际文本: '{text}'\n"
                        log += f"  - 超时设置: {timeout_ms/1000}秒"
                        return True, log, None
                    else:
                        log = f"✗ 断言失败: 文本不包含 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                             log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 实际文本: '{text}'"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64

                elif step.assert_type == 'textEquals':
                    text = await locator.inner_text(timeout=timeout_ms)
                    if text == resolved_assert_value:
                        log = f"✓ 断言通过: 文本等于 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                             log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 超时设置: {timeout_ms/1000}秒"
                        return True, log, None
                    else:
                        log = f"✗ 断言失败: 文本不等于 '{resolved_assert_value}'\n"
                        if resolved_assert_value != step.assert_value:
                             log += f"  - 变量解析: '{step.assert_value}' => '{resolved_assert_value}'\n"
                        log += f"  - 期望: '{resolved_assert_value}'\n"
                        log += f"  - 实际: '{text}'"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64

                elif step.assert_type == 'isVisible':
                    is_visible = await locator.is_visible()
                    if is_visible:
                        log = f"✓ 断言通过: 元素 '{element_name}' 可见"
                        return True, log, None
                    else:
                        log = f"✗ 断言失败: 元素 '{element_name}' 不可见"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64

                elif step.assert_type == 'exists':
                    count = await locator.count()
                    if count > 0:
                        log = f"✓ 断言通过: 元素 '{element_name}' 存在"
                        return True, log, None
                    else:
                        log = f"✗ 断言失败: 元素 '{element_name}' 不存在"
                        screenshot = await self.page.screenshot()
                        screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
                        return False, log, screenshot_base64



            else:
                log = f"⚠ 未知的操作类型: {action_type}"
                return True, log, None

        except PlaywrightTimeout as e:
            execution_time = round(time.time() - start_time, 2)
            log = f"✗ 操作超时\n"
            log += f"  - 元素: '{element_name}'\n"
            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
            log += f"  - 超时时间: {execution_time}秒\n"
            tried = self._format_tried_locators(element_data.get('_locator_candidates') or [])
            if tried and '已尝试定位器' not in str(e):
                log += f"{tried}\n"
            log += f"  - 错误: {str(e)}"

            # 捕获失败截图
            try:
                screenshot = await self.page.screenshot()
                screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
            except:
                pass

            return False, log, screenshot_base64

        except Exception as e:
            execution_time = round(time.time() - start_time, 2)
            log = f"✗ 执行失败\n"
            log += f"  - 元素: '{element_name}'\n"
            log += f"  - 定位器: {locator_strategy}={locator_value}\n"
            log += f"  - 执行时间: {execution_time}秒\n"
            tried = self._format_tried_locators(element_data.get('_locator_candidates') or [])
            if tried and '已尝试定位器' not in str(e):
                log += f"{tried}\n"
            log += f"  - 错误: {str(e)}"

            # 捕获失败截图
            try:
                screenshot = await self.page.screenshot()
                screenshot_base64 = f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
            except:
                pass

            return False, log, screenshot_base64

    async def navigate(self, url: str) -> Tuple[bool, str]:
        """
        导航到指定URL

        Args:
            url: 目标URL

        Returns:
            (是否成功, 日志信息)
        """
        try:
            # 检测是否在Linux服务器环境
            import platform
            is_linux = platform.system() == 'Linux'

            # 使用 domcontentloaded 等待页面DOM加载完成，避免networkidle在SPA应用上超时
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)

            # 额外等待，确保动态内容加载（Vue/React等SPA应用）
            # 服务器无头模式需要更长的等待时间
            extra_wait = 3 if is_linux else 2
            await asyncio.sleep(extra_wait)

            log = f"✓ 成功导航到: {url}\n"
            log += f"  - 等待页面加载完成（domcontentloaded + 额外{extra_wait}秒）"
            return True, log
        except Exception as e:
            log = f"✗ 导航失败: {url}\n  - 错误: {str(e)}"
            return False, log

    async def capture_screenshot(self) -> str:
        """
        捕获当前页面截图

        Returns:
            截图的base64字符串
        """
        try:
            screenshot = await self.page.screenshot(full_page=True)
            return f"data:image/png;base64,{base64.b64encode(screenshot).decode()}"
        except Exception as e:
            logger.error(f"捕获截图失败: {str(e)}")
            return None
