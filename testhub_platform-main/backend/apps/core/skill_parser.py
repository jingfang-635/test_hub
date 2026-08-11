"""
解析 Markdown 格式的 Skill（兼容 Cursor SKILL.md：YAML frontmatter + 正文）
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_RE = re.compile(r'\A---\s*\r?\n(.*?)\r?\n---\s*\r?\n?(.*)\Z', re.DOTALL)
HEADING_RE = re.compile(r'^#\s+(.+)$', re.MULTILINE)


def _as_str(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, list):
        return ', '.join(str(v).strip() for v in value if str(v).strip())
    return str(value).strip()


def _as_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = re.split(r'[,，]', value)
        return [p.strip() for p in parts if p.strip()]
    if isinstance(value, (list, tuple, set)):
        tags = []
        for item in value:
            text = str(item).strip()
            if text:
                tags.append(text)
        return tags
    text = str(value).strip()
    return [text] if text else []


def _slug_from_filename(filename: str | None) -> str:
    if not filename:
        return ''
    stem = Path(filename).stem.strip()
    if not stem:
        return ''
    # SKILL.md / skill.md 本身不是有效技能名
    if stem.lower() in {'skill', 'skills'}:
        return ''
    return stem


def _description_from_body(body: str) -> str:
    text = (body or '').strip()
    if not text:
        return ''
    # 跳过标题，取第一段非空文字
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            if lines:
                break
            continue
        if stripped.startswith('#'):
            if lines:
                break
            continue
        lines.append(stripped)
        if len(' '.join(lines)) >= 160:
            break
    desc = ' '.join(lines).strip()
    return desc[:300]


def parse_skill_markdown(text: str, filename: str | None = None) -> dict:
    """
    解析 Skill Markdown。

    返回:
      name, description, tags, content(完整原文), body(正文), meta(原始 frontmatter)
    """
    raw = text if isinstance(text, str) else str(text or '')
    # 去掉 UTF-8 BOM
    if raw.startswith('\ufeff'):
        raw = raw.lstrip('\ufeff')

    meta: dict = {}
    body = raw
    match = FRONTMATTER_RE.match(raw)
    if match:
        yaml_text = match.group(1) or ''
        body = match.group(2) or ''
        try:
            loaded = yaml.safe_load(yaml_text) or {}
            if isinstance(loaded, dict):
                meta = loaded
        except yaml.YAMLError:
            meta = {}

    name = _as_str(meta.get('name') or meta.get('title') or meta.get('id'))
    if not name:
        heading = HEADING_RE.search(body)
        if heading:
            # 标题若是空格分隔的展示名，转成 kebab-case 风格标识
            title = heading.group(1).strip()
            name = re.sub(r'\s+', '-', title).strip('-').lower() or title
    if not name:
        name = _slug_from_filename(filename)
    if not name:
        raise ValueError('无法识别 Skill 名称，请在 YAML frontmatter 中提供 name，或使用有意义的文件名')

    # 规范化名称：去空白
    name = re.sub(r'\s+', '-', name.strip())

    description = _as_str(
        meta.get('description')
        or meta.get('desc')
        or meta.get('summary')
    )
    if not description:
        description = _description_from_body(body)

    tags = _as_tags(meta.get('tags') or meta.get('tag') or meta.get('labels'))

    return {
        'name': name,
        'description': description,
        'tags': tags,
        'content': raw,
        'body': body,
        'meta': meta,
    }
