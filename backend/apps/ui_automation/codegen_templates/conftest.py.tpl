"""pytest + Playwright 公共 fixture（含 Trace → pytest-html 挂载）。

含图形验证码 / 需登录态时：按 reference.md 启用 _ensure_auth_state + authenticated_page。
登录页类名、首页路径、locator 一律由 Phase 4 按录制填写，勿在本模板写死业务。
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from playwright.sync_api import Browser, Page

from tests.helpers.trace_support import (
    find_trace_for_nodeid,
    is_tracing_enabled,
    resolve_output_dir,
    start_tracing,
    stop_and_save_trace,
    trace_viewer_url,
)

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
AUTH_FILE = Path(__file__).resolve().parent / "fixtures" / "auth.json"


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)

    if rep.when == "teardown":
        _attach_trace_to_html(item)


def _attach_trace_to_html(item) -> None:
    target = getattr(item, "rep_call", None) or getattr(item, "rep_setup", None)
    if target is None:
        return

    output_dir = resolve_output_dir(item.config)
    trace_path = getattr(item, "_trace_path", None)
    if trace_path is None:
        trace_path = find_trace_for_nodeid(output_dir, item.nodeid)
    if not trace_path or not Path(trace_path).exists():
        return

    trace_path = Path(trace_path)
    try:
        from pytest_html import extras
    except ImportError:
        return

    url = trace_viewer_url(trace_path, PROJECT_ROOT)
    existing = list(getattr(target, "extras", []) or [])
    if any(getattr(e, "val", None) == url for e in existing):
        return
    try:
        rel = str(trace_path.resolve().relative_to(PROJECT_ROOT.resolve()))
    except ValueError:
        rel = str(trace_path)
    target.extras = existing + [
        extras.url(url, name="Open Trace Viewer"),
        extras.text(rel, name="trace.zip path"),
    ]


@pytest.fixture(scope="session")
def base_url() -> str:
    return os.getenv("BASE_URL", "http://localhost:3000")


@pytest.fixture(scope="session")
def browser_type_launch_args() -> dict:
    # CAPTCHA_MODE=manual 必须有头
    if (os.getenv("CAPTCHA_MODE") or "ocr").strip().lower() == "manual":
        return {"headless": False}
    headless = os.getenv("HEADLESS", "true").lower() != "false"
    return {"headless": headless}


@pytest.fixture(scope="session")
def credentials() -> dict[str, str]:
    return {
        "username": os.getenv("TEST_USERNAME", ""),
        "password": os.getenv("TEST_PASSWORD", ""),
        "captcha": os.getenv("TEST_CAPTCHA", ""),
    }


# ---------------------------------------------------------------------------
# 可选：会话登录 → auth.json → authenticated_page（含验证码时启用）
# Agent 生成时：按录制填入 Login Page 类、goto、login_with_retry、登录后 URL。
# 示例骨架见 reference.md「图形验证码」；禁止在此模板写死业务 locator。
# ---------------------------------------------------------------------------


@pytest.fixture
def logged_in_page(
    browser: Browser,
    base_url: str,
    request: pytest.FixtureRequest,
    pytestconfig: pytest.Config,
) -> Page:
    """带 storage_state 的已登录页；自定义 context 必须手动启停 tracing。"""
    if not AUTH_FILE.exists():
        pytest.skip(
            "缺少 tests/fixtures/auth.json。"
            "请启用会话登录 fixture，或 codegen --save-storage。"
        )

    tracing_option = pytestconfig.getoption("--tracing")
    context = browser.new_context(storage_state=str(AUTH_FILE))
    if is_tracing_enabled(tracing_option):
        start_tracing(context, request.node.nodeid)

    page = context.new_page()
    page.goto(base_url)
    # TODO: 按场景导航到业务入口并 expect 就绪
    yield page

    rep_call = getattr(request.node, "rep_call", None)
    failed = bool(rep_call and rep_call.failed)
    if is_tracing_enabled(tracing_option):
        trace_path = stop_and_save_trace(
            context,
            nodeid=request.node.nodeid,
            output_dir=resolve_output_dir(pytestconfig),
            tracing_option=tracing_option,
            failed=failed,
        )
        if trace_path:
            request.node._trace_path = trace_path
    context.close()
