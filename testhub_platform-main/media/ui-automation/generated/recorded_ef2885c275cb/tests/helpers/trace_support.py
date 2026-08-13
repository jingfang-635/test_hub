"""自定义 BrowserContext 的 Trace 启停（对齐 pytest-playwright 行为）。"""

from __future__ import annotations

import os
import re
from pathlib import Path

from playwright.sync_api import BrowserContext

# 与 scripts/open-report.sh 默认端口一致；HTML 报告内 Trace 链接依赖该 HTTP 源
REPORT_ORIGIN = os.getenv("REPORT_ORIGIN", "http://127.0.0.1:9323")
TRACE_VIEWER_BASE = "https://trace.playwright.dev/?trace="


def _slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^\w\s-]", "-", value)
    value = re.sub(r"[-\s]+", "-", value).strip("-")
    return value[:200] or "test"


def start_tracing(context: BrowserContext, title: str) -> None:
    context.tracing.start(
        title=_slugify(title),
        screenshots=True,
        snapshots=True,
        sources=True,
    )


def stop_and_save_trace(
    context: BrowserContext,
    *,
    nodeid: str,
    output_dir: str,
    tracing_option: str,
    failed: bool,
) -> Path | None:
    """停止 tracing；在 on 或失败保留模式下写入 test-results/<slug>/trace.zip。"""
    should_save = tracing_option == "on" or (
        failed and tracing_option == "retain-on-failure"
    )
    if not should_save:
        context.tracing.stop()
        return None

    folder = Path(output_dir) / _slugify(nodeid)
    folder.mkdir(parents=True, exist_ok=True)
    trace_path = folder / "trace.zip"
    context.tracing.stop(path=str(trace_path))
    return trace_path


def is_tracing_enabled(tracing_option: str) -> bool:
    return tracing_option in ("on", "retain-on-failure")


def resolve_output_dir(pytestconfig) -> str:
    return pytestconfig.getoption("--output", default="test-results")


def find_trace_for_nodeid(output_dir: str, nodeid: str) -> Path | None:
    """查找用例对应的 trace.zip（兼容自定义 slug 与 pytest-playwright slugify）。"""
    root = Path(output_dir)
    if not root.exists():
        return None

    candidates: list[Path] = [root / _slugify(nodeid) / "trace.zip"]
    try:
        from slugify import slugify

        candidates.append(root / slugify(nodeid)[:200] / "trace.zip")
    except ImportError:
        pass

    for path in candidates:
        if path.exists():
            return path

    # 模糊：目录名包含测试函数名
    func = nodeid.split("::")[-1].split("[")[0].lower().replace("_", "-")
    for path in root.rglob("trace.zip"):
        folder = path.parent.name.lower()
        if func and func in folder.replace("_", "-"):
            return path
    return None


def trace_viewer_url(trace_path: Path, project_root: Path | None = None) -> str:
    """生成可在浏览器打开的 Trace Viewer URL（需先 scripts/open-report.sh 起本地服务）。"""
    root = project_root or Path.cwd()
    try:
        rel = trace_path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        rel = trace_path.as_posix()
    return f"{TRACE_VIEWER_BASE}{REPORT_ORIGIN.rstrip('/')}/{rel}"
