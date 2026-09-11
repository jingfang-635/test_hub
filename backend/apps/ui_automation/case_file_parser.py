"""
功能用例文件解析器（探索测试 - 功能用例驱动模式）

支持上传 Excel(.xlsx/.xls)、XMind(.xmind)、Markdown(.md/.markdown/.txt) 用例文件，
解析为统一结构：
  {
    "format": "excel" | "xmind" | "markdown",
    "case_count": int,
    "cases": [{"name": str, "precondition": str, "steps": [str, ...], "expected": str}],
    "text": "规范化后的用例文本（写入 AIExplorationTask.data_content，供 LLM 规划）",
  }

设计原则：
  - 零强依赖：xlsx/xmind 本质都是 zip 包，优先使用标准库 zipfile + xml/json 解析，
    openpyxl/xlrd 存在时优先使用（解析更完整），缺失时自动回退标准库实现。
  - 解析失败抛出 CaseFileParseError，由 View 层转为 400 响应。
"""
from __future__ import annotations

import io
import json
import re
import zipfile
from xml.etree import ElementTree as ET

SUPPORTED_EXTENSIONS = ('.xlsx', '.xls', '.xmind', '.md', '.markdown', '.txt')
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

_XLSX_NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'


class CaseFileParseError(Exception):
    """用例文件解析失败"""


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def parse_case_file(filename: str, data: bytes) -> dict:
    """解析上传的用例文件，返回统一结构。"""
    if not data:
        raise CaseFileParseError('文件内容为空')
    if len(data) > MAX_FILE_SIZE:
        raise CaseFileParseError('文件过大，请上传 10MB 以内的用例文件')

    ext = _get_ext(filename)
    if ext not in SUPPORTED_EXTENSIONS:
        raise CaseFileParseError(
            f'不支持的文件类型：{ext or "未知"}，仅支持 Excel(.xlsx/.xls)、XMind(.xmind)、Markdown(.md/.txt)'
        )

    if ext in ('.md', '.markdown', '.txt'):
        result = _parse_markdown(data)
    elif ext == '.xmind':
        result = _parse_xmind(data)
    elif ext == '.xlsx':
        result = _parse_xlsx(data)
    else:  # .xls
        result = _parse_xls(data)

    text = _cases_to_text(result['cases'], result['format'])
    result['text'] = text
    result['case_count'] = len(result['cases'])
    return result


def _get_ext(filename: str) -> str:
    if not filename:
        return ''
    idx = filename.rfind('.')
    return filename[idx:].lower() if idx >= 0 else ''


# ---------------------------------------------------------------------------
# Markdown / 纯文本
# ---------------------------------------------------------------------------

def _parse_markdown(data: bytes) -> dict:
    text = _decode_text(data)
    # Markdown 用例本身就是 LLM 友好的文本，按标题/列表粗分用例用于计数
    cases = _split_markdown_cases(text)
    return {'format': 'markdown', 'cases': cases}


def _decode_text(data: bytes) -> str:
    for enc in ('utf-8-sig', 'utf-8', 'gbk', 'gb18030'):
        try:
            return data.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode('utf-8', errors='ignore')


def _split_markdown_cases(text: str) -> list[dict]:
    """从 Markdown 文本中提取用例：

    - 标题行（# / ## ...）视为用例或分组名称；
    - 只有标题没有正文的块视为模块/分组名，作为后续用例的"所属模块"；
    - 列表项去掉 - / * / 1. 等符号；
    - 以"预期/期望/断言/expected"开头的行归入预期结果。
    """
    cases: list[dict] = []
    current_section = ''
    current_name = ''
    current_lines: list[str] = []

    def flush():
        nonlocal current_section
        body = [l.strip() for l in current_lines if l.strip()]
        if not current_name and not body:
            return
        if not body:
            # 仅有标题、无正文：视为模块/分组标题
            current_section = current_name
            return
        steps, expected = _split_md_steps(body)
        cases.append({
            'name': current_name or f'用例{len(cases) + 1}',
            'precondition': f'所属模块：{current_section}' if current_section else '',
            'steps': steps or ['\n'.join(body)],
            'expected': expected,
        })

    for line in text.splitlines():
        # markdown 标题：# / ## / ### ...
        m = re.match(r'^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$', line)
        if m:
            flush()
            current_name = m.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    flush()

    if not cases:
        steps, expected = _split_md_steps([l for l in text.splitlines() if l.strip()])
        cases = [{
            'name': 'Markdown 用例',
            'precondition': '',
            'steps': steps or [text.strip()],
            'expected': expected,
        }]
    return cases


