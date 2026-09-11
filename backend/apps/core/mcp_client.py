"""
轻量 MCP 客户端：通过 stdio / SSE / HTTP 拉取 tools/list
"""
from __future__ import annotations

import json
import logging
import os
import queue
import subprocess
import threading
import time
from typing import Any
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)

# Playwright MCP 已知工具（实连失败时作为预设回退）
PLAYWRIGHT_PRESET_TOOLS = [
    'mcp_playwright_browser_click',
    'mcp_playwright_browser_close',
    'mcp_playwright_browser_console_messages',
    'mcp_playwright_browser_drag',
    'mcp_playwright_browser_evaluate',
    'mcp_playwright_browser_file_upload',
    'mcp_playwright_browser_fill_form',
    'mcp_playwright_browser_handle_dialog',
    'mcp_playwright_browser_hover',
    'mcp_playwright_browser_install',
    'mcp_playwright_browser_navigate',
    'mcp_playwright_browser_navigate_back',
    'mcp_playwright_browser_network_requests',
    'mcp_playwright_browser_press_key',
    'mcp_playwright_browser_resize',
    'mcp_playwright_browser_run_code',
    'mcp_playwright_browser_select_option',
    'mcp_playwright_browser_snapshot',
    'mcp_playwright_browser_tabs',
    'mcp_playwright_browser_take_screenshot',
    'mcp_playwright_browser_type',
    'mcp_playwright_browser_wait_for',
    'mcp_playwright_browser_navigate_forward',
    'mcp_playwright_browser_pdf_save',
    'mcp_playwright_browser_start_tracing',
    'mcp_playwright_browser_stop_tracing',
    'mcp_playwright_browser_verify_element_visible',
]

MCP_PRESETS = [
    {
        'key': 'playwright',
        'name': 'playwright',
        'label': 'Playwright MCP',
        'description': 'Playwright MCP 浏览器自动化测试工具',
        'transport': 'stdio',
        'command': 'npx',
        'args': ['-y', '@playwright/mcp@latest'],
        'env': {},
        'url': '',
        'fallback_tools': PLAYWRIGHT_PRESET_TOOLS,
    },
]


def get_preset(key: str) -> dict | None:
    for item in MCP_PRESETS:
        if item['key'] == key:
            return item
    return None


def list_presets_public() -> list[dict]:
    """前端展示用预设（不含内部 fallback）。"""
    result = []
    for item in MCP_PRESETS:
        result.append({
            'key': item['key'],
            'name': item['name'],
            'label': item['label'],
            'description': item['description'],
            'transport': item['transport'],
            'command': item['command'],
            'args': item['args'],
            'env': item['env'],
            'url': item.get('url') or '',
        })
    return result


def _jsonrpc(method: str, params: dict | None = None, req_id: int = 1) -> dict:
    msg: dict[str, Any] = {'jsonrpc': '2.0', 'id': req_id, 'method': method}
    if params is not None:
        msg['params'] = params
    return msg


def _encode_stdio_message(payload: dict) -> bytes:
    body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
    return f'Content-Length: {len(body)}\r\n\r\n'.encode('ascii') + body


def _parse_stdio_buffer(buffer: bytes) -> tuple[list[dict], bytes]:
    messages: list[dict] = []
    while True:
        if b'\r\n\r\n' in buffer:
            header, _, rest = buffer.partition(b'\r\n\r\n')
            length = None
            for line in header.split(b'\r\n'):
                if line.lower().startswith(b'content-length:'):
                    try:
                        length = int(line.split(b':', 1)[1].strip())
                    except ValueError:
                        length = None
            if length is None:
                buffer = rest
                continue
            if len(rest) < length:
                return messages, header + b'\r\n\r\n' + rest
            body = rest[:length]
            buffer = rest[length:]
            try:
                messages.append(json.loads(body.decode('utf-8')))
            except json.JSONDecodeError:
                pass
            continue

        if b'\n' in buffer:
            line, _, buffer = buffer.partition(b'\n')
            line = line.strip()
            if not line or line.lower().startswith(b'content-length:'):
                continue
            try:
                messages.append(json.loads(line.decode('utf-8')))
            except json.JSONDecodeError:
                continue
            continue
        break
    return messages, buffer


