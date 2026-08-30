# -*- coding: utf-8 -*-
"""Figma 设计稿客户端：用 Personal Access Token 拉取页面结构与文本，整理为需求正文。"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 100_000
FIGMA_API_BASE = 'https://api.figma.com/v1'

# https://www.figma.com/design|file|proto/{fileKey}/...
_FIGMA_PATH_RE = re.compile(
    r'^/(?:design|file|proto|board)/([a-zA-Z0-9]+)',
    re.IGNORECASE,
)


class FigmaError(Exception):
    """Figma 业务/配置错误，message 可直接返回给前端。"""

    def __init__(self, message: str, code: str = 'figma_error', status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


@dataclass
class ParsedFigmaUrl:
    file_key: str
    node_id: Optional[str]
    source_url: str


class FigmaClient:
    """封装 URL 解析与 Figma REST 文本抽取。"""

    def __init__(self):
        self.access_token = (getattr(settings, 'FIGMA_ACCESS_TOKEN', '') or '').strip()
        self.api_base = (getattr(settings, 'FIGMA_API_BASE', '') or FIGMA_API_BASE).rstrip('/')

    def ensure_configured(self) -> None:
        if not self.access_token:
            raise FigmaError(
                'Figma 未配置，请在 config.yaml 或环境变量中设置 FIGMA_ACCESS_TOKEN',
                code='not_configured',
                status_code=503,
            )

    @staticmethod
    def parse_url(url: str) -> ParsedFigmaUrl:
        raw = (url or '').strip()
        if not raw:
            raise FigmaError('请输入 Figma 链接', code='invalid_url')

        parsed = urlparse(raw)
        host = (parsed.netloc or '').lower()
        if 'figma.com' not in host:
            raise FigmaError('链接无效：请使用 Figma 设计稿链接', code='invalid_url')

        match = _FIGMA_PATH_RE.match(parsed.path or '')
        if not match:
            raise FigmaError(
                '链接格式不支持：请使用 /design/、/file/ 或 /proto/ 链接',
                code='unsupported_url',
            )

        file_key = match.group(1)
        qs = parse_qs(parsed.query or '')
        node_raw = (qs.get('node-id') or qs.get('node_id') or [''])[0]
        node_id = unquote(node_raw).replace('-', ':').strip() or None

        return ParsedFigmaUrl(file_key=file_key, node_id=node_id, source_url=raw)

    def _headers(self) -> Dict[str, str]:
        return {
            'X-Figma-Token': self.access_token,
            'Accept': 'application/json',
        }

    def _request(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.ensure_configured()
        url = f'{self.api_base}{path}'
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.get(url, headers=self._headers(), params=params or {})
        except httpx.HTTPError as exc:
            logger.warning('Figma 网络请求失败: %s', exc)
            raise FigmaError('Figma 服务暂时不可用，请稍后重试', code='network_error', status_code=502) from exc

        if resp.status_code == 403:
            raise FigmaError(
                '无权访问该 Figma 文件，请确认 Token 权限或文件已分享给 Token 所有者',
                code='permission_denied',
                status_code=403,
            )
        if resp.status_code == 404:
            raise FigmaError('未找到该 Figma 文件或节点', code='not_found', status_code=404)
        if resp.status_code == 401:
            raise FigmaError(
                'Figma Token 无效，请检查 FIGMA_ACCESS_TOKEN',
                code='auth_failed',
                status_code=401,
            )
        if resp.status_code >= 500:
            raise FigmaError('Figma 服务暂时不可用，请稍后重试', code='figma_server_error', status_code=502)
        if resp.status_code >= 400:
            detail = ''
            try:
                detail = (resp.json() or {}).get('err') or (resp.json() or {}).get('message') or ''
            except Exception:
                detail = resp.text[:200]
            raise FigmaError(detail or f'Figma 请求失败 ({resp.status_code})', code='figma_error')

        try:
            return resp.json() or {}
        except Exception as exc:
            raise FigmaError('Figma 返回内容无法解析', code='figma_error') from exc

    @classmethod
    def _walk_text(cls, node: Dict[str, Any], lines: List[str], depth: int = 0) -> None:
        if not isinstance(node, dict):
            return

        ntype = node.get('type') or ''
        name = (node.get('name') or '').strip()
        visible = node.get('visible', True)
        if visible is False:
            return

        if ntype in ('FRAME', 'COMPONENT', 'COMPONENT_SET', 'INSTANCE', 'SECTION', 'GROUP'):
            if name and not name.startswith('_'):
                prefix = '#' * min(depth + 2, 6)
                lines.append(f'{prefix} {name}')

        if ntype == 'TEXT':
            chars = (node.get('characters') or '').strip()
            if chars:
                label = f'{name}: ' if name and name != chars else ''
                lines.append(f'{label}{chars}')

        for child in node.get('children') or []:
            cls._walk_text(child, lines, depth + (1 if ntype in ('FRAME', 'SECTION', 'COMPONENT', 'COMPONENT_SET') else 0))

    @classmethod
    def _extract_from_document(cls, document: Dict[str, Any]) -> str:
        lines: List[str] = []
        cls._walk_text(document, lines, depth=0)
        # 去重连续空行
        cleaned: List[str] = []
        for line in lines:
            if not line.strip():
                if cleaned and cleaned[-1] == '':
                    continue
                cleaned.append('')
            else:
                cleaned.append(line.rstrip())
        return '\n'.join(cleaned).strip()

    def _fetch_comments_text(self, file_key: str) -> str:
        try:
            data = self._request(f'/files/{file_key}/comments')
        except FigmaError:
            return ''
        comments = data.get('comments') or []
        parts: List[str] = []
        for item in comments:
            if item.get('resolved_at'):
                continue
            message = (item.get('message') or '').strip()
            if message:
                parts.append(f'- {message}')
        return '\n'.join(parts)

    def fetch_requirement(self, url: str) -> Dict[str, Any]:
        parsed = self.parse_url(url)

        if parsed.node_id:
            data = self._request(
                f'/files/{parsed.file_key}/nodes',
                params={'ids': parsed.node_id},
            )
            title = (data.get('name') or '').strip() or f'Figma-{parsed.file_key}'
            nodes_map = data.get('nodes') or {}
            node_payload = nodes_map.get(parsed.node_id) or {}
            document = node_payload.get('document') or {}
            if not document:
                raise FigmaError('未找到指定节点内容', code='not_found', status_code=404)
            body = self._extract_from_document(document)
        else:
            data = self._request(f'/files/{parsed.file_key}')
            title = (data.get('name') or '').strip() or f'Figma-{parsed.file_key}'
            document = data.get('document') or {}
            body = self._extract_from_document(document)

        comments = self._fetch_comments_text(parsed.file_key)
        sections = [f'# {title}']
        if body:
            sections.append(body)
        if comments:
            sections.append('## 设计评论 / 批注\n' + comments)

        content = '\n\n'.join(sections).strip()
        if not content or content == f'# {title}':
            raise FigmaError(
                '未能从 Figma 提取到有效文本，请确认画板含文本层或批注',
                code='empty_content',
            )
        if len(content) > MAX_CONTENT_LENGTH:
            raise FigmaError(
                f'解析内容过长（超过 {MAX_CONTENT_LENGTH} 字符），请缩小 node 范围后重试',
                code='content_too_long',
            )

        return {
            'title': title[:200],
            'content': content,
            'source_url': parsed.source_url,
            'file_key': parsed.file_key,
            'node_id': parsed.node_id or '',
        }