def _split_md_steps(lines: list[str]) -> tuple[list[str], str]:
    """清理 Markdown 列表符号，并将"预期/期望/断言"行拆分为预期结果。"""
    steps: list[str] = []
    expected: list[str] = []
    for line in lines:
        # 去掉无序列表（- / * / +，含复选框）、有序列表（1. / 1) / （1））、引用符
        s = re.sub(
            r'^\s*(?:[-*+]\s+(\[[ xX]\]\s*)?|\d+\s*[.、)）]\s*|[（(]\s*\d+\s*[)）]\s*|>\s*)',
            '',
            line,
        ).strip()
        if not s:
            continue
        if re.match(r'^(预期结果|预期|期望结果|期望|断言|expected)', s, re.IGNORECASE):
            exp = re.sub(r'^(预期结果|预期|期望结果|期望|断言|expected)\s*[:：]?\s*', '', s, flags=re.IGNORECASE)
            if exp:
                expected.append(exp)
        else:
            steps.append(s)
    return steps, '；'.join(expected)


# ---------------------------------------------------------------------------
# Excel (.xlsx)
# ---------------------------------------------------------------------------

# 表头关键字 -> 字段
_HEADER_KEYWORDS = [
    ('name', ('用例标题', '用例名称', '案例名称', '用例名', '测试标题',
              '测试项', '功能点', '测试场景', '场景', '标题', '名称', 'casename', 'case name', 'name', 'title')),
    ('precondition', ('前置条件', '前置要求', '前提条件', '前置', '前提', 'precondition', 'pre-condition')),
    ('steps', ('操作步骤', '测试步骤', '执行步骤', '操作描述', '步骤描述', '操作流程',
               '测试步骤描述', '步骤', '操作', 'steps', 'step', 'procedure', 'actions')),
    ('expected', ('预期结果', '期望结果', '预期输出', '预期', '期望', 'expected', 'expect result', 'expected result')),
    ('priority', ('优先级', '优先级别', '级别', 'priority', 'plevel')),
    # 序号列单独识别，避免「测试用例编号」被误当成用例名称
    ('serial', ('测试用例编号', '用例编号', '案例编号', '用例id', '序号', '编号',
                'caseid', 'case id', 'case no', 'no', 'id')),
]

# 名称列排除：表头含这些词时绝不当作用例标题（防止「测试用例编号」命中名称）
_NAME_HEADER_EXCLUDE = ('编号', '序号', 'id', 'no', '索引', 'index')



def _parse_xlsx(data: bytes) -> dict:
    rows = None
    # 优先 openpyxl（若环境已安装）
    try:
        import openpyxl  # type: ignore
        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
        rows = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                rows.append([('' if c is None else str(c)).strip() for c in row])
    except ImportError:
        rows = _read_xlsx_rows_stdlib(data)
    except Exception as e:
        # openpyxl 解析失败时回退标准库
        try:
            rows = _read_xlsx_rows_stdlib(data)
        except Exception:
            raise CaseFileParseError(f'Excel 文件解析失败：{e}')

    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        raise CaseFileParseError('Excel 文件中没有可用数据')

    cases = _rows_to_cases(rows)
    if not cases:
        raise CaseFileParseError('未能从 Excel 中识别出用例，请确认包含"用例名称/操作步骤/预期结果"等列')
    return {'format': 'excel', 'cases': cases}


def _col_letter_to_index(letters: str) -> int:
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch.upper()) - ord('A') + 1)
    return idx - 1


