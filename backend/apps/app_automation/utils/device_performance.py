# -*- coding: utf-8 -*-
"""通过 ADB 采集 Android 设备性能指标"""
from __future__ import annotations

import logging
import platform
import re
import subprocess
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def _subprocess_kwargs() -> dict:
    kwargs = {}
    if platform.system() == 'Windows':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return kwargs


def _adb_shell(adb_path: str, device_id: str, command: str, timeout: int = 8) -> str:
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


def _adb_getprop(adb_path: str, device_id: str, key: str) -> str:
    return _adb_shell(adb_path, device_id, f'getprop {key}', timeout=5).strip()


def collect_device_performance(adb_path: str, device_id: str) -> Dict[str, Any]:
    """采集一帧性能数据。"""
    data: Dict[str, Any] = {
        'cpu_percent': 0.0,
        'cpu_cores': 0,
        'mem_percent': 0.0,
        'mem_used_mb': 0.0,
        'mem_total_mb': 0.0,
        'net_rx_bytes': 0,
        'net_tx_bytes': 0,
        'battery_percent': 0,
        'battery_temp': None,
        'battery_status': '',
        'battery_health': '',
        'thermal_status': '',
        'storage_percent': 0.0,
        'storage_used_gb': 0.0,
        'storage_total_gb': 0.0,
        'foreground_package': '',
        'device_info': {
            'brand': '',
            'model': '',
            'android_version': '',
            'sdk': '',
            'resolution': '',
            'density': '',
        },
        'errors': [],
    }

    # CPU
    try:
        cpu = _parse_cpu(adb_path, device_id)
        data.update(cpu)
    except Exception as e:
        data['errors'].append(f'cpu: {e}')

    # Memory
    try:
        mem = _parse_mem(adb_path, device_id)
        data.update(mem)
    except Exception as e:
        data['errors'].append(f'mem: {e}')

    # Network totals (前端算速率)
    try:
        net = _parse_net(adb_path, device_id)
        data.update(net)
    except Exception as e:
        data['errors'].append(f'net: {e}')

    # Battery
    try:
        bat = _parse_battery(adb_path, device_id)
        data.update(bat)
    except Exception as e:
        data['errors'].append(f'battery: {e}')

    # Storage
    try:
        storage = _parse_storage(adb_path, device_id)
        data.update(storage)
    except Exception as e:
        data['errors'].append(f'storage: {e}')

    # Foreground
    try:
        from .remote_control import get_foreground_package
        data['foreground_package'] = get_foreground_package(adb_path, device_id) or ''
    except Exception as e:
        data['errors'].append(f'foreground: {e}')

    # Device info
    try:
        data['device_info'] = _parse_device_info(adb_path, device_id)
    except Exception as e:
        data['errors'].append(f'device_info: {e}')

    return data


def _parse_cpu(adb_path: str, device_id: str) -> Dict[str, Any]:
    cpuinfo = _adb_shell(adb_path, device_id, 'cat /proc/cpuinfo')
    cores = len(re.findall(r'^processor\s*:', cpuinfo, re.M))

    percent = 0.0

    # 优先 top：形如 800%cpu  11%user  0%nice  31%sys 753%idle ...
    top = _adb_shell(adb_path, device_id, 'top -n 1', timeout=8)
    # 去掉 ANSI 转义
    top_clean = re.sub(r'\x1b\[[0-9;?]*[A-Za-z]', '', top)
    m_top = re.search(
        r'(\d+(?:\.\d+)?)%cpu\s+(\d+(?:\.\d+)?)%user\s+(\d+(?:\.\d+)?)%nice\s+'
        r'(\d+(?:\.\d+)?)%sys\s+(\d+(?:\.\d+)?)%idle',
        top_clean,
        re.I,
    )
    if m_top:
        total = float(m_top.group(1))
        idle = float(m_top.group(5))
        percent = ((total - idle) / total * 100.0) if total > 0 else 0.0
    else:
        # dumpsys cpuinfo: "12% TOTAL"
        text = _adb_shell(adb_path, device_id, 'dumpsys cpuinfo', timeout=12)
        m = re.search(r'(\d+(?:\.\d+)?)%\s*TOTAL', text, re.I)
        if m:
            percent = float(m.group(1))
        else:
            # 汇总进程占用（粗略）
            vals = [float(x) for x in re.findall(r'^\s*(\d+(?:\.\d+)?)%\s+\d+/', text, re.M)]
            if vals:
                percent = min(sum(vals[:25]), 100.0)

    return {
        'cpu_percent': round(min(max(percent, 0), 100), 1),
        'cpu_cores': cores or 0,
    }


def _parse_mem(adb_path: str, device_id: str) -> Dict[str, Any]:
    text = _adb_shell(adb_path, device_id, 'cat /proc/meminfo')
    total_kb = _meminfo_kb(text, 'MemTotal')
    avail_kb = _meminfo_kb(text, 'MemAvailable')
    if not avail_kb:
        free_kb = _meminfo_kb(text, 'MemFree')
        cached_kb = _meminfo_kb(text, 'Cached')
        buffers_kb = _meminfo_kb(text, 'Buffers')
        avail_kb = free_kb + cached_kb + buffers_kb
    used_kb = max(total_kb - avail_kb, 0)
    total_mb = total_kb / 1024.0
    used_mb = used_kb / 1024.0
    percent = (used_mb / total_mb * 100.0) if total_mb > 0 else 0.0
    return {
        'mem_percent': round(percent, 1),
        'mem_used_mb': round(used_mb, 1),
        'mem_total_mb': round(total_mb, 1),
    }


