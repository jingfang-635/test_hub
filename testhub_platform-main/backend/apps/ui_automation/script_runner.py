"""
直接运行 TestScript（代码脚本）并写入 TestExecution。

支持：
- Python + Playwright 的 pytest 风格（def test_*(page)）
- Python 独立脚本（含 sync_playwright / 可直接 python 执行）
- JavaScript + Playwright（@playwright/test 或可 node 执行的脚本）
"""
from __future__ import annotations

import importlib.util
import inspect
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from typing import Any, Callable

from django.db import connection
from django.utils import timezone

from .models import TestExecution, TestScript

logger = logging.getLogger(__name__)

# 与 playwright_engine / test_executor 保持一致
os.environ.setdefault(
    'PLAYWRIGHT_BROWSERS_PATH',
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        'ms-playwright',
    ),
)

BROWSER_LAUNCH_MAP = {
    'chrome': 'chromium',
    'chromium': 'chromium',
    'firefox': 'firefox',
    'webkit': 'webkit',
    'safari': 'webkit',
    'edge': 'chromium',
}

ENV_MAP = {
    'chrome': 'CHROME',
    'chromium': 'CHROME',
    'firefox': 'FIREFOX',
    'webkit': 'SAFARI',
    'safari': 'SAFARI',
    'edge': 'EDGE',
}