def _read_xlsx_rows_stdlib(data: bytes) -> list[list[str]]:
    """标准库解析 xlsx：zipfile + XML，返回所有 sheet 的行（每行是字符串列表）。"""
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise CaseFileParseError('文件不是有效的 xlsx（xlsx 本质为 zip 包），请用 Excel 另存为 .xlsx 后上传')

    has_sheets = any(re.match(r'xl/worksheets/sheet\d+\.xml$', n) for n in zf.namelist())
    if not has_sheets:
        raise CaseFileParseError('xlsx 文件结构不完整，缺少工作表数据')

    # 共享字符串
    shared: list[str] = []
    if 'xl/sharedStrings.xml' in zf.namelist():
        try:
            root = ET.fromstring(zf.read('xl/sharedStrings.xml'))
            for si in root.iter(f'{{{_XLSX_NS}}}si'):
                text = ''.join(t.text or '' for t in si.iter(f'{{{_XLSX_NS}}}t'))
                shared.append(text)
        except ET.ParseError as e:
            raise CaseFileParseError(f'xlsx 共享字符串解析失败：{e}')

    sheet_files = sorted(
        n for n in zf.namelist() if re.match(r'xl/worksheets/sheet\d+\.xml$', n)
    )
    if not sheet_files:
        raise CaseFileParseError('xlsx 中未找到工作表')

    rows: list[list[str]] = []
    for sf in sheet_files:
        try:
            root = ET.fromstring(zf.read(sf))
        except ET.ParseError as e:
            raise CaseFileParseError(f'工作表 {sf} 解析失败：{e}')
        for row in root.iter(f'{{{_XLSX_NS}}}row'):
            cells: dict[int, str] = {}
            max_col = -1
            for c in row.iter(f'{{{_XLSX_NS}}}c'):
                ref = c.get('r', '')
                m = re.match(r'([A-Z]+)', ref)
                col = _col_letter_to_index(m.group(1)) if m else max_col + 1
                cell_type = c.get('t', '')
                value = ''
                if cell_type == 's':
                    v_el = c.find(f'{{{_XLSX_NS}}}v')
                    if v_el is not None and v_el.text is not None:
                        try:
                            value = shared[int(v_el.text)]
                        except (IndexError, ValueError):
                            value = ''
                elif cell_type == 'inlineStr':
                    value = ''.join(t.text or '' for t in c.iter(f'{{{_XLSX_NS}}}t'))
                else:
                    v_el = c.find(f'{{{_XLSX_NS}}}v')
                    if v_el is not None and v_el.text is not None:
                        value = v_el.text
                cells[col] = value.strip()
                max_col = max(max_col, col)
            if max_col >= 0:
                rows.append([cells.get(i, '') for i in range(max_col + 1)])
    return rows


def _norm_header(s: str) -> str:
    return re.sub(r'[\s*/_（）()：:\-]+', '', (s or '')).lower()


def _detect_header(row: list[str]) -> dict[str, int] | None:
    """识别表头行，返回 {字段: 列索引}。

    评分规则：精确匹配 > 更长关键字包含匹配；名称字段排除含「编号/序号」的表头。
    """
    best: dict[str, tuple[int, int, int]] = {}  # field -> (score, kw_len, col_index)

    for i, cell in enumerate(row):
        cell_norm = _norm_header(cell)
        if not cell_norm:
            continue
        for field, keywords in _HEADER_KEYWORDS:
            # 名称列：表头若是编号类，跳过，留给 serial
            if field == 'name' and any(ex in cell_norm for ex in _NAME_HEADER_EXCLUDE):
                continue
            for kw in keywords:
                kw_norm = _norm_header(kw)
                if not kw_norm:
                    continue
                if cell_norm == kw_norm:
                    score = 100 + len(kw_norm)
                elif kw_norm in cell_norm or cell_norm in kw_norm:
                    # 短词仅允许精确匹配，避免误伤
                    if len(kw_norm) <= 2 and cell_norm != kw_norm:
                        continue
                    score = 50 + len(kw_norm)
                else:
                    continue
                prev = best.get(field)
                key = (score, len(kw_norm), -i)
                if prev is None or key > (prev[0], prev[1], -prev[2]):
                    best[field] = (score, len(kw_norm), i)

    mapping = {field: col for field, (_, __, col) in best.items()}
    # 至少识别出 名称 或 步骤 才算表头
    if 'name' in mapping or 'steps' in mapping:
        return mapping
    return None


def _rows_to_cases(rows: list[list[str]]) -> list[dict]:
    """将 Excel 行转换为用例列表。"""
    header_idx = -1
    header_map: dict[str, int] | None = None
    for i, row in enumerate(rows[:10]):  # 表头通常在前 10 行
        hm = _detect_header(row)
        if hm:
            header_idx = i
            header_map = hm
            break

    cases: list[dict] = []
    if header_map:
        for row in rows[header_idx + 1:]:
            def cell(field):
                idx = header_map.get(field)
                if idx is None or idx >= len(row):
                    return ''
                return row[idx].strip()

            name = cell('name')
            steps_raw = cell('steps')
            expected = cell('expected')
            precondition = cell('precondition')
            if not any((name, steps_raw, expected, precondition)):
                continue
            # 名称若是纯数字（误把序号当名称），从同行其他非空文本列回退
            if name and re.fullmatch(r'\d+', name.strip()):
                for col in row:
                    col = (col or '').strip()
                    if col and not re.fullmatch(r'\d+', col) and col not in (steps_raw, expected, precondition):
                        name = col
                        break
            if not name or re.fullmatch(r'\d+', name.strip()):
                name = f'用例{len(cases) + 1}'
            cases.append({
                'name': name,
                'precondition': precondition,
                'steps': _split_steps(steps_raw),
                'expected': expected,
            })
    else:
        # 无表头：每行视为一条用例；若首列是纯数字序号则取第二列为名称
        for row in rows:
            vals = [c for c in row if c.strip()]
            if not vals:
                continue
            if len(vals) >= 2 and re.fullmatch(r'\d+', vals[0]):
                name, rest = vals[1], vals[2:]
            else:
                name, rest = vals[0], vals[1:]
            cases.append({
                'name': name,
                'precondition': '',
                'steps': rest,
                'expected': '',
            })
    return cases


