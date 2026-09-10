# -*- coding: utf-8 -*-
"""通过 ADB 采集 Android 应用级性能指标"""
from __future__ import annotations

import logging
import platform
import re
import subprocess
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def _subprocess_kwargs() -> dict:
    kwargs = {}
    if platform.system() == 'Windows':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return kwargs


def _adb_shell(adb_path: str, device_id: str, command: str, timeout: int = 10) -> str:
    try:
        result = subprocess.run(
            [adb_path, '-s', device_id, 'shell', command],
            capture_output=True,
            timeout=timeout,
            **_subprocess_kwargs(),
        )
        out = (result.stdout or b'').decode('utf-8', errors='ignore')
        err = (result.stderr or b'').decode('utf-8', errors='ignore')
        return out if out.strip() else err
    except Exception as e:
        logger.debug(f'adb shell 失败 device={device_id} cmd={command}: {e}')
        return ''


def list_running_packages(adb_path: str, device_id: str) -> List[str]:
    """返回可选包名：前台 + 运行中进程 + 第三方已安装包（去重排序）。"""
    packages: set = set()

    try:
        from .remote_control import get_foreground_package
        fg = get_foreground_package(adb_path, device_id) or ''
        if fg:
            packages.add(fg)
    except Exception:
        pass

    # 运行中应用（含系统服务时过滤明显非应用名）
    ps = _adb_shell(adb_path, device_id, 'ps -A 2>/dev/null || ps', timeout=8)
    for line in ps.splitlines():
        parts = line.split()
        if len(parts) < 9:
            continue
        name = parts[-1].strip()
        if not name or name in ('NAME', 'CMD'):
            continue
        if '.' in name and not name.startswith('[') and not name.startswith('/'):
            # strip :suffix for process name like com.pkg:push
            base = name.split(':', 1)[0]
            if re.match(r'^[a-zA-Z][\w.]*\.[a-zA-Z][\w.]*$', base):
                packages.add(base)

    # 第三方已安装包
    pm = _adb_shell(adb_path, device_id, 'pm list packages -3', timeout=12)
    for m in re.finditer(r'^package:(.+)$', pm, re.M):
        pkg = m.group(1).strip()
        if pkg:
            packages.add(pkg)

    return sorted(packages)


def collect_app_performance(adb_path: str, device_id: str, package: str = '') -> Dict[str, Any]:
    """采集指定应用一帧性能数据。"""
    data: Dict[str, Any] = {
        'package': package or '',
        'pid': 0,
        'activity': '',
        'cpu_percent': 0.0,
        'pss_mb': 0.0,
        'rss_mb': 0.0,
        'threads': 0,
        'fd_count': 0,
        'fps': 0.0,
        'jank_percent': 0.0,
        'jank_count': 0,
        'total_frames': 0,
        'p50_ms': 0.0,
        'p90_ms': 0.0,
        'errors': [],
    }

    if not package:
        try:
            from .remote_control import get_foreground_package
            package = get_foreground_package(adb_path, device_id) or ''
        except Exception as e:
            data['errors'].append(f'foreground: {e}')
        data['package'] = package

    if not package:
        data['errors'].append('no package')
        return data

    data['package'] = package

    pid = _resolve_pid(adb_path, device_id, package)
    data['pid'] = pid

    try:
        data['activity'] = _parse_activity(adb_path, device_id, package)
    except Exception as e:
        data['errors'].append(f'activity: {e}')

    try:
        data['cpu_percent'] = _parse_app_cpu(adb_path, device_id, package, pid)
    except Exception as e:
        data['errors'].append(f'cpu: {e}')

    try:
        mem = _parse_app_mem(adb_path, device_id, package)
        data.update(mem)
    except Exception as e:
        data['errors'].append(f'mem: {e}')

    if pid:
        try:
            thr_fd = _parse_threads_fd(adb_path, device_id, pid)
            data.update(thr_fd)
        except Exception as e:
            data['errors'].append(f'threads_fd: {e}')

    try:
        gfx = _parse_gfxinfo(adb_path, device_id, package)
        data.update(gfx)
    except Exception as e:
        data['errors'].append(f'gfxinfo: {e}')

    return data


