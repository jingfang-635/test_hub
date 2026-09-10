# -*- coding: utf-8 -*-
"""通过 ADB 采集 / 清空 Android logcat"""
from __future__ import annotations

import logging
import platform
import re
import subprocess
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_LOG_RE = re.compile(
    r'^(\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s+'
    r'(\d+)\s+(\d+)\s+'
    r'([VDIWEF])\s+'
    r'(\S+)\s*:\s*(.*)$'
)


def _subprocess_kwargs() -> dict:
    kwargs = {}
    if platform.system() == 'Windows':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return kwargs


def _run_adb(adb_path: str, args: List[str], timeout: int = 15) -> str:
    try:
        result = subprocess.run(
            [adb_path, *args],
            capture_output=True,
            timeout=timeout,
            **_subprocess_kwargs(),
        )
        out = (result.stdout or b'').decode('utf-8', errors='ignore')
        err = (result.stderr or b'').decode('utf-8', errors='ignore')
        return out if out.strip() else err
    except Exception as e:
        logger.debug(f'adb 命令失败 args={args}: {e}')
        return ''


def _get_package_pid(adb_path: str, device_id: str, package: str) -> Optional[str]:
    if not package:
        return None
    # 优先 pidof，兼容失败时回退 ps
    out = _run_adb(adb_path, ['-s', device_id, 'shell', 'pidof', package], timeout=5).strip()
    if out:
        pid = out.split()[0]
        if pid.isdigit():
            return pid

    out = _run_adb(
        adb_path,
        ['-s', device_id, 'shell', f'ps -A | grep {package}'],
        timeout=8,
    )
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and package in parts[-1]:
            # USER PID ... NAME
            for token in parts[1:3]:
                if token.isdigit():
                    return token
    return None


def _parse_log_line(line: str) -> Optional[Dict[str, str]]:
    text = line.rstrip('\r\n')
    if not text or text.startswith('---------'):
        return None
    m = _LOG_RE.match(text)
    if m:
        return {
            'time': m.group(1),
            'pid': m.group(2),
            'tid': m.group(3),
            'level': m.group(4),
            'tag': m.group(5),
            'message': m.group(6),
            'raw': text,
        }
    return {
        'time': '',
        'pid': '',
        'tid': '',
        'level': '',
        'tag': '',
        'message': text,
        'raw': text,
    }


def fetch_device_logs(
    adb_path: str,
    device_id: str,
    *,
    lines: int = 200,
    package: str = '',
    level: str = '',
    keyword: str = '',
) -> Dict[str, Any]:
    """拉取一段 logcat dump（非阻塞 -d）。"""
    try:
        lines = max(50, min(int(lines or 200), 2000))
    except (TypeError, ValueError):
        lines = 200
    level = (level or '').strip().upper()
    package = (package or '').strip()
    keyword = (keyword or '').strip()

    cmd = ['-s', device_id, 'logcat', '-d', '-v', 'threadtime', '-t', str(lines)]
    pid = _get_package_pid(adb_path, device_id, package) if package else None
    if pid:
        cmd.extend(['--pid', pid])
    if level and level in {'V', 'D', 'I', 'W', 'E', 'F'}:
        cmd.append(f'*:{level}')

    raw = _run_adb(adb_path, cmd, timeout=20)
    entries: List[Dict[str, str]] = []
    for line in raw.splitlines():
        item = _parse_log_line(line)
        if not item:
            continue
        if keyword and keyword.lower() not in item['raw'].lower():
            continue
        # 无 pid 过滤能力时，用包名关键字兜底
        if package and not pid and package.lower() not in item['raw'].lower():
            continue
        entries.append(item)

    return {
        'lines': entries,
        'count': len(entries),
        'requested': lines,
        'package': package,
        'pid': pid or '',
        'level': level,
        'keyword': keyword,
        'connected': True,
    }


def clear_device_logs(adb_path: str, device_id: str) -> bool:
    """清空设备 logcat 缓冲区。"""
    out = _run_adb(adb_path, ['-s', device_id, 'logcat', '-c'], timeout=10)
    # 成功时通常无输出；失败时 stderr 会有内容
    lower = (out or '').lower()
    if 'error' in lower or 'failed' in lower:
        logger.warning(f'清空 logcat 可能失败 device={device_id}: {out}')
        return False
    return True
