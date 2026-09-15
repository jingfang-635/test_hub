#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TestHub 一键启动（单窗口版）

把 MySQL / Redis / 前端 / Django-Q2 集群 / 定时任务调度器 / Uvicorn 后端
全部收敛到一个窗口里运行：

* 每个服务的输出都会带 [服务名] 前缀实时打印，并同时落盘到 logs/start/<服务名>.log
* MySQL / Redis / 前端 / Q2 / 调度器 均以「无窗口」方式后台启动，不再弹出多个黑框
* Uvicorn 后端在当前窗口前台运行，按 Ctrl+C 一次性停止所有由本脚本启动的服务

用法：
  start.bat                       # 启动全部服务（单窗口）
  start.bat --no-frontend         # 不启动前端
  start.bat --no-backend          # 只启动前端 + 后台 worker（后端单独调试时用）
  start.bat --no-infra            # 不管理 MySQL / Redis（假设已作为系统服务运行）
  start.bat --keep-infra          # 退出时不停止本脚本启动的 MySQL / Redis
  start.bat --reload              # 后端开启热重载
  start.bat --stop                # 停止后端 / 前端 / Q2 / 调度器（按端口与命令行匹配）
  start.bat --status              # 查看 MySQL / Redis / 前后端 / worker 运行状态