def _resolve_pid(adb_path: str, device_id: str, package: str) -> int:
    # pidof
    text = _adb_shell(adb_path, device_id, f'pidof {package}', timeout=5).strip()
    if text:
        # may return multiple pids
        for part in text.replace('\n', ' ').split():
            if part.isdigit():
                return int(part)

    # dumpsys package / activity
    text = _adb_shell(adb_path, device_id, f'dumpsys activity processes | grep -F {package}', timeout=10)
    m = re.search(r'pid=(\d+)', text)
    if m:
        return int(m.group(1))

    ps = _adb_shell(adb_path, device_id, f'ps -A 2>/dev/null | grep -F {package} || ps | grep -F {package}', timeout=8)
    for line in ps.splitlines():
        if package not in line:
            continue
        parts = line.split()
        # Android ps: USER PID ... NAME
        for i, p in enumerate(parts):
            if p.isdigit() and i >= 1:
                return int(p)
    return 0


def _parse_activity(adb_path: str, device_id: str, package: str) -> str:
    text = _adb_shell(adb_path, device_id, 'dumpsys activity activities', timeout=10)
    # mResumedActivity: ActivityRecord{xxx u0 com.pkg/.MainActivity t123}
    m = re.search(
        rf'mResumedActivity:.*?({re.escape(package)}/[^\s}}]+)',
        text,
    )
    if m:
        return m.group(1)

    m = re.search(
        rf'mCurrentFocus=Window\{{[^\s]+\s+[^\s]+\s+({re.escape(package)}/[^\s}}]+)',
        _adb_shell(adb_path, device_id, 'dumpsys window windows', timeout=8),
    )
    if m:
        return m.group(1)

    # top activity for package
    m = re.search(
        rf'ActivityRecord\{{[^ ]+ [^ ]+ ({re.escape(package)}/[^\s}}]+)',
        text,
    )
    return m.group(1) if m else ''


def _parse_app_cpu(adb_path: str, device_id: str, package: str, pid: int) -> float:
    # dumpsys cpuinfo lines like:  12% 1234/com.pkg: 10% user + 2% kernel
    text = _adb_shell(adb_path, device_id, 'dumpsys cpuinfo', timeout=12)
    if pid:
        m = re.search(rf'^\s*(\d+(?:\.\d+)?)%\s+{pid}/', text, re.M)
        if m:
            return round(float(m.group(1)), 1)
    m = re.search(rf'^\s*(\d+(?:\.\d+)?)%\s+\d+/{re.escape(package)}(?:[:\s]|$)', text, re.M)
    if m:
        return round(float(m.group(1)), 1)

    # top -n 1
    top = _adb_shell(adb_path, device_id, 'top -n 1', timeout=8)
    top = re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', top)
    for line in top.splitlines():
        if package not in line and (not pid or str(pid) not in line):
            continue
        # look for cpu% field near package
        m = re.search(r'(\d+(?:\.\d+)?)%', line)
        if m:
            return round(float(m.group(1)), 1)
    return 0.0


def _parse_app_mem(adb_path: str, device_id: str, package: str) -> Dict[str, float]:
    text = _adb_shell(adb_path, device_id, f'dumpsys meminfo {package}', timeout=12)
    pss_kb = 0.0
    rss_kb = 0.0

    # TOTAL    123456    ... or App Summary TOTAL PSS
    m = re.search(r'TOTAL\s+(\d+)', text)
    if m:
        pss_kb = float(m.group(1))

    m = re.search(r'TOTAL PSS:\s+(\d+)', text, re.I)
    if m:
        pss_kb = float(m.group(1))

    m = re.search(r'TOTAL RSS:\s+(\d+)', text, re.I)
    if m:
        rss_kb = float(m.group(1))

    if not pss_kb:
        m2 = re.search(
            r'^\s*TOTAL\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',
            text,
            re.M,
        )
        if m2:
            pss_kb = float(m2.group(1))

    # App Summary section
    m = re.search(r'App Summary[\s\S]*?TOTAL\s+(\d+)', text, re.I)
    if m and not pss_kb:
        pss_kb = float(m.group(1))

    return {
        'pss_mb': round(pss_kb / 1024.0, 1) if pss_kb else 0.0,
        'rss_mb': round(rss_kb / 1024.0, 1) if rss_kb else 0.0,
    }


