"""
接口批量导入解析器：Swagger/OpenAPI、Postman Collection、HAR、cURL
"""
from __future__ import annotations

import json
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlparse

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None


HTTP_METHODS = {'get', 'post', 'put', 'delete', 'patch', 'head', 'options'}


def _uid() -> str:
    return str(uuid.uuid4())


def _normalize_method(method: str) -> str:
    return (method or 'GET').upper()


def _headers_list(headers: Any) -> List[Dict[str, Any]]:
    """将多种 headers 表示统一为前端使用的数组格式"""
    result = []
    if isinstance(headers, list):
        for item in headers:
            if not isinstance(item, dict):
                continue
            key = item.get('key') or item.get('name') or ''
            if not key:
                continue
            result.append({
                'key': key,
                'value': item.get('value', '') or '',
                'description': item.get('description', '') or '',
                'enabled': item.get('enabled', True) is not False and item.get('disabled') is not True,
            })
    elif isinstance(headers, dict):
        for key, value in headers.items():
            if not key:
                continue
            result.append({
                'key': key,
                'value': '' if value is None else str(value),
                'description': '',
                'enabled': True,
            })
    return result


def _params_object(params: Any) -> Dict[str, str]:
    if isinstance(params, dict):
        return {str(k): '' if v is None else str(v) for k, v in params.items()}
    if isinstance(params, list):
        obj = {}
        for item in params:
            if isinstance(item, dict) and item.get('key'):
                if item.get('disabled') is True or item.get('enabled') is False:
                    continue
                obj[str(item['key'])] = '' if item.get('value') is None else str(item.get('value'))
        return obj
    return {}


def _make_item(
    name: str,
    method: str,
    url: str,
    *,
    headers: Any = None,
    params: Any = None,
    body: Any = None,
    description: str = '',
) -> Dict[str, Any]:
    return {
        'temp_id': _uid(),
        'name': name or url or '未命名接口',
        'method': _normalize_method(method),
        'url': url or '',
        'description': description or '',
        'headers': _headers_list(headers),
        'params': _params_object(params),
        'body': body if isinstance(body, dict) else {},
        'auth': {},
        'assertions': [],
        'request_type': 'HTTP',
    }


def _group_result(name: str, groups: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = sum(len(g.get('items') or []) for g in groups)
    return {
        'name': name or '导入接口',
        'groups': groups,
        'total': total,
        'group_count': len(groups),
    }


def load_content(content: str) -> Any:
    """尝试按 JSON / YAML 解析文本内容"""
    text = (content or '').strip()
    if not text:
        raise ValueError('导入内容为空')
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    if yaml is None:
        raise ValueError('无法解析文件内容：非 JSON，且当前环境未安装 PyYAML，无法解析 YAML')
    try:
        data = yaml.safe_load(text)
        if data is None:
            raise ValueError('导入内容为空')
        return data
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f'无法解析文件内容，请确认是有效的 JSON 或 YAML：{exc}') from exc


# ---------------------------------------------------------------------------
# Swagger / OpenAPI
# ---------------------------------------------------------------------------

def _resolve_ref(spec: dict, ref: str) -> Any:
    if not ref or not ref.startswith('#/'):
        return {}
    node: Any = spec
    for part in ref[2:].split('/'):
        if not isinstance(node, dict):
            return {}
        node = node.get(part, {})
    return node


def _schema_example(schema: Any, spec: dict, depth: int = 0) -> Any:
    if not isinstance(schema, dict) or depth > 6:
        return None
    if '$ref' in schema:
        return _schema_example(_resolve_ref(spec, schema['$ref']), spec, depth + 1)
    if 'example' in schema:
        return schema['example']
    if 'default' in schema:
        return schema['default']
    schema_type = schema.get('type')
    if 'allOf' in schema and isinstance(schema['allOf'], list):
        merged = {}
        for part in schema['allOf']:
            val = _schema_example(part, spec, depth + 1)
            if isinstance(val, dict):
                merged.update(val)
        return merged or None
    if schema_type == 'object' or 'properties' in schema:
        props = schema.get('properties') or {}
        obj = {}
        for key, prop in props.items():
            obj[key] = _schema_example(prop, spec, depth + 1)
        return obj
    if schema_type == 'array':
        return [_schema_example(schema.get('items') or {}, spec, depth + 1)]
    if schema_type == 'integer':
        return 0
    if schema_type == 'number':
        return 0
    if schema_type == 'boolean':
        return False
    if schema_type == 'string':
        return schema.get('format') or ''
    return None