def list_tools_stdio(command: str, args: list | None = None, env: dict | None = None, timeout: float = 30.0) -> list[str]:
    if not command:
        raise ValueError('stdio 传输需要填写启动命令')

    run_env = os.environ.copy()
    if env:
        run_env.update({str(k): str(v) for k, v in env.items()})

    cmd = [command] + list(args or [])
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=run_env,
        shell=False,
    )

    out_q: queue.Queue[bytes] = queue.Queue()

    def _pump():
        try:
            while True:
                chunk = proc.stdout.read(4096) if proc.stdout else b''
                if not chunk:
                    break
                out_q.put(chunk)
        except Exception:
            pass

    reader = threading.Thread(target=_pump, daemon=True)
    reader.start()

    try:
        assert proc.stdin is not None
        init = _jsonrpc(
            'initialize',
            {
                'protocolVersion': '2024-11-05',
                'capabilities': {},
                'clientInfo': {'name': 'testhub', 'version': '1.0'},
            },
            req_id=1,
        )
        notified = {'jsonrpc': '2.0', 'method': 'notifications/initialized'}
        tools_req = _jsonrpc('tools/list', {}, req_id=2)

        proc.stdin.write(_encode_stdio_message(init))
        proc.stdin.flush()
        time.sleep(0.4)
        proc.stdin.write(_encode_stdio_message(notified))
        proc.stdin.write(_encode_stdio_message(tools_req))
        proc.stdin.flush()

        buffer = b''
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                buffer += out_q.get(timeout=0.2)
            except queue.Empty:
                if proc.poll() is not None and out_q.empty():
                    break
                continue
            messages, buffer = _parse_stdio_buffer(buffer)
            for msg in messages:
                if msg.get('id') == 2 and 'result' in msg:
                    tools = msg['result'].get('tools') or []
                    return [t.get('name') for t in tools if isinstance(t, dict) and t.get('name')]
                if msg.get('id') == 2 and 'error' in msg:
                    raise RuntimeError(msg['error'].get('message') or str(msg['error']))

        stderr = ''
        try:
            if proc.stderr:
                stderr = proc.stderr.read().decode('utf-8', errors='ignore')[:800]
        except Exception:
            pass
        raise RuntimeError(stderr.strip() or '未能从 MCP 服务器获取工具列表（超时）')
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


def list_tools_http(url: str, timeout: float = 20.0) -> list[str]:
    if not url:
        raise ValueError('sse/http 传输需要填写服务器 URL')

    base = url.rstrip('/') + '/'
    payload = _jsonrpc('tools/list', {}, req_id=1)

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        candidates = [url, urljoin(base, 'message'), urljoin(base, 'mcp'), urljoin(base, 'rpc')]
        last_error = None
        for endpoint in candidates:
            try:
                resp = client.post(endpoint, json=payload, headers={'Content-Type': 'application/json'})
                if resp.status_code >= 400:
                    last_error = f'{endpoint} -> HTTP {resp.status_code}'
                    continue
                try:
                    data = resp.json()
                except Exception:
                    data = None
                if isinstance(data, dict) and 'result' in data:
                    tools = data['result'].get('tools') or []
                    return [t.get('name') for t in tools if isinstance(t, dict) and t.get('name')]
                for line in (resp.text or '').splitlines():
                    line = line.strip()
                    if not line.startswith('data:'):
                        continue
                    try:
                        event = json.loads(line[5:].strip())
                    except json.JSONDecodeError:
                        continue
                    if isinstance(event, dict) and 'result' in event:
                        tools = event['result'].get('tools') or []
                        return [t.get('name') for t in tools if isinstance(t, dict) and t.get('name')]
                last_error = f'{endpoint} 响应无法解析'
            except Exception as exc:
                last_error = str(exc)
        raise RuntimeError(last_error or 'HTTP MCP 连接失败')


def _server_field(server, key, default=None):
    if isinstance(server, dict):
        return server.get(key, default)
    return getattr(server, key, default)


def discover_tools(server, allow_preset_fallback: bool = True) -> list[str]:
    transport = _server_field(server, 'transport', 'stdio') or 'stdio'
    name = _server_field(server, 'name', '') or ''

    try:
        if transport == 'stdio':
            return list_tools_stdio(
                _server_field(server, 'command', '') or '',
                _server_field(server, 'args', []) or [],
                _server_field(server, 'env', {}) or {},
            )
        return list_tools_http(_server_field(server, 'url', '') or '')
    except Exception as exc:
        if allow_preset_fallback:
            preset = get_preset('playwright')
            if preset and name == preset['name']:
                logger.warning('MCP 实连失败，使用 Playwright 预设工具列表: %s', exc)
                return list(preset['fallback_tools'])
        raise