def _parse_threads_fd(adb_path: str, device_id: str, pid: int) -> Dict[str, int]:
    status = _adb_shell(adb_path, device_id, f'cat /proc/{pid}/status', timeout=5)
    threads = 0
    m = re.search(r'^Threads:\s+(\d+)', status, re.M)
    if m:
        threads = int(m.group(1))

    # FD count: ls /proc/pid/fd | wc -l  (may need root on some devices)
    fd_text = _adb_shell(
        adb_path,
        device_id,
        f'ls /proc/{pid}/fd 2>/dev/null | wc -l',
        timeout=5,
    ).strip()
    fd_count = 0
    if fd_text.isdigit():
        fd_count = int(fd_text)
    else:
        # FDSize from status as approximate
        m = re.search(r'^FDSize:\s+(\d+)', status, re.M)
        if m:
            fd_count = int(m.group(1))

    return {'threads': threads, 'fd_count': fd_count}


def _parse_gfxinfo(adb_path: str, device_id: str, package: str) -> Dict[str, Any]:
    text = _adb_shell(adb_path, device_id, f'dumpsys gfxinfo {package}', timeout=12)
    result = {
        'fps': 0.0,
        'jank_percent': 0.0,
        'jank_count': 0,
        'total_frames': 0,
        'p50_ms': 0.0,
        'p90_ms': 0.0,
    }
    if not text or 'No process found' in text or 'not found' in text.lower():
        return result

    # Total frames rendered: 1234
    m = re.search(r'Total frames rendered:\s*(\d+)', text, re.I)
    total = int(m.group(1)) if m else 0

    # Janky frames: 12 (1.23%)
    m = re.search(r'Janky frames:\s*(\d+)\s*\((\d+(?:\.\d+)?)%\)', text, re.I)
    jank = int(m.group(1)) if m else 0
    jank_pct = float(m.group(2)) if m else 0.0

    if not m:
        m2 = re.search(r'Janky frames:\s*(\d+)', text, re.I)
        jank = int(m2.group(1)) if m2 else 0
        if total > 0 and jank:
            jank_pct = round(jank / total * 100.0, 1)

    # 50th/90th percentile from HISTOGRAM or profile data
    # "50th percentile: 8ms" / "90th percentile: 12ms"
    m = re.search(r'50th percentile:\s*(\d+(?:\.\d+)?)\s*ms', text, re.I)
    p50 = float(m.group(1)) if m else 0.0
    m = re.search(r'90th percentile:\s*(\d+(?:\.\d+)?)\s*ms', text, re.I)
    p90 = float(m.group(1)) if m else 0.0

    # Estimate FPS from frame timing if available
    # Number of frames / pipeline or "Average FPS: xx"
    fps = 0.0
    m = re.search(r'(?:Average |Avg )?FPS[:\s]+(\d+(?:\.\d+)?)', text, re.I)
    if m:
        fps = float(m.group(1))
    elif total > 0:
        # gfxinfo reset window is typically ~last few seconds; use 1/frameTime if p50 known
        if p50 > 0:
            fps = round(min(1000.0 / p50, 120.0), 1)
        else:
            # fallback: assume ~1s window roughly — keep 0 rather than fake high
            fps = 0.0

    # Also try framestats histogram last lines for percentiles
    if p50 == 0 and p90 == 0:
        p50, p90 = _percentiles_from_histogram(text)

    result.update({
        'fps': round(fps, 1),
        'jank_percent': round(jank_pct, 1),
        'jank_count': jank,
        'total_frames': total,
        'p50_ms': round(p50, 1),
        'p90_ms': round(p90, 1),
    })
    return result


def _percentiles_from_histogram(text: str) -> tuple:
    """Parse 'HISTOGRAM: 5ms=10 8ms=20 ...' style if present."""
    m = re.search(r'HISTOGRAM:\s*(.+)', text, re.I)
    if not m:
        return 0.0, 0.0
    pairs = re.findall(r'(\d+(?:\.\d+)?)ms=(\d+)', m.group(1))
    if not pairs:
        return 0.0, 0.0
    samples = []
    for ms, cnt in pairs:
        samples.extend([float(ms)] * int(cnt))
    if not samples:
        return 0.0, 0.0
    samples.sort()
    n = len(samples)

    def pct(p: float) -> float:
        idx = min(int(n * p), n - 1)
        return samples[idx]

    return pct(0.5), pct(0.9)