def _swagger_server_url(spec: dict) -> str:
    # OpenAPI 3
    servers = spec.get('servers') or []
    if servers and isinstance(servers[0], dict) and servers[0].get('url'):
        return str(servers[0]['url']).rstrip('/')
    # Swagger 2
    host = spec.get('host') or ''
    base_path = spec.get('basePath') or ''
    schemes = spec.get('schemes') or ['https']
    if host:
        return f"{schemes[0]}://{host}{base_path}".rstrip('/')
    return ''


def parse_swagger(content: str) -> Dict[str, Any]:
    spec = load_content(content)
    if not isinstance(spec, dict):
        raise ValueError('Swagger/OpenAPI 内容格式不正确')

    is_openapi3 = bool(spec.get('openapi'))
    is_swagger2 = str(spec.get('swagger', '')).startswith('2')
    if not is_openapi3 and not is_swagger2:
        # 宽松兼容：有 paths 也尝试解析
        if 'paths' not in spec:
            raise ValueError('不是有效的 Swagger/OpenAPI 文档（缺少 openapi/swagger 或 paths）')

    info = spec.get('info') or {}
    title = info.get('title') or 'Swagger Import'
    base_url = _swagger_server_url(spec)
    paths = spec.get('paths') or {}

    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for path, path_item in paths.items():
        if not isinstance(path_item, dict):
            continue
        shared_params = path_item.get('parameters') or []
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue

            tags = operation.get('tags') or ['默认分组']
            group_name = tags[0] if tags else '默认分组'
            name = operation.get('summary') or operation.get('operationId') or f'{method.upper()} {path}'
            description = operation.get('description') or ''

            params_list = list(shared_params) + list(operation.get('parameters') or [])
            query_params = {}
            headers = []
            path_url = path

            for param in params_list:
                if not isinstance(param, dict):
                    continue
                if '$ref' in param:
                    param = _resolve_ref(spec, param['$ref'])
                    if not isinstance(param, dict):
                        continue
                where = param.get('in')
                pname = param.get('name')
                if not pname:
                    continue
                example = param.get('example')
                if example is None:
                    schema = param.get('schema') or {}
                    example = schema.get('example', schema.get('default', ''))
                if where == 'query':
                    query_params[pname] = '' if example is None else str(example)
                elif where == 'header':
                    headers.append({'key': pname, 'value': '' if example is None else str(example), 'enabled': True})
                elif where == 'path':
                    path_url = path_url.replace('{' + pname + '}', str(example if example not in (None, '') else f'{{{{{pname}}}}}'))

            body: Dict[str, Any] = {}
            if is_openapi3:
                request_body = operation.get('requestBody') or {}
                if '$ref' in request_body:
                    request_body = _resolve_ref(spec, request_body['$ref'])
                content_map = (request_body or {}).get('content') or {}
                if 'application/json' in content_map:
                    schema = content_map['application/json'].get('schema') or {}
                    example = content_map['application/json'].get('example')
                    if example is None:
                        example = _schema_example(schema, spec)
                    body = {'type': 'json', 'data': example if example is not None else {}}
                    headers.append({'key': 'Content-Type', 'value': 'application/json', 'enabled': True})
                elif 'application/x-www-form-urlencoded' in content_map:
                    schema = content_map['application/x-www-form-urlencoded'].get('schema') or {}
                    example = _schema_example(schema, spec) or {}
                    data = [{'key': k, 'value': '' if v is None else str(v), 'enabled': True}
                            for k, v in (example.items() if isinstance(example, dict) else [])]
                    body = {'type': 'x-www-form-urlencoded', 'data': data}
                elif 'multipart/form-data' in content_map:
                    schema = content_map['multipart/form-data'].get('schema') or {}
                    example = _schema_example(schema, spec) or {}
                    data = [{'key': k, 'value': '' if v is None else str(v), 'type': 'text', 'enabled': True}
                            for k, v in (example.items() if isinstance(example, dict) else [])]
                    body = {'type': 'form-data', 'data': data}
            else:
                body_param = next((p for p in params_list if isinstance(p, dict) and p.get('in') == 'body'), None)
                if body_param:
                    schema = body_param.get('schema') or {}
                    example = body_param.get('example')
                    if example is None:
                        example = _schema_example(schema, spec)
                    body = {'type': 'json', 'data': example if example is not None else {}}
                    headers.append({'key': 'Content-Type', 'value': 'application/json', 'enabled': True})
                form_params = [p for p in params_list if isinstance(p, dict) and p.get('in') == 'formData']
                if form_params:
                    data = []
                    for p in form_params:
                        data.append({
                            'key': p.get('name', ''),
                            'value': '' if p.get('default') is None else str(p.get('default')),
                            'type': 'file' if p.get('type') == 'file' else 'text',
                            'enabled': True,
                        })
                    body = {'type': 'form-data', 'data': data}

            url = f'{base_url}{path_url}' if base_url else path_url
            item = _make_item(name, method, url, headers=headers, params=query_params, body=body, description=description)
            grouped.setdefault(group_name, []).append(item)

    groups = [{'name': name, 'items': items} for name, items in grouped.items()]
    if not groups:
        raise ValueError('未从 Swagger/OpenAPI 文档中解析到任何接口')
    return _group_result(title, groups)


