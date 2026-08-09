# -*- coding: utf-8 -*-
"""APP 设备远程投屏 / 控制：ADB 截图与触控输入"""
from __future__ import annotations

import base64
import io
import logging
import platform
import subprocess
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

KEYCODE_MAP = {
    'BACK': '4',
    'HOME': '3',
    'APP_SWITCH': '187',
    'POWER': '26',
    'VOLUME_UP': '24',
    'VOLUME_DOWN': '25',
    'MENU': '82',
    'ENTER': '66',
    'DEL': '67',
}


def _subprocess_kwargs() -> dict:
    kwargs = {}
    if platform.system() == 'Windows':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return kwargs


def capture_screen_jpeg(
    adb_path: str,
    device_id: str,
    quality: int = 55,
) -> Optional[Tuple[bytes, int, int]]:
    """
    截取设备屏幕并转为 JPEG。
    返回 (jpeg_bytes, width, height)，失败返回 None。
    """
    png_data = _capture_png(adb_path, device_id)
    if not png_data:
        return None

    try:
        from PIL import Image

        img = Image.open(io.BytesIO(png_data))
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')
        elif img.mode == 'L':
            img = img.convert('RGB')

        width, height = img.size
        buf = io.BytesIO()
        img.save(buf, format='JPEG', quality=quality, optimize=True)
        return buf.getvalue(), width, height
    except Exception as e:
        logger.error(f'截图 JPEG 转换失败 device={device_id}: {e}')
        return None


def _capture_png(adb_path: str, device_id: str) -> Optional[bytes]:
    """优先 exec-out，失败则 shell + CRLF 修复。"""
    kwargs = _subprocess_kwargs()

    try:
        result = subprocess.run(
            [adb_path, '-s', device_id, 'exec-out', 'screencap', '-p'],
            capture_output=True,
            timeout=12,
            **kwargs,
        )
        data = result.stdout or b''
        if _is_png(data):
            return data
        # 部分 Windows 环境会把 \n 变成 \r\n
        fixed = data.replace(b'\r\n', b'\n')
        if _is_png(fixed):
            return fixed
    except Exception as e:
        logger.debug(f'exec-out screencap 失败 device={device_id}: {e}')

    try:
        result = subprocess.run(
            [adb_path, '-s', device_id, 'shell', 'screencap', '-p'],
            capture_output=True,
            timeout=12,
            **kwargs,
        )
        data = (result.stdout or b'').replace(b'\r\n', b'\n')
        if _is_png(data):
            return data
    except Exception as e:
        logger.error(f'shell screencap 失败 device={device_id}: {e}')

    return None


def _is_png(data: bytes) -> bool:
    return bool(data) and len(data) > 100 and data[:4] == b'\x89PNG'


def to_data_url_jpeg(jpeg_bytes: bytes) -> str:
    return 'data:image/jpeg;base64,' + base64.b64encode(jpeg_bytes).decode('ascii')


def adb_input_tap(adb_path: str, device_id: str, x: int, y: int) -> bool:
    return _run_adb(
        adb_path, device_id,
        ['shell', 'input', 'tap', str(int(x)), str(int(y))],
    )


def adb_input_swipe(
    adb_path: str,
    device_id: str,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    duration_ms: int = 300,
) -> bool:
    duration_ms = max(50, min(int(duration_ms), 5000))
    return _run_adb(
        adb_path, device_id,
        [
            'shell', 'input', 'swipe',
            str(int(x1)), str(int(y1)),
            str(int(x2)), str(int(y2)),
            str(duration_ms),
        ],
    )


def adb_input_key(adb_path: str, device_id: str, key: str) -> bool:
    keycode = KEYCODE_MAP.get(str(key).upper())
    if not keycode:
        # 允许直接传数字 keycode
        if str(key).isdigit():
            keycode = str(key)
        else:
            logger.warning(f'未知按键: {key}')
            return False
    return _run_adb(adb_path, device_id, ['shell', 'input', 'keyevent', keycode])


def adb_input_text(adb_path: str, device_id: str, text: str) -> bool:
    if not text:
        return False
    # adb input text 空格需用 %s，特殊字符尽量转义
    escaped = (
        text.replace('\\', '\\\\')
        .replace(' ', '%s')
        .replace("'", "\\'")
        .replace('"', '\\"')
        .replace('&', '\\&')
        .replace('<', '\\<')
        .replace('>', '\\>')
        .replace('|', '\\|')
        .replace(';', '\\;')
        .replace('(', '\\(')
        .replace(')', '\\)')
    )
    return _run_adb(adb_path, device_id, ['shell', 'input', 'text', escaped])


def get_foreground_package(adb_path: str, device_id: str) -> str:
    """获取当前前台应用包名。"""
    import re

    try:
        result = subprocess.run(
            [adb_path, '-s', device_id, 'shell', 'dumpsys', 'window', 'windows'],
            capture_output=True,
            timeout=8,
            **_subprocess_kwargs(),
        )
        text = (result.stdout or b'').decode('utf-8', errors='ignore')
        # mCurrentFocus=Window{xxx u0 com.pkg/com.pkg.Activity}
        match = re.search(r'mCurrentFocus=Window\{[^\s]+\s+[^\s]+\s+([^}/\s]+)', text)
        if match:
            return match.group(1)
        match = re.search(r'mFocusedApp=.*?ActivityRecord\{[^ ]+ [^ ]+ ([^}/\s]+)', text)
        if match:
            return match.group(1)
    except Exception as e:
        logger.debug(f'获取前台应用失败 device={device_id}: {e}')

    try:
        result = subprocess.run(
            [adb_path, '-s', device_id, 'shell', 'dumpsys', 'activity', 'activities'],
            capture_output=True,
            timeout=8,
            **_subprocess_kwargs(),
        )
        text = (result.stdout or b'').decode('utf-8', errors='ignore')
        match = re.search(r'mResumedActivity:.*? ([^}/\s]+)/', text)
        if match:
            return match.group(1)
    except Exception:
        pass
    return ''


def _run_adb(adb_path: str, device_id: str, args: list) -> bool:
    try:
        result = subprocess.run(
            [adb_path, '-s', device_id, *args],
            capture_output=True,
            timeout=10,
            **_subprocess_kwargs(),
        )
        if result.returncode != 0:
            stderr = (result.stderr or b'').decode('utf-8', errors='ignore')
            logger.warning(f'ADB 命令失败 device={device_id} args={args}: {stderr}')
            return False
        return True
    except Exception as e:
        logger.error(f'ADB 命令异常 device={device_id} args={args}: {e}')
        return False