def _split_steps(raw: str) -> list[str]:
    """将步骤单元格拆分为步骤列表（兼容换行、数字编号、分号分隔）。"""
    if not raw:
        return []
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')
    parts: list[str] = []
    # 优先按换行拆分
    for line in raw.split('\n'):
        line = line.strip()
        if not line:
            continue
        # 去掉开头的步骤编号：1. / 1、 / 1) / （1） / 步骤1：
        line = re.sub(r'^\s*(?:步骤\s*)?\d+\s*[.、)）:：]\s*', '', line)
        line = re.sub(r'^\s*[（(]\s*\d+\s*[)）]\s*', '', line)
        if line:
            parts.append(line)
    # 单行内用分号分隔多个步骤
    if len(parts) <= 1 and ('；' in raw or ';' in raw):
        parts = [p.strip() for p in re.split(r'[；;]', raw) if p.strip()]
    return parts


# ---------------------------------------------------------------------------
# 旧版 .xls
# ---------------------------------------------------------------------------

def _parse_xls(data: bytes) -> dict:
    try:
        import xlrd  # type: ignore
    except ImportError:
        raise CaseFileParseError('旧版 .xls 格式需要 xlrd 库支持，请将文件另存为 .xlsx 后上传')
    try:
        book = xlrd.open_workbook(file_contents=data)
    except Exception as e:
        raise CaseFileParseError(f'xls 文件解析失败：{e}')
    rows: list[list[str]] = []
    for sheet in book.sheets():
        for rx in range(sheet.nrows):
            rows.append([str(sheet.cell_value(rx, cx)).strip() for cx in range(sheet.ncols)])
    rows = [r for r in rows if any(c.strip() for c in r)]
    if not rows:
        raise CaseFileParseError('xls 文件中没有可用数据')
    cases = _rows_to_cases(rows)
    if not cases:
        raise CaseFileParseError('未能从 xls 中识别出用例')
    return {'format': 'excel', 'cases': cases}


# ---------------------------------------------------------------------------
# XMind
# ---------------------------------------------------------------------------

def _parse_xmind(data: bytes) -> dict:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile:
        raise CaseFileParseError('文件不是有效的 xmind 文件（xmind 本质为 zip 包）')

    names = set(zf.namelist())
    sheets = None
    if 'content.json' in names:
        # XMind Zen / XMind 2021+
        try:
            content = json.loads(zf.read('content.json').decode('utf-8'))
        except Exception as e:
            raise CaseFileParseError(f'xmind content.json 解析失败：{e}')
        sheets = [_topic_from_json(s.get('rootTopic')) for s in content if isinstance(s, dict)]
    elif 'content.xml' in names:
        # XMind 8
        try:
            root = ET.fromstring(zf.read('content.xml'))
        except ET.ParseError as e:
            raise CaseFileParseError(f'xmind content.xml 解析失败：{e}')
        sheets = []
        # 任意命名空间下的 sheet/topic
        for sheet in root.iter():
            if sheet.tag.split('}')[-1] == 'sheet':
                topic = next((el for el in sheet.iter() if el.tag.split('}')[-1] == 'topic'), None)
                if topic is not None:
                    sheets.append(_topic_from_xml(topic))

    if not sheets:
        raise CaseFileParseError('未能从 xmind 中读取到思维导图内容')

    cases: list[dict] = []
    for root_topic in sheets:
        if not root_topic:
            continue
        module = root_topic.get('title', '') or '功能模块'
        branches = root_topic.get('children', [])
        if not branches:
            continue
        for branch in branches:
            name = branch.get('title', '').strip()
            if not name:
                continue
            steps, expected = _collect_xmind_steps(branch)
            cases.append({
                'name': name,
                'precondition': f'所属模块：{module}' if module else '',
                'steps': steps,
                'expected': expected,
            })

    if not cases:
        raise CaseFileParseError('未能从 xmind 中识别出用例（第二层节点应作为用例名称）')
    return {'format': 'xmind', 'cases': cases}