# ---------------------------------------------------------------------------
# Postman Collection v2.x
# ---------------------------------------------------------------------------

def _postman_url(url_field: Any) -> Tuple[str, Dict[str, str]]:
    params: Dict[str, str] = {}
    if isinstance(url_field, str):
        parsed = urlparse(url_field)
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
        return url_field, params
    if isinstance(url_field, dict):
        raw = url_field.get('raw')
        query = url_field.get('query') or []
        for q in query:
            if isinstance(q, dict) and q.get('key') and not q.get('disabled'):
                params[str(q['key'])] = '' if q.get('value') is None else str(q.get('value'))
        if raw:
            return str(raw), params
        host = url_field.get('host') or []
        path = url_field.get('path') or []
        protocol = url_field.get('protocol') or 'https'
        if isinstance(host, list):
            host_str = '.'.join(str(h) for h in host)
        else:
            host_str = str(host)
        if isinstance(path, list):
            path_str = '/'.join(str(p) for p in path)
        else:
            path_str = str(path).lstrip('/')
        url = f'{protocol}://{host_str}/{path_str}' if host_str else f'/{path_str}'
        return url, params
    return '', params


def _postman_body(body_field: Any) -> Dict[str, Any]:
    if not isinstance(body_field, dict):
        return {}
    mode = body_field.get('mode')
    if mode == 'raw':
        raw = body_field.get('raw') or ''
        options = body_field.get('options') or {}
        lang = ((options.get('raw') or {}).get('language') or '').lower()
        if lang == 'json' or (raw.strip().startswith('{') or raw.strip().startswith('[')):
            try:
                return {'type': 'json', 'data': json.loads(raw)}
            except Exception:
                return {'type': 'raw', 'data': raw}
        return {'type': 'raw', 'data': raw}
    if mode == 'urlencoded':
        data = []
        for item in body_field.get('urlencoded') or []:
            if not isinstance(item, dict) or not item.get('key'):
                continue
            data.append({
                'key': item['key'],
                'value': item.get('value') or '',
                'description': item.get('description') or '',
                'enabled': not item.get('disabled', False),
            })
        return {'type': 'x-www-form-urlencoded', 'data': data}
    if mode == 'formdata':
        data = []
        for item in body_field.get('formdata') or []:
            if not isinstance(item, dict) or not item.get('key'):
                continue
            data.append({
                'key': item['key'],
                'value': item.get('value') or '',
                'type': item.get('type') or 'text',
                'description': item.get('description') or '',
                'enabled': not item.get('disabled', False),
            })
        return {'type': 'form-data', 'data': data}
    if mode == 'file':
        return {'type': 'binary', 'data': None}
    return {}