也可以直接：python start_all.py [选项]
"""
from __future__ import annotations

import argparse
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / 'backend'
FRONTEND_DIR = ROOT / 'frontend'
LOG_DIR = ROOT / 'logs' / 'start'

IS_WINDOWS = os.name == 'nt'
CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0

# 日志前缀宽度，保证各服务输出对齐
_PREFIX_WIDTH = 11
_MAX_LOG_BYTES = 10 * 1024 * 1024

_COLORS = {
    'core': '\033[37m',
    'mysql': '\033[35m',
    'redis': '\033[31m',
    'frontend': '\033[96m',
    'qcluster': '\033[33m',
    'scheduler': '\033[94m',
    'backend': '\033[32m',
}
_RESET = '\033[0m'

# 停机保护：进入清理阶段后忽略再次 Ctrl+C，避免把清理流程打断只留下一半进程
_SHUTTING_DOWN = False


def _sigint_handler(signum, frame):
    if _SHUTTING_DOWN:
        print('\n  正在停止服务，请稍候 ...（若长时间无响应可直接关闭本窗口）', flush=True)
        return
    raise KeyboardInterrupt


def _decode(raw: bytes) -> str:
    """子进程输出解码：优先 UTF-8，回退 GBK（cmd 内建命令用 GBK 输出）。"""
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('gbk', 'replace')


# --------------------------------------------------------------------------
# 控制台输出（带服务名前缀 + 落盘日志）
# --------------------------------------------------------------------------
def _enable_vt() -> bool:
    """在 Windows 控制台开启 ANSI 转义支持。"""
    if not sys.stdout.isatty():
        return False
    if not IS_WINDOWS:
        return True
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        handle = kernel32.GetStdHandle(-11)
        mode = ctypes.c_uint32()
        if not kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        return True
    except Exception:
        return False


class Console:
    """统一输出：控制台带前缀打印，同时按服务写入 logs/start/<name>.log。"""

    def __init__(self, color: bool = True):
        self.color = bool(color) and _enable_vt()
        self._lock = threading.Lock()
        self._files: dict[str, object] = {}
        LOG_DIR.mkdir(parents=True, exist_ok=True)

    # -- 内部工具 ---------------------------------------------------------
    def _log_file(self, name: str):
        handle = self._files.get(name)
        if handle is None:
            path = LOG_DIR / f'{name}.log'
            try:
                if path.exists() and path.stat().st_size > _MAX_LOG_BYTES:
                    backup = path.with_suffix('.log.1')
                    if backup.exists():
                        backup.unlink()
                    path.rename(backup)
            except OSError:
                pass
            try:
                handle = path.open('a', encoding='utf-8', errors='replace', buffering=1)
            except OSError:
                handle = False
            self._files[name] = handle
        return handle or None

    def _write(self, name: str, text: str) -> None:
        handle = self._log_file(name)
        if handle is not None:
            try:
                handle.write(text + '\n')
            except Exception:
                pass

    def _paint(self, name: str, text: str) -> str:
        color = _COLORS.get(name)
        if not self.color or not color:
            return text
        return f'{color}{text}{_RESET}'

    # -- 对外接口 ---------------------------------------------------------
    def service(self, name: str, text: str) -> None:
        """打印某个服务的一行输出。"""
        prefix = f'[{name}]'.ljust(_PREFIX_WIDTH)
        with self._lock:
            self._write(name, f'{prefix}{text}')
            print(f'{self._paint(name, prefix)}{text}', flush=True)

    def info(self, text: str = '') -> None:
        with self._lock:
            print(text, flush=True)

    def warn(self, text: str) -> None:
        self.info(self._paint('core', f'  ! {text}'))

    def rule(self, text: str = '') -> None:
        self.info('-' * 64)
        if text:
            self.info(f'  {text}')
            self.info('-' * 64)

    def banner(self, lines: list[str]) -> None:
        self.info('=' * 64)
        for line in lines:
            self.info(f'  {line}')
        self.info('=' * 64)

    def close(self) -> None:
        with self._lock:
            for handle in self._files.values():
                if handle:
                    try:
                        handle.close()
                    except Exception:
                        pass
            self._files.clear()


# --------------------------------------------------------------------------
# 端口 / 进程工具
# --------------------------------------------------------------------------
def read_config_port(key: str, default: int) -> int:
    """读取端口配置，优先级：环境变量 TESTHUB_<KEY> > config.yaml > 默认值。"""
    env_value = os.environ.get(f'TESTHUB_{key}')
    if env_value and env_value.strip().isdigit():
        return int(env_value.strip())

    config_path = ROOT / 'config.yaml'
    if not config_path.exists():
        return default
    try:
        text = config_path.read_text(encoding='utf-8')
    except Exception:
        return default
    match = re.search(rf'^{re.escape(key)}:\s*(\d+)\s*$', text, re.MULTILINE)
    return int(match.group(1)) if match else default


def port_in_use(port: int, host: str = '127.0.0.1') -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.6)
        return sock.connect_ex((host, port)) == 0


def wait_for_port(port: int, timeout: float, label: str, console: Console) -> bool:
    deadline = time.time() + timeout
    last_report = 0.0
    while time.time() < deadline:
        if port_in_use(port):
            return True
        if time.time() - last_report > 5:
            last_report = time.time()
            console.service('core', f'等待 {label} 端口 {port} 就绪 ...')
        time.sleep(0.5)
    return port_in_use(port)


def pids_on_port(port: int) -> list[int]:
    """列出监听指定端口的进程 PID。"""
    try:
        proc = subprocess.run(
            ['netstat', '-ano', '-p', 'tcp'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
        )
    except Exception:
        return []

    pids: list[int] = []
    for line in (proc.stdout or '').splitlines():
        parts = line.split()
        if len(parts) < 5 or parts[0].upper() != 'TCP':
            continue
        if parts[3].upper() != 'LISTENING':
            continue
        if not parts[1].endswith(f':{port}'):
            continue
        try:
            pid = int(parts[4])
        except ValueError:
            continue
        if pid and pid not in pids:
            pids.append(pid)
    return pids


def pid_image_name(pid: int) -> str:
    if not IS_WINDOWS:
        return ''
    try:
        proc = subprocess.run(
            ['tasklist', '/FI', f'PID eq {pid}', '/FO', 'CSV', '/NH'],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
        )
    except Exception:
        return ''
    text = (proc.stdout or '').strip().splitlines()
    if not text:
        return ''
    name = text[0].split('","')[0].strip('"')
    return name


def taskkill(pid: int, force: bool = True) -> None:
    """结束进程（含子进程树）。"""
    if IS_WINDOWS:
        cmd = ['taskkill', '/T', '/PID', str(pid)]
        if force:
            cmd.insert(1, '/F')
        try:
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    else:
        try:
            os.kill(pid, 9)
        except Exception:
            pass


def list_manage_procs() -> list[tuple[int, str]]:
    """列出所有 `python manage.py ...` 进程的 (PID, 命令行)（仅 Windows）。

    特意限制进程名为 python/pythonw，避免查询用的 powershell 自身命令行
    里包含同样关键字而被误匹配。
    """
    if not IS_WINDOWS:
        return []
    script = (
        'Get-CimInstance Win32_Process | '
        "Where-Object { $_.Name -match '^pythonw?\\.exe$' "
        "-and $_.CommandLine "
        "-and $_.CommandLine -match 'manage\\.py' } | "
        "ForEach-Object { '{0}::{1}' -f $_.ProcessId, $_.CommandLine }"
    )
    try:
        proc = subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-Command', script],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
        )
    except Exception:
        return []

    procs: list[tuple[int, str]] = []
    for line in (proc.stdout or '').splitlines():
        line = line.strip()
        if '::' not in line:
            continue
        pid_text, _, cmdline = line.partition('::')
        try:
            procs.append((int(pid_text.strip()), cmdline.strip()))
        except ValueError:
            continue
    return procs


def find_worker_pids() -> list[tuple[str, int]]:
    """找出残留的 Django-Q2 集群 / 定时任务调度器进程。

    旧版 start.bat 每次启动都会新开这两个进程且从不清理，导致重复实例
    堆积：既多出一堆窗口，也会让定时任务与异步任务被重复执行。
    """
    self_pid = os.getpid()
    results: list[tuple[str, int]] = []
    for pid, cmdline in list_manage_procs():
        if pid == self_pid:
            continue
        if 'qcluster' in cmdline:
            results.append(('Django-Q2 集群', pid))
        elif 'run_all_scheduled_tasks' in cmdline:
            results.append(('定时任务调度器', pid))
    return results


def clean_duplicate_workers(console: Console) -> int:
    """清理残留的重复 worker 进程（必须在启动新 worker 之前调用）。"""
    found = find_worker_pids()
    if not found:
        return 0
    console.warn(f'检测到 {len(found)} 个残留 worker 进程（重复实例会导致任务被重复执行），正在清理 ...')
    for label, pid in found:
        console.info(f'     停止 {label} (PID {pid})')
        taskkill(pid)
    # 给 Windows 一点时间释放进程（避免紧接着启动时端口/句柄冲突）
    time.sleep(1)
    return len(found)


def clean_stale_port(port: int, console: Console, exclude: set[int] | None = None) -> None:
    """结束仍占用端口的旧进程（与旧版 start.bat 清理后端进程的行为一致）。"""
    exclude = exclude or set()
    for pid in pids_on_port(port):
        if pid in exclude or pid == os.getpid():
            continue
        name = pid_image_name(pid) or 'unknown'
        console.info(f'     停止占用端口 {port} 的旧进程: {name} (PID {pid})')
        taskkill(pid)


# --------------------------------------------------------------------------
# 服务进程管理
# --------------------------------------------------------------------------
class Service:
    def __init__(self, name: str, proc: subprocess.Popen, infra: bool = False):
        self.name = name
        self.proc = proc
        self.infra = infra

    @property
    def alive(self) -> bool:
        return self.proc.poll() is None


class Manager:
    """启动/监控子服务，退出时统一回收。"""

    def __init__(self, console: Console, python_exe: str, keep_infra: bool = False):
        self.console = console
        self.python_exe = python_exe
        self.keep_infra = keep_infra
        self.services: list[Service] = []

    def start(self, name: str, cmd, cwd: Path, hidden: bool = False, infra: bool = False) -> Service:
        env = os.environ.copy()
        env.setdefault('PYTHONIOENCODING', 'utf-8')
        env.setdefault('PYTHONUNBUFFERED', '1')

        kwargs = {
            'cwd': str(cwd),
            'stdout': subprocess.PIPE,
            'stderr': subprocess.STDOUT,
            'stdin': subprocess.DEVNULL,
            'env': env,
        }
        if IS_WINDOWS:
            kwargs['creationflags'] = CREATE_NO_WINDOW if hidden else 0

        if isinstance(cmd, str):
            # 字符串命令行（用于 cmd /c npm ... 这类需要 shell 解析的命令）
            if not IS_WINDOWS:
                cmd = ['/bin/sh', '-c', cmd]
            proc = subprocess.Popen(cmd, **kwargs)
        else:
            proc = subprocess.Popen(cmd, **kwargs)

        svc = Service(name, proc, infra=infra)
        self.services.append(svc)
        self.console.service(name, f'已启动 (PID {proc.pid}) -> logs/start/{name}.log')
        threading.Thread(target=self._pump, args=(svc,), daemon=True).start()
        return svc

    def _pump(self, svc: Service) -> None:
        stream = svc.proc.stdout
        if stream is None:
            return
        try:
            for raw in iter(stream.readline, b''):
                self.console.service(svc.name, _decode(raw).rstrip('\r\n'))
        except Exception:
            pass
        finally:
            try:
                stream.close()
            except Exception:
                pass

    def any_alive(self) -> bool:
        return any(svc.alive for svc in self.services)

    def status_lines(self) -> list[str]:
        lines = []
        for svc in self.services:
            state = '运行中' if svc.alive else f'已退出({svc.proc.returncode})'
            lines.append(f'  - {svc.name}: {state}')
        return lines

    def shutdown(self) -> None:
        targets = [svc for svc in self.services if svc.alive]
        if not targets:
            return
        self.console.info('')
        self.console.rule('正在停止服务 ...')
        for svc in reversed(targets):
            if svc.infra and self.keep_infra:
                self.console.info(f'     保留 {svc.name} (PID {svc.proc.pid}) 继续运行')
                continue
            taskkill(svc.proc.pid)
            self.console.info(f'     已停止 {svc.name} (PID {svc.proc.pid})')

        deadline = time.time() + 6
        for svc in targets:
            try:
                svc.proc.wait(timeout=max(0.2, deadline - time.time()))
            except Exception:
                pass
        for svc in targets:
            if svc.alive and not (svc.infra and self.keep_infra):
                taskkill(svc.proc.pid)
        self.console.info('  清理完成')


# --------------------------------------------------------------------------
# 基础设施（MySQL / Redis）
# --------------------------------------------------------------------------
def ensure_mysql(args, console: Console, manager: Manager) -> None:
    if args.no_infra:
        return
    port = args.mysql_port
    if port_in_use(port):
        console.info(f'  [1] MySQL 已在运行（端口 {port}），保持不动')
        return

    exe = Path(args.mysql_path) / 'mysqld.exe'
    if not exe.exists():
        console.warn(f'未找到 MySQL: {exe}，请手动启动或设置 TESTHUB_MYSQL_PATH')
        return

    console.info(f'  [1] 启动 MySQL: {exe}')
    manager.start('mysql', [str(exe), '--console'], cwd=exe.parent, hidden=True, infra=True)
    if wait_for_port(port, args.infra_timeout, 'MySQL', console):
        console.info(f'      MySQL 就绪（端口 {port}）')
    else:
        console.warn(f'等待 MySQL 端口 {port} 超时（{args.infra_timeout:.0f}s），后续服务可能启动失败')


def ensure_redis(args, console: Console, manager: Manager) -> None:
    if args.no_infra:
        return
    port = args.redis_port
    if port_in_use(port):
        console.info(f'  [2] Redis 已在运行（端口 {port}），保持不动')
        return

    redis_dir = Path(args.redis_path)
    exe = redis_dir / 'redis-server.exe'
    if not exe.exists():
        console.warn(f'未找到 Redis: {exe}，请手动启动或设置 TESTHUB_REDIS_PATH')
        return

    conf = redis_dir / 'redis.windows.conf'
    cmd = [str(exe)] + ([conf.name] if conf.exists() else [])
    console.info(f'  [2] 启动 Redis: {exe}')
    manager.start('redis', cmd, cwd=redis_dir, hidden=True, infra=True)
    if wait_for_port(port, 15, 'Redis', console):
        console.info(f'      Redis 就绪（端口 {port}）')
    else:
        console.warn(f'等待 Redis 端口 {port} 超时，后续服务可能启动失败')


# --------------------------------------------------------------------------
# 后端（当前窗口前台运行）
# --------------------------------------------------------------------------
def run_backend(args, console: Console, port: int) -> None:
    sys.argv = [str(ROOT / 'start_backend.py'), '--port', str(port)]
    if args.reload:
        sys.argv.append('--reload')
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    import start_backend  # noqa: WPS433 (延迟导入，保证 sys.path 已就绪)

    console.info('')
    console.rule(f'Uvicorn 后端启动中（HTTP + SSE + WebSocket，端口 {port}）')
    start_backend.main()


# --------------------------------------------------------------------------
# --stop：停止本项目相关进程
# --------------------------------------------------------------------------
def do_stop(args, console: Console) -> int:
    console.banner(['TestHub 停止服务'])
    targets: list[tuple[str, int]] = []

    for label, port in (('后端', read_config_port('BACKEND_PORT', 8000)),
                        ('前端', read_config_port('FRONTEND_PORT', 3000))):
        for pid in pids_on_port(port):
            if pid == os.getpid():
                continue
            targets.append((f'{label}（端口 {port}）', pid))

    targets.extend(find_worker_pids())

    if not targets:
        console.info('  未发现运行中的服务进程。')
    for label, pid in targets:
        name = pid_image_name(pid) or 'unknown'
        console.info(f'  停止 {label}: {name} (PID {pid})')
        taskkill(pid)

    console.info('')
    console.info('  说明：MySQL / Redis 不在停止范围内（如为本脚本启动，请关闭其控制台或手动结束进程）。')
    return 0


# --------------------------------------------------------------------------
# --status：查看服务状态
# --------------------------------------------------------------------------
def do_status(args, console: Console) -> int:
    console.banner(['TestHub 服务状态'])

    checks = [
        ('MySQL', read_config_port('MYSQL_PORT', 3306)),
        ('Redis', read_config_port('REDIS_PORT', 6379)),
        ('后端 (Uvicorn)', read_config_port('BACKEND_PORT', 8000)),
        ('前端 (Vite)', read_config_port('FRONTEND_PORT', 3000)),
    ]
    for label, port in checks:
        pids = pids_on_port(port)
        if pids:
            names = ', '.join(f'{pid_image_name(p) or "?"}({p})' for p in pids)
            console.info(f'  [OK]   {label}: 端口 {port} 已监听  ({names})')
        else:
            console.info(f'  [--]   {label}: 端口 {port} 未监听')

    console.info('')
    procs = find_worker_pids()
    if procs:
        for label, pid in procs:
            console.info(f'  [OK]   {label}: 运行中 (PID {pid})')
        qcluster_count = sum(1 for label, _ in procs if 'Q2' in label)
        scheduler_count = len(procs) - qcluster_count
        if qcluster_count > 1 or scheduler_count > 1:
            console.warn(f'存在重复 worker（Q2: {qcluster_count}，调度器: {scheduler_count}），'
                         '建议执行 stop.bat 后重新 start.bat')
    else:
        console.info('  [--]   Django-Q2 集群 / 定时任务调度器: 未运行')

    console.info('')
    return 0


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog='start_all.py',
        description='TestHub 一键启动（单窗口版）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--no-infra', action='store_true', help='不检查/启动 MySQL、Redis（假设已作为系统服务运行）')
    parser.add_argument('--keep-infra', action='store_true', help='退出时不停止本脚本启动的 MySQL / Redis')
    parser.add_argument('--no-frontend', action='store_true', help='不启动前端')
    parser.add_argument('--no-backend', action='store_true', help='不启动 Uvicorn 后端（仅前端 + worker）')
    parser.add_argument('--no-qcluster', action='store_true', help='不启动 Django-Q2 集群')
    parser.add_argument('--no-scheduler', action='store_true', help='不启动定时任务调度器')
    parser.add_argument('--no-workers', action='store_true', help='不启动 Q2 集群与调度器')
    parser.add_argument('--no-clean', action='store_true', help='启动前不清理占用前后端端口的旧进程')
    parser.add_argument('--reload', action='store_true', help='后端开启热重载')
    parser.add_argument('--no-color', action='store_true', help='关闭彩色输出')
    parser.add_argument('--stop', action='store_true', help='停止后端 / 前端 / Q2 / 调度器')
    parser.add_argument('--status', action='store_true', help='查看 MySQL / Redis / 前后端 / worker 状态')
    parser.add_argument('--mysql-path', default=os.environ.get('TESTHUB_MYSQL_PATH', r'D:\mysql-8.0.46-winx64\bin'),
                        help='MySQL bin 目录（默认 D:\\mysql-8.0.46-winx64\\bin）')
    parser.add_argument('--mysql-port', type=int, default=int(os.environ.get('TESTHUB_MYSQL_PORT', '3306')))
    parser.add_argument('--redis-path', default=os.environ.get('TESTHUB_REDIS_PATH', str(ROOT / 'redis-windows')),
                        help='Redis 目录（默认 <项目>/redis-windows）')
    parser.add_argument('--redis-port', type=int, default=int(os.environ.get('TESTHUB_REDIS_PORT', '6379')))
    parser.add_argument('--infra-timeout', type=float, default=60.0, help='等待 MySQL 就绪的超时秒数')
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    console = Console(color=not args.no_color)

    # 安装信号处理：正常阶段 Ctrl+C 触发优雅停机，清理阶段忽略重复 Ctrl+C
    for signame in ('SIGINT', 'SIGBREAK'):
        sig = getattr(signal, signame, None)
        if sig is not None:
            try:
                signal.signal(sig, _sigint_handler)
            except (ValueError, OSError):
                pass

    try:
        if args.stop:
            return do_stop(args, console)
        if args.status:
            return do_status(args, console)

        backend_port = read_config_port('BACKEND_PORT', 8000)
        frontend_port = read_config_port('FRONTEND_PORT', 3000)
        python_exe = sys.executable or 'python'

        console.banner([
            'TestHub One-Click Start（单窗口版）',
            f'前端端口: {frontend_port}    后端端口: {backend_port}',
            'Uvicorn ASGI + Django-Q2 + Scheduler（HTTP + SSE + WebSocket 同端口）',
            f'Python: {python_exe}',
            f'日志目录: {LOG_DIR}',
        ])

        manager = Manager(console, python_exe, keep_infra=args.keep_infra)
        try:
            ensure_mysql(args, console, manager)
            ensure_redis(args, console, manager)

            console.info('  [3] 清理旧进程 ...')
            if args.no_clean:
                console.info('     已通过 --no-clean 跳过')
            else:
                # 先清理重复的 worker（旧版 start.bat 会不断堆积 qcluster/调度器）
                clean_duplicate_workers(console)
                clean_stale_port(backend_port, console)
                clean_stale_port(frontend_port, console)
                console.info('     清理完成')

            if not (args.no_qcluster or args.no_workers):
                console.info('  [4] 启动 Django-Q2 集群 ...')
                manager.start('qcluster', [python_exe, 'manage.py', 'qcluster'], cwd=BACKEND_DIR)
            if not (args.no_scheduler or args.no_workers):
                console.info('  [5] 启动定时任务调度器 ...')
                manager.start('scheduler', [python_exe, 'manage.py', 'run_all_scheduled_tasks'], cwd=BACKEND_DIR)
            if not args.no_frontend:
                console.info('  [6] 启动前端 ...')
                npm_cmd = ['npm', 'run', 'dev'] if not IS_WINDOWS else 'cmd /c npm run dev'
                manager.start('frontend', npm_cmd, cwd=FRONTEND_DIR)

            console.info('')
            console.banner([
                '所有服务已启动（单窗口模式）',
                f'前端:     http://localhost:{frontend_port}/',
                f'后端:     http://localhost:{backend_port}/',
                f'API 文档: http://localhost:{backend_port}/api/docs/',
                f'Admin:    http://localhost:{backend_port}/admin/   (admin / admin123)',
                '',
                f'日志:     logs/start/<服务名>.log',
                '停止服务: 在此窗口按 Ctrl+C（或运行 stop.bat）',
            ])

            if args.no_backend:
                console.info('  已通过 --no-backend 跳过后端，按 Ctrl+C 停止其他服务 ...')
                try:
                    while manager.any_alive():
                        time.sleep(0.5)
                except KeyboardInterrupt:
                    pass
            else:
                try:
                    run_backend(args, console, backend_port)
                except KeyboardInterrupt:
                    pass
                except SystemExit as exc:
                    if exc.code:
                        console.warn(f'后端异常退出（exit code {exc.code}）')
        finally:
            global _SHUTTING_DOWN
            _SHUTTING_DOWN = True
            manager.shutdown()
            if manager.services:
                console.rule('服务状态')
                for line in manager.status_lines():
                    console.info(line)
            console.info('')
            console.info('  全部停止完成，窗口即将关闭。若出现 "Terminate batch job (Y/N)?" 直接按任意键即可。')
        return 0
    except KeyboardInterrupt:
        # 清理阶段被强制中断（如连续 Ctrl+C 或直接关闭窗口）
        return 130
    except Exception as exc:  # noqa: BLE001
        console.info('')
        console.warn(f'启动器异常: {exc!r}')
        console.warn(f'详细日志: {LOG_DIR}')
        return 1
    finally:
        console.close()


if __name__ == '__main__':
    sys.exit(main())