class ScriptRunner:
    def __init__(
        self,
        script: TestScript,
        browser: str = 'chrome',
        headless: bool = False,
        executed_by=None,
        timeout: int = 600,
    ):
        self.script = script
        self.browser = (browser or 'chrome').lower()
        self.headless = bool(headless)
        self.executed_by = executed_by
        self.timeout = timeout
        self.execution: TestExecution | None = None
        self.work_dir: Path | None = None

    def create_execution_record(self) -> TestExecution:
        self.execution = TestExecution.objects.create(
            project=self.script.project,
            test_script=self.script,
            status='RUNNING',
            environment=ENV_MAP.get(self.browser, 'CHROME'),
            engine=self.script.framework or 'playwright',
            browser=self.browser,
            headless=self.headless,
            executed_by=self.executed_by,
            started_at=timezone.now(),
            total_cases=1,
        )
        return self.execution

    def update_execution_result(
        self,
        status: str,
        *,
        passed: int = 0,
        failed: int = 0,
        skipped: int = 0,
        duration: float = 0,
        error_msg: str = '',
        result_data: dict | None = None,
    ) -> None:
        if not self.execution:
            return
        self.execution.status = status
        self.execution.passed_cases = passed
        self.execution.failed_cases = failed
        self.execution.skipped_cases = skipped
        self.execution.total_cases = max(passed + failed + skipped, 1)
        self.execution.duration = duration
        self.execution.error_message = (error_msg or '')[:5000]
        self.execution.result_data = result_data or {}
        self.execution.finished_at = timezone.now()
        self.execution.save()

    def run(self) -> TestExecution:
        start = time.time()
        try:
            if not self.execution:
                self.create_execution_record()
            content = (self.script.content or '').strip()
            if not content:
                raise ValueError('脚本内容为空，无法执行')

            language = (self.script.language or 'python').lower()
            framework = (self.script.framework or 'playwright').lower()

            if language == 'python':
                result = self._run_python(content, framework)
            elif language in ('javascript', 'typescript'):
                result = self._run_javascript(content)
            else:
                raise ValueError(f'暂不支持的脚本语言: {language}')

            duration = time.time() - start
            status = 'SUCCESS' if result.get('success') else 'FAILED'
            self.update_execution_result(
                status,
                passed=result.get('passed', 0),
                failed=result.get('failed', 0),
                skipped=result.get('skipped', 0),
                duration=duration,
                error_msg=result.get('error', ''),
                result_data={
                    'test_cases': result.get('test_cases', []),
                    'logs': result.get('logs', ''),
                    'stdout': result.get('stdout', ''),
                    'stderr': result.get('stderr', ''),
                },
            )
            return self.execution
        except Exception as exc:
            logger.exception('脚本执行失败: script_id=%s', self.script.id)
            duration = time.time() - start
            if self.execution:
                self.update_execution_result(
                    'FAILED',
                    failed=1,
                    duration=duration,
                    error_msg=f'{exc}\n\n{traceback.format_exc()}',
                    result_data={
                        'test_cases': [{
                            'name': self.script.name,
                            'status': 'failed',
                            'error': str(exc),
                        }],
                    },
                )
            return self.execution
        finally:
            self._cleanup()
            connection.close()

    def _cleanup(self) -> None:
        # 仅清理临时目录；工程化 generated/ 目录不可删
        if self.work_dir and self.work_dir.exists():
            if 'generated' not in self.work_dir.parts:
                shutil.rmtree(self.work_dir, ignore_errors=True)
            self.work_dir = None

    def _ensure_work_dir(self) -> Path:
        if not self.work_dir:
            self.work_dir = Path(tempfile.mkdtemp(prefix=f'ui_script_{self.script.id}_'))
        return self.work_dir

    def _run_python(self, content: str, framework: str) -> dict[str, Any]:
        project_root = self._resolve_generated_project_root(content)
        if project_root or self._needs_tests_package(content):
            if not project_root:
                raise RuntimeError(
                    '脚本依赖 tests 包，但未找到对应的工程化目录 '
                    f'(media/ui-automation/generated/<scenario>/)。'
                    '请确认该脚本由 Codegen 流水线 Phase4 生成，且生成文件仍在磁盘上。'
                )
            return self._run_python_playwright_pytest_style(content, project_root=project_root)

        if framework == 'playwright' and self._is_pytest_page_style(content):
            return self._run_python_playwright_pytest_style(content)
        return self._run_python_subprocess(content)

    @staticmethod
    def _needs_tests_package(content: str) -> bool:
        return bool(re.search(r'(?:from|import)\s+tests(?:\.|\s|$)', content))

    @staticmethod
    def _is_pytest_page_style(content: str) -> bool:
        return bool(
            re.search(r'def\s+test_\w+\s*\([^)]*\bpage\b', content)
            or re.search(r'class\s+Test\w*', content)
        )

    def _media_generated_root(self) -> Path:
        from django.conf import settings
        return Path(settings.MEDIA_ROOT) / 'ui-automation' / 'generated'

    def _resolve_generated_project_root(self, content: str) -> Path | None:
        """定位 codegen 落盘工程根目录：media/ui-automation/generated/{scenario}/"""
        generated_root = self._media_generated_root()
        if not generated_root.exists():
            return None

        # 1) 通过 CodegenConversion.generated_script_ids 反查
        try:
            from .models import CodegenConversion
            for conv in CodegenConversion.objects.filter(project_id=self.script.project_id).order_by('-id')[:50]:
                ids = conv.generated_script_ids or []
                if self.script.id in ids or str(self.script.id) in [str(x) for x in ids]:
                    root = generated_root / conv.scenario
                    if (root / 'tests').is_dir():
                        return root
        except Exception as exc:
            logger.debug('resolve project via CodegenConversion failed: %s', exc)

        # 2) 脚本名前缀 scenario_xxx
        name = self.script.name or ''
        for child in sorted(generated_root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if child.is_dir() and (child / 'tests').is_dir():
                if name.startswith(child.name + '_') or child.name in name:
                    return child

        # 3) 磁盘 specs 内容匹配
        needle = (content or '').strip()
        if needle:
            for spec in generated_root.glob('*/tests/specs/*'):
                if not spec.is_file():
                    continue
                try:
                    disk = spec.read_text(encoding='utf-8').strip()
                except Exception:
                    continue
                if disk == needle or (len(needle) > 80 and needle[:80] in disk):
                    return spec.parents[2]  # .../generated/scenario

        # 4) 仅有一个 generated 工程时直接使用
        candidates = [p for p in generated_root.iterdir() if p.is_dir() and (p / 'tests').is_dir()]
        if len(candidates) == 1:
            return candidates[0]
        return None

    def _find_spec_file(self, project_root: Path, content: str) -> Path | None:
        specs_dir = project_root / 'tests' / 'specs'
        if not specs_dir.is_dir():
            return None
        needle = (content or '').strip()
        name = self.script.name or ''
        # 精确/前缀匹配文件名
        for path in specs_dir.iterdir():
            if not path.is_file():
                continue
            if path.name in name or name.endswith(path.name):
                return path
        # 内容匹配
        for path in specs_dir.iterdir():
            if not path.is_file():
                continue
            try:
                disk = path.read_text(encoding='utf-8').strip()
            except Exception:
                continue
            if disk == needle:
                return path
        return None

    @staticmethod
    def _normalize_spec_indentation(content: str) -> str:
        """修复常见生成缺陷：test 方法体内步骤误缩进到 class 级（4 空格）。"""
        lines = content.splitlines()
        out: list[str] = []
        in_test_method = False
        method_indent = 0
        step_re = re.compile(
            r'^(page\.|expect\(|pom\.|assert |data\s*=|#\s*(TODO|下列|参数化)|pytest\.|self\.)'
        )

        for line in lines:
            stripped = line.lstrip(' \t')
            indent = len(line) - len(stripped) if stripped else len(line)

            if re.match(r'def\s+test_\w+\s*\(', stripped):
                in_test_method = True
                method_indent = indent
                out.append(line)
                continue

            if in_test_method:
                if not stripped:
                    out.append(line)
                    continue
                if indent <= method_indent:
                    if re.match(r'(def |class |@)', stripped):
                        in_test_method = False
                        out.append(line)
                        continue
                    if step_re.match(stripped):
                        out.append(' ' * (method_indent + 4) + stripped)
                        continue
                    in_test_method = False
                out.append(line)
                continue

            out.append(line)

        normalized = '\n'.join(out)
        if content.endswith('\n'):
            normalized += '\n'
        return normalized

    def _prepare_sys_path(self, project_root: Path | None) -> list[str]:
        """将工程根加入 sys.path，并清理已缓存的 tests.* 模块。"""
        old = list(sys.path)
        if project_root:
            root = str(project_root.resolve())
            while root in sys.path:
                sys.path.remove(root)
            sys.path.insert(0, root)
            for key in [k for k in list(sys.modules) if k == 'tests' or k.startswith('tests.')]:
                del sys.modules[key]
        return old

    @staticmethod
    def _harden_fragile_locators(content: str) -> str:
        """将录制产生的脆弱定位器改写为更稳的表达式。

        典型问题：购物车角标文案 ``购物车 2`` 会随数量变化导致 Timeout。
        """
        if not content:
            return content
        original = content

        # page.get_by_text("购物车 2") / '购物车 12'
        content = re.sub(
            r'get_by_text\(\s*(["\'])购物车\s*\d+\1\s*\)',
            lambda _m: 'get_by_text(re.compile(r"购物车\\s*\\d*"))',
            content,
        )
        # get_by_role("link", name="购物车 2")
        content = re.sub(
            r'get_by_role\(\s*(["\'])link\1\s*,\s*name\s*=\s*(["\'])购物车\s*\d+\2\s*\)',
            lambda _m: 'get_by_role("link", name=re.compile(r"购物车"))',
            content,
        )
        # JS: getByText('购物车 2')
        content = re.sub(
            r'getByText\(\s*(["\'])购物车\s*\d+\1\s*\)',
            lambda _m: 'getByText(/购物车\\s*\\d*/)',
            content,
        )
        # JS: getByRole('link', { name: '购物车 2' })
        content = re.sub(
            r"getByRole\(\s*(['\"])link\1\s*,\s*\{\s*name\s*:\s*(['\"])购物车\s*\d+\2\s*\}\s*\)",
            lambda _m: "getByRole('link', { name: /购物车/ })",
            content,
        )

        if content == original:
            return content

        # 确保 Python 脚本有 import re
        if 're.compile' in content and not re.search(r'^\s*(import re|from re import)', content, re.M):
            lines = content.splitlines(keepends=True)
            insert_at = 0
            # 跳过 shebang / encoding / 模块 docstring
            i = 0
            if i < len(lines) and lines[i].startswith('#!'):
                i += 1
            if i < len(lines) and re.match(r'^#.*coding[:=]', lines[i]):
                i += 1
            if i < len(lines) and lines[i].lstrip().startswith(('"""', "'''")):
                quote = lines[i].lstrip()[:3]
                if lines[i].count(quote) >= 2 and len(lines[i].strip()) > 3:
                    i += 1
                else:
                    i += 1
                    while i < len(lines) and quote not in lines[i]:
                        i += 1
                    if i < len(lines):
                        i += 1
            insert_at = i
            # 插到首个 import 之前或之后均可，放在 docstring 后更清晰
            lines.insert(insert_at, 'import re\n')
            content = ''.join(lines)

        return content

    def _harden_project_page_objects(self, project_root: Path) -> None:
        """同步加固工程内 pages 下的脆弱定位器。"""
        pages_dir = project_root / 'tests' / 'pages'
        if not pages_dir.is_dir():
            return
        for path in pages_dir.glob('*.py'):
            try:
                text = path.read_text(encoding='utf-8')
            except Exception:
                continue
            hardened = self._harden_fragile_locators(text)
            if hardened != text:
                path.write_text(hardened, encoding='utf-8')
                logger.info('hardened page object locators: %s', path)

    def _run_python_playwright_pytest_style(
        self, content: str, project_root: Path | None = None
    ) -> dict[str, Any]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                'Playwright 未安装。请在虚拟环境执行: pip install playwright && python -m playwright install'
            ) from exc

        content = self._normalize_spec_indentation(content)
        content = self._harden_fragile_locators(content)
        if project_root:
            self._harden_project_page_objects(project_root)
        old_sys_path = self._prepare_sys_path(project_root)
        try:
            if project_root:
                specs_dir = project_root / 'tests' / 'specs'
                specs_dir.mkdir(parents=True, exist_ok=True)
                (project_root / 'tests' / '__init__.py').touch(exist_ok=True)
                (specs_dir / '__init__.py').touch(exist_ok=True)
                runtime_path = specs_dir / f'_runtime_{self.script.id}.py'
                runtime_path.write_text(content, encoding='utf-8')
                script_path = runtime_path
                module_name = f'tests.specs._runtime_{self.script.id}'
                # 包路径已在 sys.path，直接 import
                if module_name in sys.modules:
                    del sys.modules[module_name]
                module = importlib.import_module(module_name)
            else:
                work = self._ensure_work_dir()
                script_path = work / 'test_script.py'
                script_path.write_text(content, encoding='utf-8')
                module_name = 'user_ui_test_script'
                module = self._load_module(script_path, module_name)

            test_items = self._collect_test_items(module)
            if not test_items:
                raise ValueError('未找到可执行的 test_* 函数/方法')

            launch_name = BROWSER_LAUNCH_MAP.get(self.browser, 'chromium')
            base_url = ''
            try:
                base_url = (getattr(self.script.project, 'base_url', None) or '').strip()
            except Exception:
                base_url = ''
            if not base_url:
                base_url = os.getenv('BASE_URL', 'http://localhost:3000')

            logs: list[str] = [
                f'脚本: {self.script.name}',
                f'模式: Playwright pytest 风格',
                f'工程目录: {project_root or "(临时目录)"}',
                f'浏览器: {launch_name}',
                f'无头: {self.headless}',
                f'base_url: {base_url}',
                f'用例数: {len(test_items)}',
                '',
            ]
            case_results: list[dict[str, Any]] = []
            passed = failed = skipped = 0

            with sync_playwright() as p:
                launcher = getattr(p, launch_name, None)
                if launcher is None:
                    raise ValueError(f'不支持的浏览器: {self.browser}')
                browser_obj = launcher.launch(headless=self.headless)
                try:
                    context = browser_obj.new_context()
                    page = context.new_page()
                    for name, fn in test_items:
                        logs.append(f'>>> 开始: {name}')
                        if self._is_unimplemented_stub(fn):
                            skipped += 1
                            case_results.append({
                                'name': name,
                                'status': 'skipped',
                                'error': '未实现的计划占位用例',
                            })
                            logs.append(f'<<< 跳过: {name} - 未实现的计划占位用例')
                            continue
                        try:
                            self._invoke_test_fn(
                                fn,
                                page=page,
                                context=context,
                                browser=browser_obj,
                                base_url=base_url,
                            )
                            passed += 1
                            case_results.append({'name': name, 'status': 'passed'})
                            logs.append(f'<<< 通过: {name}')
                        except Exception as exc:
                            if self._is_skip_exception(exc):
                                skipped += 1
                                case_results.append({
                                    'name': name,
                                    'status': 'skipped',
                                    'error': str(exc),
                                })
                                logs.append(f'<<< 跳过: {name} - {exc}')
                            else:
                                failed += 1
                                err = f'{type(exc).__name__}: {exc}'
                                case_results.append({'name': name, 'status': 'failed', 'error': err})
                                logs.append(f'<<< 失败: {name} - {err}')
                                logs.append(traceback.format_exc())
                finally:
                    browser_obj.close()

            # 全部 skip / 无真实通过时不算成功，避免「报告成功但实际未执行」
            success = failed == 0 and passed > 0
            error = ''
            if failed:
                error = f'{failed} 个用例失败'
            elif passed == 0:
                error = f'无实际执行的用例（跳过 {skipped}）'

            return {
                'success': success,
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'test_cases': case_results,
                'logs': '\n'.join(logs),
                'error': error,
            }
        finally:
            sys.path[:] = old_sys_path
            # 清理 runtime 临时 spec
            if project_root:
                runtime_path = project_root / 'tests' / 'specs' / f'_runtime_{self.script.id}.py'
                if runtime_path.exists():
                    try:
                        runtime_path.unlink()
                    except Exception:
                        pass
                for key in [k for k in list(sys.modules) if k == 'tests' or k.startswith('tests.')]:
                    del sys.modules[key]
                if module_name in sys.modules:
                    del sys.modules[module_name]

    @staticmethod
    def _load_module(path: Path, module_name: str):
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f'无法加载脚本模块: {path}')
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module

    @staticmethod
    def _collect_test_items(module) -> list[tuple[str, Callable]]:
        """收集模块级 test_* 与 Test* 类中的 test_* 方法。"""
        items: list[tuple[str, Callable]] = []

        for name, obj in inspect.getmembers(module, inspect.isfunction):
            if name.startswith('test_') and obj.__module__ == module.__name__:
                items.append((name, obj))

        for cls_name, cls in inspect.getmembers(module, inspect.isclass):
            if not cls_name.startswith('Test'):
                continue
            if cls.__module__ != module.__name__:
                continue
            try:
                instance = cls()
            except Exception:
                continue
            methods = []
            for mname, method in inspect.getmembers(instance, predicate=inspect.ismethod):
                if mname.startswith('test_'):
                    methods.append((mname, method))
            methods.sort(
                key=lambda x: getattr(x[1].__func__, '__code__', type('C', (), {'co_firstlineno': 0})).co_firstlineno
            )
            for mname, method in methods:
                items.append((f'{cls_name}.{mname}', method))

        return items

    @staticmethod
    def _is_skip_exception(exc: BaseException) -> bool:
        name = type(exc).__name__
        if name in ('Skipped', 'SkipTest'):
            return True
        module = getattr(type(exc), '__module__', '') or ''
        return 'pytest' in module and 'skip' in name.lower()

    @staticmethod
    def _is_unimplemented_stub(fn: Callable) -> bool:
        """识别 codegen 生成的假成功占位（goto + assert data）。"""
        try:
            src = inspect.getsource(fn)
        except (OSError, TypeError):
            return False
        if 'pytest.skip(' in src:
            return False
        has_todo = 'TODO: 按计划补齐' in src
        has_fake_assert = re.search(r'\bassert\s+data\b', src) is not None
        return has_todo and has_fake_assert

    @staticmethod
    def _invoke_test_fn(fn: Callable, *, page, context, browser, base_url: str = '') -> None:
        sig = inspect.signature(fn)
        kwargs = {}
        for param in sig.parameters.values():
            if param.name == 'self':
                continue
            if param.name == 'page':
                kwargs['page'] = page
            elif param.name == 'context':
                kwargs['context'] = context
            elif param.name == 'browser':
                kwargs['browser'] = browser
            elif param.name == 'base_url':
                kwargs['base_url'] = base_url or ''
        if kwargs:
            fn(**kwargs)
        else:
            # 无参或仅 self：仍尝试传入 page
            try:
                fn(page)
            except TypeError:
                fn()

    def _run_python_subprocess(self, content: str) -> dict[str, Any]:
        content = self._harden_fragile_locators(content)
        work = self._ensure_work_dir()
        script_path = work / 'script.py'
        script_path.write_text(content, encoding='utf-8')

        env = os.environ.copy()
        env.setdefault('PYTHONUNBUFFERED', '1')
        # 透传无头偏好（脚本若自行读取）
        env['UI_SCRIPT_HEADLESS'] = '1' if self.headless else '0'
        env['UI_SCRIPT_BROWSER'] = BROWSER_LAUNCH_MAP.get(self.browser, 'chromium')

        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(work),
            capture_output=True,
            text=True,
            timeout=self.timeout,
            env=env,
        )
        stdout = result.stdout or ''
        stderr = result.stderr or ''
        success = result.returncode == 0
        logs = f'$ python {script_path.name}\n{stdout}\n{stderr}'.strip()
        return {
            'success': success,
            'passed': 1 if success else 0,
            'failed': 0 if success else 1,
            'skipped': 0,
            'test_cases': [{
                'name': self.script.name,
                'status': 'passed' if success else 'failed',
                'error': '' if success else (stderr or f'exit code {result.returncode}'),
            }],
            'logs': logs,
            'stdout': stdout,
            'stderr': stderr,
            'error': '' if success else (stderr.strip() or f'脚本退出码: {result.returncode}'),
        }

    def _run_javascript(self, content: str) -> dict[str, Any]:
        work = self._ensure_work_dir()
        is_playwright_test = '@playwright/test' in content or "from '@playwright/test'" in content

        if is_playwright_test:
            spec_path = work / 'test_script.spec.js'
            spec_path.write_text(content, encoding='utf-8')
            config = (
                "module.exports = {\n"
                f"  use: {{ headless: {str(self.headless).lower()}, "
                f"browserName: '{BROWSER_LAUNCH_MAP.get(self.browser, 'chromium')}' }},\n"
                "  testDir: '.',\n"
                "};\n"
            )
            (work / 'playwright.config.js').write_text(config, encoding='utf-8')
            cmd = ['npx', '--yes', 'playwright', 'test', str(spec_path), '--config', str(work / 'playwright.config.js')]
            if not self.headless:
                cmd.append('--headed')
        else:
            script_path = work / 'script.js'
            script_path.write_text(content, encoding='utf-8')
            cmd = ['node', str(script_path)]

        result = subprocess.run(
            cmd,
            cwd=str(work),
            capture_output=True,
            text=True,
            timeout=self.timeout,
            shell=os.name == 'nt',
        )
        stdout = result.stdout or ''
        stderr = result.stderr or ''
        success = result.returncode == 0
        logs = f"$ {' '.join(cmd)}\n{stdout}\n{stderr}".strip()
        return {
            'success': success,
            'passed': 1 if success else 0,
            'failed': 0 if success else 1,
            'skipped': 0,
            'test_cases': [{
                'name': self.script.name,
                'status': 'passed' if success else 'failed',
                'error': '' if success else (stderr or f'exit code {result.returncode}'),
            }],
            'logs': logs,
            'stdout': stdout,
            'stderr': stderr,
            'error': '' if success else (stderr.strip() or f'脚本退出码: {result.returncode}'),
        }