def _walk_postman_items(items: List[Any], folder_path: str, grouped: Dict[str, List[Dict[str, Any]]]):
    for item in items or []:
        if not isinstance(item, dict):
            continue
        name = item.get('name') or '未命名'
        if 'item' in item and isinstance(item['item'], list) and 'request' not in item:
            next_path = f'{folder_path}/{name}' if folder_path else name
            _walk_postman_items(item['item'], next_path, grouped)
            continue

        request = item.get('request')
        if not request:
            if 'item' in item:
                next_path = f'{folder_path}/{name}' if folder_path else name
                _walk_postman_items(item['item'], next_path, grouped)
            continue

        if isinstance(request, str):
            method, url, headers, params, body, description = 'GET', request, [], {}, {}, ''
        else:
            method = request.get('method') or 'GET'
            url, params = _postman_url(request.get('url'))
            headers = request.get('header') or []
            body = _postman_body(request.get('body'))
            description = ''
            desc = request.get('description')
            if isinstance(desc, dict):
                description = desc.get('content') or ''
            elif isinstance(desc, str):
                description = desc

        group_name = folder_path.split('/')[0] if folder_path else '默认分组'
        # 更深层级：用完整 folder 作为分组名更贴近图片（微信/邮件）
        if folder_path:
            # 取第一层文件夹作为分组
            group_name = folder_path.split('/')[0]
        grouped.setdefault(group_name, []).append(
            _make_item(name, method, url, headers=headers, params=params, body=body, description=description)
        )


def parse_postman(content: str) -> Dict[str, Any]:
    data = load_content(content)
    if not isinstance(data, dict):
        raise ValueError('Postman Collection 内容格式不正确')

    info = data.get('info') or {}
    # 兼容 Postman v2 / v2.1
    schema = str(info.get('schema') or '')
    if 'item' not in data and 'requests' not in data:
        raise ValueError('不是有效的 Postman Collection（缺少 item）')

    title = info.get('name') or 'Postman Import'
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    if 'item' in data:
        _walk_postman_items(data.get('item') or [], '', grouped)
    else:
        # 极旧格式兼容
        for req in data.get('requests') or []:
            if not isinstance(req, dict):
                continue
            grouped.setdefault('默认分组', []).append(
                _make_item(
                    req.get('name') or '未命名',
                    req.get('method') or 'GET',
                    req.get('url') or '',
                    headers=req.get('headers') or [],
                    body={'type': 'raw', 'data': req.get('rawModeData') or ''},
                )
            )

    groups = [{'name': name, 'items': items} for name, items in grouped.items()]
    if not groups:
        raise ValueError('未从 Postman Collection 中解析到任何接口')
    return _group_result(title, groups)


# ---------------------------------------------------------------------------
# HAR
# ---------------------------------------------------------------------------

def parse_har(content: str) -> Dict[str, Any]:
    data = load_content(content)
    if not isinstance(data, dict):
        raise ValueError('HAR 内容格式不正确')

    log = data.get('log') or data
    entries = log.get('entries') or []
    if not entries:
        raise ValueError('HAR 文件中没有请求条目')

    title = (log.get('creator') or {}).get('name') or 'HAR Import'
    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        req = entry.get('request') or {}
        method = req.get('method') or 'GET'
        url = req.get('url') or ''
        parsed = urlparse(url)
        group_name = parsed.netloc or '默认分组'

        headers = []
        for h in req.get('headers') or []:
            if not isinstance(h, dict):
                continue
            name = h.get('name') or ''
            if name.startswith(':'):  # HTTP/2 pseudo headers
                continue
            headers.append({'key': name, 'value': h.get('value') or '', 'enabled': True})

        params = {}
        for q in req.get('queryString') or []:
            if isinstance(q, dict) and q.get('name'):
                params[str(q['name'])] = '' if q.get('value') is None else str(q['value'])

        body: Dict[str, Any] = {}
        post_data = req.get('postData') or {}
        if post_data:
            mime = (post_data.get('mimeType') or '').lower()
            text = post_data.get('text') or ''
            if 'application/json' in mime:
                try:
                    body = {'type': 'json', 'data': json.loads(text) if text else {}}
                except Exception:
                    body = {'type': 'raw', 'data': text}
            elif 'x-www-form-urlencoded' in mime:
                data_list = []
                for p in post_data.get('params') or []:
                    if isinstance(p, dict) and p.get('name'):
                        data_list.append({
                            'key': p['name'],
                            'value': p.get('value') or '',
                            'enabled': True,
                        })
                if not data_list and text:
                    data_list = [
                        {'key': k, 'value': v, 'enabled': True}
                        for k, v in parse_qsl(text, keep_blank_values=True)
                    ]
                body = {'type': 'x-www-form-urlencoded', 'data': data_list}
            elif 'multipart/form-data' in mime:
                data_list = []
                for p in post_data.get('params') or []:
                    if isinstance(p, dict) and p.get('name'):
                        data_list.append({
                            'key': p['name'],
                            'value': p.get('value') or '',
                            'type': 'file' if p.get('fileName') else 'text',
                            'enabled': True,
                        })
                body = {'type': 'form-data', 'data': data_list}
            else:
                body = {'type': 'raw', 'data': text}

        path = parsed.path or '/'
        name = f'{method.upper()} {path}'
        item = _make_item(name, method, url, headers=headers, params=params, body=body)
        grouped.setdefault(group_name, []).append(item)

    groups = [{'name': name, 'items': items} for name, items in grouped.items()]
    return _group_result(title, groups)