def _topic_from_json(node) -> dict:
    """将 XMind content.json 的 topic 节点转为 {title, children:[...]} 树。"""
    if not isinstance(node, dict):
        return {'title': '', 'children': []}
    title = (node.get('title') or '').strip()
    children = []
    attached = (node.get('children') or {}).get('attached') or []
    for ch in attached:
        t = _topic_from_json(ch)
        if t.get('title') or t.get('children'):
            children.append(t)
    return {'title': title, 'children': children}


def _topic_from_xml(topic_el) -> dict:
    """将 XMind content.xml 的 topic 元素转为 {title, children:[...]} 树。"""
    title = ''
    for el in topic_el.iter():
        if el.tag.split('}')[-1] == 'title':
            title = (el.text or '').strip()
            break
    children = []
    # 递归构建：直接 children -> topics -> topic
    children_container = None
    for el in topic_el:
        tag = el.tag.split('}')[-1]
        if tag == 'children':
            children_container = el
            break
    if children_container is not None:
        for topics_el in children_container:
            if topics_el.tag.split('}')[-1] == 'topics':
                for sub in topics_el:
                    if sub.tag.split('}')[-1] == 'topic':
                        t = _topic_from_xml(sub)
                        if t.get('title') or t.get('children'):
                            children.append(t)
    return {'title': title, 'children': children}


def _collect_xmind_steps(branch: dict) -> tuple[list[str], str]:
    """收集用例分支下的步骤：子节点标题为步骤，更深层节点为步骤补充/预期。"""
    steps: list[str] = []
    expected_parts: list[str] = []

    def walk(node: dict, depth: int):
        for ch in node.get('children', []):
            title = (ch.get('title') or '').strip()
            if not title:
                walk(ch, depth + 1)
                continue
            if depth == 0:
                sub_lines = _flatten_titles(ch, skip_root=True)
                is_expected = bool(re.search(r'预期|期望|断言|expected', title, re.IGNORECASE))
                detail = title if not sub_lines else f"{title}（{' / '.join(sub_lines)}）"
                if is_expected:
                    # 预期类节点归入预期结果，不重复作为操作步骤；去掉开头的"预期结果："等前缀
                    detail = re.sub(
                        r'^\s*(预期结果|预期|期望结果|期望|断言|expected)\s*[:：]?\s*',
                        '',
                        detail,
                        flags=re.IGNORECASE,
                    )
                    if detail:
                        expected_parts.append(detail)
                else:
                    steps.append(detail)
            else:
                walk(ch, depth + 1)

    walk(branch, 0)
    if not steps:
        # 没有子节点：分支自身叶子作为步骤描述
        steps = [branch.get('title', '').strip()] if branch.get('title') else []
    return steps, '；'.join(expected_parts)


def _flatten_titles(node: dict, skip_root: bool = False) -> list[str]:
    """将节点所有后代标题平铺为列表。"""
    out: list[str] = []

    def walk(n: dict, is_root: bool):
        if not is_root:
            t = (n.get('title') or '').strip()
            if t:
                out.append(t)
        for ch in n.get('children', []):
            walk(ch, False)

    walk(node, skip_root)
    return out


# ---------------------------------------------------------------------------
# 统一文本输出（写入 data_content，供 LLM 规划）
# ---------------------------------------------------------------------------

def _cases_to_text(cases: list[dict], fmt: str) -> str:
    fmt_name = {'excel': 'Excel', 'xmind': 'XMind', 'markdown': 'Markdown'}.get(fmt, '文件')
    lines = [f'以下功能用例解析自上传的{fmt_name}文件，共 {len(cases)} 条用例，请严格按用例名称、步骤顺序和预期结果逐条执行探索：']
    for i, c in enumerate(cases, 1):
        name = c.get('name') or f'用例{i}'
        lines.append(f'\n【用例{i}】{name}')
        if c.get('precondition'):
            lines.append(f'前置条件：{c["precondition"]}')
        steps = c.get('steps') or []
        if steps:
            lines.append('操作步骤：')
            for si, s in enumerate(steps, 1):
                lines.append(f'  {si}. {s}')
        if c.get('expected'):
            lines.append(f'预期结果：{c["expected"]}')
    return '\n'.join(lines)
