"""
Playwright Codegen 录制会话管理。

对齐实践教程流程：
1. 检测 node/npx/playwright 环境
2. 启动全屏/最大化有头浏览器 + Inspector 录制（优先 codegen_launcher）
3. 人工操作结束后进程退出，读取 -o 输出文件
4. 将原始录制脚本落到 media/ui-automation/recorded/
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

# 文章默认使用 python + pytest 风格
LANGUAGE_TARGET_MAP = {
    'python': 'python-pytest',
    'javascript': 'javascript',
    'typescript': 'playwright-test',
}

BROWSER_CHOICES = {'chromium', 'firefox', 'webkit'}

# 启动后短暂观察，捕获「浏览器未安装」等立即退出错误
STARTUP_PROBE_SECONDS = 1.5


@dataclass
class CodegenSession:
    session_id: str
    user_id: int
    url: str
    browser: str
    language: str
    target: str
    output_path: str
    command: list[str]
    process: subprocess.Popen | None = None
    status: str = 'starting'  # starting | recording | finished | failed | stopped
    error: str = ''
    log_path: str = ''
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    project_id: int | None = None
    script_name: str = ''

    def to_dict(self, include_content: bool = False) -> dict[str, Any]:
        content = ''
        if include_content and self.output_path and os.path.exists(self.output_path):
            try:
                content = Path(self.output_path).read_text(encoding='utf-8')
            except Exception as exc:  # noqa: BLE001
                logger.warning('read recorded script failed: %s', exc)

        return {
            'session_id': self.session_id,
            'status': self.status,
            'url': self.url,
            'browser': self.browser,
            'language': self.language,
            'target': self.target,
            'command': ' '.join(self.command),
            'output_path': self.output_path,
            'script_name': self.script_name,
            'project_id': self.project_id,
            'error': self.error,
            'log_path': self.log_path,
            'started_at': self.started_at,
            'finished_at': self.finished_at,
            'pid': self.process.pid if self.process and self.process.poll() is None else None,
            'content': content if include_content else None,
            'has_content': bool(content) if include_content else (
                bool(self.output_path and os.path.exists(self.output_path) and os.path.getsize(self.output_path) > 0)
            ),
        }


class CodegenRecorderService:
    """按用户隔离的 codegen 会话（单用户同时仅允许一个录制）。"""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sessions: dict[int, CodegenSession] = {}

    def recorded_root(self) -> Path:
        root = Path(settings.MEDIA_ROOT) / 'ui-automation' / 'recorded'
        root.mkdir(parents=True, exist_ok=True)
        return root

    def logs_root(self) -> Path:
        root = Path(settings.MEDIA_ROOT) / 'ui-automation' / 'codegen-logs'
        root.mkdir(parents=True, exist_ok=True)
        return root

    def check_environment(self) -> dict[str, Any]:
        node = self._which_node()
        npx = self._which('npx')
        python_playwright = self._resolve_python_playwright()
        npx_playwright = False
        npx_playwright_version = ''

        if npx:
            try:
                result = subprocess.run(
                    [npx, 'playwright', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    shell=False,
                )
                if result.returncode == 0:
                    npx_playwright = True
                    npx_playwright_version = (result.stdout or result.stderr or '').strip()
            except Exception as exc:  # noqa: BLE001
                logger.info('npx playwright check failed: %s', exc)

        browsers = self._check_browsers(python_playwright.get('python') if python_playwright.get('installed') else None)
        ready = bool(python_playwright.get('installed') or (npx and (npx_playwright or node)))
        can_start = bool(python_playwright.get('installed') or npx)

        return {
            'ready': ready and (browsers.get('ok') or can_start),
            'can_start': can_start,
            'node': {
                'installed': bool(node),
                'path': node or '',
                'version': self._run_version([node, '--version']) if node else '',
            },
            'npx': {
                'installed': bool(npx),
                'path': npx or '',
                'version': self._run_version([npx, '--version']) if npx else '',
            },
            'python_playwright': python_playwright,
            'npx_playwright': {
                'installed': npx_playwright,
                'version': npx_playwright_version,
            },
            'browsers': browsers,
            'tips': self._env_tips(
                bool(node),
                bool(npx),
                bool(python_playwright.get('installed')),
                npx_playwright,
                browsers,
                python_playwright.get('python') or '',
            ),
        }

    def get_session(self, user_id: int) -> CodegenSession | None:
        with self._lock:
            session = self._sessions.get(user_id)
            if session:
                self._refresh_session(session)
            return session

    def start(
        self,
        user_id: int,
        url: str,
        browser: str = 'chromium',
        language: str = 'python',
        project_id: int | None = None,
        script_name: str = '',
    ) -> CodegenSession:
        url = (url or '').strip()
        if not url or url in {'https://', 'http://'}:
            raise ValueError('请输入有效的目标 URL')

        browser = (browser or 'chromium').lower()
        if browser not in BROWSER_CHOICES:
            raise ValueError(f'不支持的浏览器: {browser}')

        language = (language or 'python').lower()
        if language not in LANGUAGE_TARGET_MAP:
            raise ValueError(f'不支持的语言: {language}')

        env = self.check_environment()
        if not env.get('can_start'):
            raise RuntimeError('未检测到可用的 Playwright 环境，请先安装 Node.js/npx 或 python playwright')

        with self._lock:
            current = self._sessions.get(user_id)
            if current:
                self._refresh_session(current)
                if current.status in {'starting', 'recording'}:
                    raise RuntimeError('当前已有录制任务进行中，请先结束录制')

            session_id = uuid.uuid4().hex[:12]
            target = LANGUAGE_TARGET_MAP[language]
            ext = 'py' if language == 'python' else ('ts' if language == 'typescript' else 'js')
            safe_name = (script_name or f'recorded_{session_id}').strip()
            for ch in r'\/:*?"<>|':
                safe_name = safe_name.replace(ch, '_')
            if not safe_name.lower().endswith(f'.{ext}'):
                safe_name = f'{safe_name}.{ext}'

            output_path = str(self.recorded_root() / safe_name)
            log_path = str(self.logs_root() / f'{session_id}.log')
            command = self._build_command(env, target, browser, output_path, url)

            session = CodegenSession(
                session_id=session_id,
                user_id=user_id,
                url=url,
                browser=browser,
                language=language,
                target=target,
                output_path=output_path,
                command=command,
                log_path=log_path,
                project_id=project_id,
                script_name=safe_name,
            )

            log_fh = None
            try:
                creationflags = 0
                if sys.platform == 'win32':
                    # 不弹黑窗口；stdout/stderr 已重定向到日志文件，避免与 Django IO 互相阻塞
                    creationflags = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

                log_fh = open(log_path, 'w', encoding='utf-8', errors='replace')  # noqa: SIM115
                session.process = subprocess.Popen(
                    command,
                    cwd=str(self.recorded_root()),
                    stdout=log_fh,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    creationflags=creationflags,
                )
                # 句柄由子进程继承，父进程可关闭
                log_fh.close()
                log_fh = None
                session.status = 'recording'
            except Exception as exc:  # noqa: BLE001
                if log_fh:
                    try:
                        log_fh.close()
                    except Exception:  # noqa: BLE001
                        pass
                session.status = 'failed'
                session.error = str(exc)
                session.finished_at = time.time()
                self._sessions[user_id] = session
                raise RuntimeError(f'启动 codegen 失败: {exc}') from exc

            # 立即探测：浏览器未安装时进程会秒退
            time.sleep(STARTUP_PROBE_SECONDS)
            self._refresh_session(session)
            if session.status in {'failed', 'finished', 'stopped'}:
                detail = session.error or self._read_log_tail(log_path)
                hint = self._browser_install_hint(env, detail)
                session.status = 'failed'
                session.error = hint
                session.finished_at = session.finished_at or time.time()
                self._sessions[user_id] = session
                raise RuntimeError(hint)

            self._sessions[user_id] = session
            logger.info('codegen started user=%s session=%s cmd=%s', user_id, session_id, ' '.join(command))
            return session

    def stop(self, user_id: int) -> CodegenSession | None:
        with self._lock:
            session = self._sessions.get(user_id)
            if not session:
                return None
            self._refresh_session(session)
            process = session.process
            still_running = bool(process and process.poll() is None)
            if still_running:
                self._request_graceful_stop(session)

        # 锁外等待，避免阻塞 status 轮询
        if still_running and process is not None:
            exited = self._wait_process_exit(process, timeout=8.0)
            if not exited:
                self._kill_process_tree(process)
                self._wait_process_exit(process, timeout=3.0)
            time.sleep(0.4)

        with self._lock:
            session = self._sessions.get(user_id)
            if not session:
                return None
            self._refresh_session(session)
            if session.status in {'starting', 'recording'}:
                self._finalize_stopped_session(session)
            elif session.status in {'finished', 'stopped', 'failed'}:
                # 确保有内容时优先 finished，并清理 stop 文件
                has_content = (
                    session.output_path
                    and os.path.exists(session.output_path)
                    and os.path.getsize(session.output_path) > 0
                )
                if has_content:
                    session.status = 'finished'
                    session.error = ''
                try:
                    stop_path = self._stop_file_path(session)
                    if stop_path.exists():
                        stop_path.unlink()
                except Exception:  # noqa: BLE001
                    pass
            return session

    @staticmethod
    def _stop_file_path(session: CodegenSession) -> Path:
        return Path(f'{session.output_path}.stop')

    def _request_graceful_stop(self, session: CodegenSession) -> None:
        """写入停止标记，让 launcher 优雅关闭浏览器并刷盘。"""
        try:
            stop_path = self._stop_file_path(session)
            stop_path.write_text('stop', encoding='utf-8')
            logger.info('codegen stop file written: %s', stop_path)
        except Exception as exc:  # noqa: BLE001
            logger.warning('write stop file failed: %s', exc)

    @staticmethod
    def _wait_process_exit(process: subprocess.Popen, timeout: float) -> bool:
        try:
            process.wait(timeout=timeout)
            return True
        except subprocess.TimeoutExpired:
            return False
        except Exception:  # noqa: BLE001
            return process.poll() is not None

    @staticmethod
    def _kill_process_tree(process: subprocess.Popen) -> None:
        """Windows 下 terminate 不会杀子进程树，需 taskkill /T。"""
        if process.poll() is not None:
            return
        pid = process.pid
        try:
            if sys.platform == 'win32':
                subprocess.run(
                    ['taskkill', '/F', '/T', '/PID', str(pid)],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    creationflags=subprocess.CREATE_NO_WINDOW,  # type: ignore[attr-defined]
                )
            else:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
        except Exception as exc:  # noqa: BLE001
            logger.warning('kill codegen process tree failed: %s', exc)
            try:
                process.kill()
            except Exception:  # noqa: BLE001
                pass

    def _finalize_stopped_session(self, session: CodegenSession) -> None:
        """结束后读取脚本；有内容视为 finished，否则 stopped。"""
        session.finished_at = session.finished_at or time.time()
        has_content = (
            session.output_path
            and os.path.exists(session.output_path)
            and os.path.getsize(session.output_path) > 0
        )
        session.status = 'finished' if has_content else 'stopped'
        if not has_content:
            session.error = session.error or '录制已结束，但未生成脚本内容（可能未执行任何操作）'
        else:
            session.error = ''
        try:
            stop_path = self._stop_file_path(session)
            if stop_path.exists():
                stop_path.unlink()
        except Exception:  # noqa: BLE001
            pass

    def list_recorded(self, limit: int = 50) -> list[dict[str, Any]]:
        root = self.recorded_root()
        files = []
        for path in sorted(root.glob('*'), key=lambda p: p.stat().st_mtime, reverse=True):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {'.py', '.js', '.ts'}:
                continue
            if path.name.startswith('_diag'):
                continue
            files.append({
                'name': path.name,
                'path': str(path),
                'size': path.stat().st_size,
                'updated_at': path.stat().st_mtime,
            })
            if len(files) >= limit:
                break
        return files

    def read_recorded(self, name: str) -> str:
        root = self.recorded_root().resolve()
        path = (root / Path(name).name).resolve()
        if not str(path).startswith(str(root)):
            raise ValueError('非法文件路径')
        if not path.exists():
            raise FileNotFoundError('录制文件不存在')
        return path.read_text(encoding='utf-8')

    def _refresh_session(self, session: CodegenSession) -> None:
        if session.status not in {'starting', 'recording'}:
            return
        if not session.process:
            session.status = 'failed'
            session.error = session.error or '录制进程丢失'
            session.finished_at = time.time()
            return

        code = session.process.poll()
        if code is None:
            session.status = 'recording'
            return

        session.finished_at = time.time()
        has_content = (
            session.output_path
            and os.path.exists(session.output_path)
            and os.path.getsize(session.output_path) > 0
        )
        log_tail = self._read_log_tail(session.log_path)
        if has_content:
            session.status = 'finished'
            session.error = ''
        elif code == 0:
            session.status = 'finished'
            session.error = '录制已结束，但未生成脚本内容（可能未执行任何操作）'
        else:
            session.status = 'failed'
            detail = log_tail or f'录制进程异常退出，exit_code={code}'
            if 'Executable doesn\'t exist' in detail or 'Please run' in detail:
                session.error = (
                    'Playwright 浏览器未安装或版本不匹配，进程已退出。\n'
                    f'{detail.strip()[:500]}'
                )
            else:
                session.error = detail.strip()[:800] or f'录制进程异常退出，exit_code={code}'

    def _screen_viewport_size(self) -> str:
        """主屏分辨率，供 codegen --viewport-size 使用。"""
        try:
            if sys.platform == 'win32':
                import ctypes

                user32 = ctypes.windll.user32
                width = int(user32.GetSystemMetrics(0))
                height = int(user32.GetSystemMetrics(1))
                if width > 0 and height > 0:
                    return f'{width},{height}'
        except Exception:  # noqa: BLE001
            pass
        return '1920,1080'

    def _build_command(self, env: dict[str, Any], target: str, browser: str, output_path: str, url: str) -> list[str]:
        py_info = env.get('python_playwright') or {}
        python_ok = bool(py_info.get('installed'))
        python_bin = py_info.get('python') or ''
        npx = env.get('npx', {}).get('path') or self._which('npx')
        launcher = str(Path(__file__).resolve().with_name('codegen_launcher.py'))

        # 优先使用带 playwright 的 Python + 全屏启动器（最大化窗口录制）
        if python_ok and python_bin:
            stop_file = f'{output_path}.stop'
            return [
                python_bin, launcher,
                '--target', target,
                '--browser', browser,
                '-o', output_path,
                '--stop-file', stop_file,
                url,
            ]

        if not npx:
            raise RuntimeError('未找到可用的 Python Playwright 或 npx，无法启动录制')

        # npx 回退：官方 CLI 不支持 maximized，用主屏分辨率近似全屏
        return [
            npx, 'playwright', 'codegen',
            '--target', target,
            '--browser', browser,
            '--viewport-size', self._screen_viewport_size(),
            '-o', output_path,
            url,
        ]

    def _resolve_python_playwright(self) -> dict[str, Any]:
        """在系统解释器与项目 venv 中查找可用的 python -m playwright。"""
        candidates: list[str] = []
        for item in [
            sys.executable,
            str(Path(settings.BASE_DIR) / 'venv' / 'Scripts' / 'python.exe'),
            str(Path(settings.BASE_DIR) / 'venv' / 'bin' / 'python'),
            str(Path(settings.BASE_DIR) / '.venv' / 'Scripts' / 'python.exe'),
            str(Path(settings.BASE_DIR) / '.venv' / 'bin' / 'python'),
        ]:
            if item and item not in candidates and os.path.isfile(item):
                candidates.append(item)

        last_hint = ''
        for python_bin in candidates:
            info = self._check_python_playwright(python_bin)
            if info.get('installed'):
                info['python'] = python_bin
                return info
            last_hint = info.get('hint') or last_hint

        return {
            'installed': False,
            'version': '',
            'python': '',
            'hint': last_hint or '请在项目 venv 中执行: pip install playwright && python -m playwright install',
        }

    def _check_browsers(self, python_bin: str | None) -> dict[str, Any]:
        if not python_bin:
            return {'ok': False, 'detail': '未检测到 Python Playwright，无法检查浏览器'}
        try:
            result = subprocess.run(
                [python_bin, '-m', 'playwright', 'install', '--dry-run'],
                capture_output=True,
                text=True,
                timeout=30,
            )
            text = (result.stdout or '') + (result.stderr or '')
            # dry-run 会列出需要下载的包；若 chromium 已存在通常仍会打印 Install location
            missing = 'Download url' in text and 'chromium' in text.lower()
            # 更稳妥：直接看常见 chrome 路径是否存在（版本目录会变，用 glob）
            ms_root = Path.home() / 'AppData' / 'Local' / 'ms-playwright'
            chrome_bins = list(ms_root.glob('chromium-*/chrome-win64/chrome.exe')) if ms_root.exists() else []
            ok = bool(chrome_bins)
            return {
                'ok': ok,
                'chromium_paths': [str(p) for p in chrome_bins[:5]],
                'detail': '' if ok else '未找到已安装的 Chromium，请执行: python -m playwright install chromium',
                'dry_run': text[:400],
                'missing_hint': missing,
            }
        except Exception as exc:  # noqa: BLE001
            return {'ok': False, 'detail': str(exc)}

    @staticmethod
    def _browser_install_hint(env: dict[str, Any], detail: str) -> str:
        py = (env.get('python_playwright') or {}).get('python') or sys.executable
        base = (
            '录制进程启动后立即退出。常见原因是 Playwright 浏览器未安装。\n'
            f'请执行：\n  "{py}" -m playwright install chromium\n'
            '然后重新点击「开始录制」。'
        )
        tail = (detail or '').strip()
        if tail:
            return f'{base}\n\n详情：\n{tail[:600]}'
        return base

    @staticmethod
    def _read_log_tail(log_path: str, max_chars: int = 1200) -> str:
        if not log_path or not os.path.exists(log_path):
            return ''
        try:
            text = Path(log_path).read_text(encoding='utf-8', errors='replace')
            return text[-max_chars:]
        except Exception:  # noqa: BLE001
            return ''

    @staticmethod
    def _which(cmd: str) -> str | None:
        return shutil.which(cmd)

    @classmethod
    def _which_node(cls) -> str | None:
        """避开 Cursor 自带的 helper node，优先系统/正式 Node 安装。"""
        found = shutil.which('node')
        if found and 'cursor' in found.lower() and 'helpers' in found.lower():
            # 继续在 PATH 中找其他 node
            path_env = os.environ.get('PATH', '')
            for folder in path_env.split(os.pathsep):
                for name in ('node.exe', 'node'):
                    candidate = Path(folder) / name
                    if candidate.is_file():
                        resolved = str(candidate.resolve())
                        if 'cursor' in resolved.lower() and 'helpers' in resolved.lower():
                            continue
                        return resolved
            return found
        return found

    @staticmethod
    def _run_version(cmd: list[str]) -> str:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            return (result.stdout or result.stderr or '').strip()
        except Exception:  # noqa: BLE001
            return ''

    @staticmethod
    def _check_python_playwright(python_bin: str | None = None) -> dict[str, Any]:
        python_bin = python_bin or sys.executable
        try:
            result = subprocess.run(
                [python_bin, '-m', 'playwright', '--version'],
                capture_output=True,
                text=True,
                timeout=20,
            )
            installed = result.returncode == 0
            return {
                'installed': installed,
                'version': (result.stdout or result.stderr or '').strip() if installed else '',
                'python': python_bin if installed else '',
                'hint': '' if installed else f'{python_bin} -m pip install playwright && {python_bin} -m playwright install',
            }
        except Exception as exc:  # noqa: BLE001
            return {
                'installed': False,
                'version': '',
                'python': '',
                'hint': f'{python_bin} -m pip install playwright && playwright install ({exc})',
            }

    @staticmethod
    def _env_tips(
        has_node: bool,
        has_npx: bool,
        has_py_pw: bool,
        has_npx_pw: bool,
        browsers: dict[str, Any] | None = None,
        python_bin: str = '',
    ) -> list[str]:
        tips = []
        if not has_node:
            tips.append('未检测到 Node.js，建议安装后使用 npx playwright codegen')
        if not has_npx and not has_py_pw:
            tips.append('未检测到 npx 与 python playwright，无法启动录制')
        if has_npx and not has_npx_pw and not has_py_pw:
            tips.append('首次启动会通过 npx 自动下载 playwright，请保持网络畅通')
        if has_py_pw:
            tips.append(f'已检测到 Python Playwright（{python_bin or "venv"}），将优先使用全屏录制启动器')
        if browsers and not browsers.get('ok'):
            cmd = f'"{python_bin}" -m playwright install chromium' if python_bin else 'python -m playwright install chromium'
            tips.append(f'未检测到 Chromium 浏览器，请先执行: {cmd}')
        tips.append('录制过程中请在 Playwright Inspector 中点击停止，或关闭浏览器结束录制')
        return tips


codegen_recorder = CodegenRecorderService()