# ---------------------------------------------------------------------------
# cURL（简单解析，便于导入弹窗统一入口）
# ---------------------------------------------------------------------------

def parse_curl(content: str) -> Dict[str, Any]:
    text = (content or '').strip()
    if not text:
        raise ValueError('cURL 内容为空')
    # 去掉续行符
    text = text.replace('\\\n', ' ').replace('\\\r\n', ' ')

    method = 'GET'
    url = ''
    headers = []
    body_raw = None

    # method
    m = re.search(r'(?:^|\s)(?:-X|--request)\s+[\'"]?([A-Za-z]+)[\'"]?', text)
    if m:
        method = m.group(1).upper()

    # url: first http(s) token or curl argument
    m = re.search(r'curl\s+(?:--location\s+)?[\'"]?(https?://[^\s\'"]+)[\'"]?', text, re.I)
    if not m:
        m = re.search(r'[\'"]?(https?://[^\s\'"]+)[\'"]?', text, re.I)
    if m:
        url = m.group(1)

    # headers
    for hm in re.finditer(r'(?:^|\s)(?:-H|--header)\s+[\'"]([^\'"]+)[\'"]', text):
        line = hm.group(1)
        if ':' in line:
            key, value = line.split(':', 1)
            headers.append({'key': key.strip(), 'value': value.strip(), 'enabled': True})

    # body
    bm = re.search(r'(?:^|\s)(?:-d|--data|--data-raw|--data-binary)\s+[\'"]([\s\S]*?)[\'"]', text)
    if bm:
        body_raw = bm.group(1)
        if method == 'GET':
            method = 'POST'

    body: Dict[str, Any] = {}
    if body_raw is not None:
        try:
            body = {'type': 'json', 'data': json.loads(body_raw)}
        except Exception:
            if '=' in body_raw and not body_raw.strip().startswith('{'):
                data = [{'key': k, 'value': v, 'enabled': True} for k, v in parse_qsl(body_raw, keep_blank_values=True)]
                body = {'type': 'x-www-form-urlencoded', 'data': data}
            else:
                body = {'type': 'raw', 'data': body_raw}

    if not url:
        raise ValueError('未能从 cURL 中解析出 URL')

    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    name = f'{method} {parsed.path or "/"}'
    item = _make_item(name, method, url, headers=headers, params=params, body=body)
    return _group_result('cURL Import', [{'name': '默认分组', 'items': [item]}])


def parse_import(format_type: str, content: str) -> Dict[str, Any]:
    fmt = (format_type or '').lower().strip()
    if fmt in ('swagger', 'openapi', 'swagger/openapi'):
        return parse_swagger(content)
    if fmt in ('postman',):
        return parse_postman(content)
    if fmt in ('har',):
        return parse_har(content)
    if fmt in ('curl', 'cURL'):
        return parse_curl(content)
    raise ValueError(f'不支持的导入格式: {format_type}')