def _meminfo_kb(text: str, key: str) -> float:
    m = re.search(rf'^{key}:\s+(\d+)\s*kB', text, re.M | re.I)
    return float(m.group(1)) if m else 0.0


def _parse_net(adb_path: str, device_id: str) -> Dict[str, Any]:
    text = _adb_shell(adb_path, device_id, 'cat /proc/net/dev')
    rx = tx = 0
    for line in text.splitlines():
        if ':' not in line:
            continue
        name, rest = line.split(':', 1)
        iface = name.strip()
        if iface in ('lo',):
            continue
        parts = rest.split()
        if len(parts) < 9:
            continue
        # skip all-zero virtual ifaces lightly
        try:
            rx += int(parts[0])
            tx += int(parts[8])
        except ValueError:
            continue
    return {'net_rx_bytes': rx, 'net_tx_bytes': tx}


def _parse_battery(adb_path: str, device_id: str) -> Dict[str, Any]:
    text = _adb_shell(adb_path, device_id, 'dumpsys battery', timeout=8)
    level = _dump_int(text, 'level')
    temp_raw = _dump_int(text, 'temperature')  # usually tenths of °C
    status_code = _dump_int(text, 'status')
    health_code = _dump_int(text, 'health')
    temp_c = round(temp_raw / 10.0, 1) if temp_raw else None

    status_map = {
        1: 'unknown', 2: 'charging', 3: 'discharging',
        4: 'not charging', 5: 'full',
    }
    health_map = {
        1: 'unknown', 2: 'good', 3: 'overheat', 4: 'dead',
        5: 'over voltage', 6: 'unspecified failure', 7: 'cold',
    }

    thermal = ''
    thermal_err = ''
    try:
        # Android 10+ thermal service; may fail on some devices
        ttext = _adb_shell(adb_path, device_id, 'dumpsys thermalservice', timeout=6)[:2000]
        if 'Exception' in ttext or 'Error' in ttext or 'not found' in ttext.lower():
            thermal_err = ttext.strip().splitlines()[0][:120] if ttext.strip() else 'thermalservice unavailable'
        else:
            m = re.search(r'Current thermal status[:\s]+(\w+)', ttext, re.I)
            thermal = m.group(1) if m else ''
    except Exception as e:
        thermal_err = str(e)[:120]

    result = {
        'battery_percent': int(level or 0),
        'battery_temp': temp_c,
        'battery_status': status_map.get(int(status_code or 0), str(status_code or '')),
        'battery_health': health_map.get(int(health_code or 0), str(health_code or '')),
        'thermal_status': thermal,
    }
    if thermal_err and not thermal:
        result['thermal_status'] = thermal_err
    return result


def _dump_int(text: str, key: str) -> Optional[int]:
    m = re.search(rf'^\s*{key}\s*:\s*(-?\d+)', text, re.M | re.I)
    return int(m.group(1)) if m else None


def _parse_storage(adb_path: str, device_id: str) -> Dict[str, Any]:
    text = _adb_shell(adb_path, device_id, 'df -k /data 2>/dev/null || df /data')
    # Filesystem 1K-blocks Used Available Use% Mounted
    lines = [ln for ln in text.splitlines() if ln.strip() and not ln.lower().startswith('filesystem')]
    if not lines:
        return {}
    parts = lines[-1].split()
    # formats vary
    used = total = 0.0
    percent = 0.0
    try:
        if len(parts) >= 5 and parts[1].isdigit():
            total = float(parts[1]) / (1024 * 1024)  # GB from KB
            used = float(parts[2]) / (1024 * 1024)
            percent = float(parts[4].replace('%', '')) if '%' in parts[4] else (used / total * 100 if total else 0)
        else:
            for p in parts:
                if p.endswith('%'):
                    percent = float(p[:-1])
    except Exception:
        pass
    return {
        'storage_percent': round(percent, 1),
        'storage_used_gb': round(used, 1),
        'storage_total_gb': round(total, 1),
    }


def _parse_device_info(adb_path: str, device_id: str) -> Dict[str, str]:
    brand = _adb_getprop(adb_path, device_id, 'ro.product.brand')
    model = _adb_getprop(adb_path, device_id, 'ro.product.model')
    version = _adb_getprop(adb_path, device_id, 'ro.build.version.release')
    sdk = _adb_getprop(adb_path, device_id, 'ro.build.version.sdk')
    size = _adb_shell(adb_path, device_id, 'wm size').strip()
    density = _adb_shell(adb_path, device_id, 'wm density').strip()
    # Physical size: 1080x2400
    res = ''
    m = re.search(r'(\d+x\d+)', size)
    if m:
        res = m.group(1)
    dens = ''
    m2 = re.search(r'(\d+)', density)
    if m2:
        dens = m2.group(1)
    return {
        'brand': brand,
        'model': model,
        'android_version': version,
        'sdk': sdk,
        'resolution': res,
        'density': dens,
    }
