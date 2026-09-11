"""项目级 Playwright storage_state 复用（录制/执行共用）。

文件：MEDIA_ROOT/ui-automation/auth/project_{id}.json
过期：mtime TTL（默认 24h，环境变量 AUTH_STATE_TTL_HOURS）。
缺失或会话失效时：ensure_project_auth_state 静默 headless 登录并覆盖保存。
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_TTL_HOURS = 24.0

# 常见登录入口 / 表单文案（含柠檬商城等国内站）
_LOGIN_ENTRY_NAMES = ('登录', 'Login', 'Sign in', 'Sign In', '登 录')
_USER_FIELD_NAMES = (
    '请输入手机号/用户名',
    '手机号/用户名',
    '请输入用户名',
    '请输入账号',
    '请输入手机号',
    '用户名',
    '账号',
    '手机号',
    '手机',
    'Username',
    'Email',
    'email',
    'Account',
)
_SUBMIT_NAMES = ('登录', 'Login', 'Sign in', 'Sign In', '登 录', '提交', 'Submit')
_PASSWORD_FIELD_NAMES = (
    '请输入密码',
    '密码',
    'Password',
    'password',
    '口令',
)


def ttl_hours() -> float:
    try:
        return float(os.environ.get('AUTH_STATE_TTL_HOURS', DEFAULT_TTL_HOURS))
    except (TypeError, ValueError):
        return DEFAULT_TTL_HOURS


def auth_dir() -> Path:
    try:
        from django.conf import settings

        root = Path(settings.MEDIA_ROOT) / 'ui-automation' / 'auth'
    except Exception:  # noqa: BLE001
        root = Path(__file__).resolve().parents[3] / 'media' / 'ui-automation' / 'auth'
    root.mkdir(parents=True, exist_ok=True)
    return root


def auth_path_for_project(project_id: int | str | None) -> Path | None:
    if project_id is None or project_id == '':
        return None
    try:
        pid = int(project_id)
    except (TypeError, ValueError):
        return None
    if pid <= 0:
        return None
    return auth_dir() / f'project_{pid}.json'


def is_fresh(path: Path | str | None) -> bool:
    if not path:
        return False
    p = Path(path)
    try:
        if not p.is_file() or p.stat().st_size < 20:
            return False
        age_h = (time.time() - p.stat().st_mtime) / 3600.0
        return age_h < ttl_hours()
    except OSError:
        return False


def load_path_if_fresh(path: Path | str | None) -> str | None:
    """返回可传给 new_context(storage_state=...) 的路径，否则 None。"""
    if path and is_fresh(path):
        return str(path)
    return None


def load_path_if_exists(path: Path | str | None) -> str | None:
    """文件存在即返回路径（不看 TTL），用于「仅复用、不登录」场景。"""
    if not path:
        return None
    p = Path(path)
    try:
        if p.is_file() and p.stat().st_size >= 20:
            return str(p)
    except OSError:
        return None
    return None


def invalidate(path: Path | str | None) -> None:
    if not path:
        return
    p = Path(path)
    try:
        if p.is_file():
            p.unlink()
    except OSError:
        pass


async def save_storage_state(context: Any, path: Path | str | None) -> bool:
    if not context or not path:
        return False
    p = Path(path)
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        await context.storage_state(path=str(p))
        return True
    except Exception:  # noqa: BLE001
        return False


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


async def _visible_password(page: Any) -> Any | None:
    loc = page.locator('input[type="password"]')
    count = await loc.count()
    for i in range(count):
        item = loc.nth(i)
        try:
            if await item.is_visible():
                return item
        except Exception:  # noqa: BLE001
            continue
    return None


async def _find_password_field(page: Any) -> Any | None:
    """兼容 type=password 与柠檬商城一类 role=textbox 的密码框。"""
    pwd = await _visible_password(page)
    if pwd is not None:
        return pwd
    for name in _PASSWORD_FIELD_NAMES:
        loc = page.get_by_role('textbox', name=name)
        try:
            if await loc.count() == 0:
                continue
            target = loc.first
            if await target.is_visible():
                return target
        except Exception:  # noqa: BLE001
            continue
    return None


async def _click_login_entry(page: Any) -> bool:
    """打开登录入口：优先点第一个「登录」链接（导航），避免点到表单提交。"""
    for role in ('link', 'button'):
        for name in _LOGIN_ENTRY_NAMES:
            loc = page.get_by_role(role, name=name)
            try:
                if await loc.count() == 0:
                    continue
                target = loc.first
                if await target.is_visible():
                    await target.click(timeout=3000)
                    return True
            except Exception:  # noqa: BLE001
                continue
    return False


async def _click_login_submit(page: Any) -> bool:
    """提交登录：多个「登录」时点最后一个（表单按钮/链接）。"""
    for role in ('button', 'link'):
        for name in _SUBMIT_NAMES:
            loc = page.get_by_role(role, name=name)
            try:
                n = await loc.count()
                if n == 0:
                    continue
                target = loc.nth(n - 1)
                if await target.is_visible():
                    await target.click(timeout=3000)
                    return True
            except Exception:  # noqa: BLE001
                continue
    return False


async def _fill_username(page: Any, username: str) -> bool:
    for name in _USER_FIELD_NAMES:
        loc = page.get_by_role('textbox', name=name)
        try:
            if await loc.count() == 0:
                continue
            target = loc.first
            if await target.is_visible():
                await target.fill(username)
                return True
        except Exception:  # noqa: BLE001
            continue

    for selector in (
        'input[type="text"]:visible',
        'input[type="tel"]:visible',
        'input[type="email"]:visible',
        'input:not([type]):visible',
    ):
        loc = page.locator(selector)
        try:
            if await loc.count() == 0:
                continue
            await loc.first.fill(username)
            return True
        except Exception:  # noqa: BLE001
            continue
    return False


async def try_auto_login(page: Any, username: str, password: str, timeout_ms: int = 15000) -> bool:
    """用项目账号填写登录表单；失败返回 False，不抛异常。"""
    username = (username or '').strip()
    password = password or ''
    if not username or not password:
        return False

    try:
        await page.wait_for_load_state('domcontentloaded', timeout=timeout_ms)
    except Exception:  # noqa: BLE001
        pass

    try:
        pwd = await _find_password_field(page)
        if pwd is None:
            opened = await _click_login_entry(page)
            if opened:
                try:
                    await page.get_by_role('textbox', name='请输入手机号/用户名').first.wait_for(
                        state='visible', timeout=5000,
                    )
                except Exception:  # noqa: BLE001
                    await page.wait_for_timeout(800)
                pwd = await _find_password_field(page)

        if pwd is None:
            return False

        if not await _fill_username(page, username):
            return False

        await pwd.fill(password)

        submitted = await _click_login_submit(page)
        if not submitted:
            try:
                await pwd.press('Enter')
                submitted = True
            except Exception:  # noqa: BLE001
                submitted = False

        if not submitted:
            return False

        try:
            await page.get_by_role('textbox', name='请输入密码').first.wait_for(
                state='hidden', timeout=8000,
            )
        except Exception:  # noqa: BLE001
            try:
                await page.wait_for_load_state('networkidle', timeout=timeout_ms)
            except Exception:  # noqa: BLE001
                await page.wait_for_timeout(1000)

        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning('try_auto_login failed: %s', exc)
        return False


async def looks_logged_out(page: Any) -> bool:
    """粗判当前页是否未登录：密码框可见，或顶栏仍有登录入口。"""
    try:
        if await _find_password_field(page) is not None:
            return True
    except Exception:  # noqa: BLE001
        pass
    for role in ('link', 'button'):
        for name in _LOGIN_ENTRY_NAMES:
            loc = page.get_by_role(role, name=name)
            try:
                if await loc.count() == 0:
                    continue
                if await loc.first.is_visible():
                    return True
            except Exception:  # noqa: BLE001
                continue
    return False


async def _ensure_auth_async(
    auth_path: Path,
    base_url: str,
    username: str,
    password: str,
) -> str | None:
    from playwright.async_api import async_playwright

    storage = load_path_if_exists(auth_path)
    target = _normalize_url(base_url)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            ctx_opts: dict[str, Any] = {}
            if storage:
                ctx_opts['storage_state'] = storage
            context = await browser.new_context(**ctx_opts)
            page = await context.new_page()

            if target:
                try:
                    await page.goto(target, wait_until='domcontentloaded', timeout=30000)
                except Exception as exc:  # noqa: BLE001
                    logger.warning('ensure auth goto failed: %s', exc)

            need_login = not storage
            if storage and target:
                try:
                    need_login = await looks_logged_out(page)
                except Exception:  # noqa: BLE001
                    need_login = True
            elif storage and not target:
                # 无 URL 无法探测，信任已有文件
                return storage

            if not need_login:
                await save_storage_state(context, auth_path)
                logger.info('ensure auth: valid existing state path=%s', auth_path)
                return str(auth_path)

            if not username or not password:
                logger.warning('ensure auth: logged out / missing state, no credentials')
                return storage

            if not target:
                logger.warning('ensure auth: need login but no base_url')
                return storage

            ok = await try_auto_login(page, username, password)
            if ok:
                saved = await save_storage_state(context, auth_path)
                logger.info('ensure auth: silent login saved=%s path=%s', saved, auth_path)
                return str(auth_path) if saved else storage

            logger.warning('ensure auth: silent login failed path=%s', auth_path)
            return storage
        finally:
            await browser.close()


def ensure_project_auth_state(
    project_id: int | str | None,
    base_url: str = '',
    username: str = '',
    password: str = '',
) -> str | None:
    """确保项目登录态可用；缺失或失效时 headless 静默登录并覆盖保存。

    录制/运行启动前调用；浏览器会话本身只注入 storage_state，不再表单登录。
    """
    path = auth_path_for_project(project_id)
    if not path:
        return None

    username = (username or '').strip()
    password = password or ''
    base_url = (base_url or '').strip()
    existing = load_path_if_exists(path)

    if existing and not base_url:
        return existing
    if not existing and not (username and password and base_url):
        return existing

    try:
        return asyncio.run(_ensure_auth_async(path, base_url, username, password))
    except Exception as exc:  # noqa: BLE001
        logger.warning('ensure_project_auth_state failed: %s', exc)
        return load_path_if_exists(path)


def auth_status_for_hub_project(hub_project_id: int | str | None) -> dict[str, Any]:
    """主项目环境下的登录态是否已保存（按关联 UiProject 的 auth 文件）。"""
    empty: dict[str, Any] = {'auth_state_saved': False, 'auth_state_updated_at': None}
    if hub_project_id is None or hub_project_id == '':
        return empty
    try:
        hid = int(hub_project_id)
    except (TypeError, ValueError):
        return empty
    try:
        from .models import UiProject

        ui = UiProject.objects.filter(hub_project_id=hid).only('id').first()
        if not ui:
            return empty
        path = auth_path_for_project(ui.id)
        existing = load_path_if_exists(path)
        if not existing:
            return empty
        mtime = Path(existing).stat().st_mtime
        from datetime import datetime

        return {
            'auth_state_saved': True,
            'auth_state_updated_at': datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S'),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning('auth_status_for_hub_project failed: %s', exc)
        return empty


_LOGIN_STEP_KEYWORDS = (
    '登录', '登 录', '密码', '用户名', '账号', '手机号',
    'username', 'password', 'signin', 'sign in', 'sign-in', 'login',
    '请输入密码', '请输入手机号', '请输入用户名', '请输入账号',
    '请输入手机号/用户名', '口令',
)


def is_login_related_step(step_data: dict[str, Any] | None) -> bool:
    """判断用例步骤是否属于登录流程（复用登录态时应跳过）。"""
    if not step_data:
        return False
    ed = step_data.get('element_data') or {}
    parts = [
        step_data.get('description') or '',
        step_data.get('input_value') or '',
        ed.get('name') or '',
        ed.get('locator_value') or '',
    ]
    blob = ' '.join(str(p) for p in parts)
    blob_l = blob.lower()
    for kw in _LOGIN_STEP_KEYWORDS:
        if kw.lower() in blob_l or kw in blob:
            return True
    loc = (ed.get('locator_value') or '').lower()
    if 'type="password"' in loc or "type='password'" in loc:
        return True
    if (ed.get('locator_strategy') or '').lower() in ('password',):
        return True
    return False


if __name__ == '__main__':
    # ponytail: 无浏览器自检，只校验路径与关键词
    assert auth_path_for_project(1).name == 'project_1.json'
    assert is_login_related_step({'description': '输入密码', 'element_data': {}})
    assert not is_login_related_step({'description': '点击搜索', 'element_data': {}})
    assert '请输入手机号/用户名' in _USER_FIELD_NAMES
    print('auth_state selfcheck ok')
