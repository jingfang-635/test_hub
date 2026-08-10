import json
import re
import time
from django.utils import timezone
from .models import RequestHistory
from .variable_resolver import VariableResolver


def normalize_extractor_variable_name(name):
    """规范化变量名，支持 {{ var }} 或 var 两种写法"""
    if not name:
        return ''
    value = str(name).strip()
    if value.startswith('{{') and value.endswith('}}'):
        value = value[2:-2].strip()
    return value


def _serialize_extracted_value(value):
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def execute_extractors(response, extractors):
    """根据提取规则从响应中提取变量"""
    results = []
    extracted_variables = {}

    for extractor in extractors or []:
        variable_raw = extractor.get('variable', '')
        variable = normalize_extractor_variable_name(variable_raw)
        source = extractor.get('source', 'body')
        extract_type = extractor.get('type', 'jsonpath')
        expression = (extractor.get('expression') or '').strip()
        default_value = extractor.get('default_value', '')

        result = {
            'variable': variable_raw or variable,
            'variable_key': variable,
            'source': source,
            'type': extract_type,
            'expression': expression,
            'success': False,
            'value': None,
            'error': None,
            'used_default': False,
        }

        try:
            if not variable:
                raise ValueError('变量名不能为空')

            source_text = ''
            if source == 'headers':
                source_text = json.dumps(dict(response.headers), ensure_ascii=False)
            else:
                source_text = response.text or ''

            extracted = None

            if extract_type in ('jsonpath', 'json_path'):
                if not expression:
                    raise ValueError('JSONPath 表达式不能为空')
                try:
                    response_json = json.loads(source_text)
                except json.JSONDecodeError as exc:
                    raise ValueError(f'响应不是合法 JSON: {exc}') from exc

                from jsonpath_ng import parse
                matches = parse(expression).find(response_json)
                if not matches:
                    extracted = None
                elif len(matches) == 1:
                    extracted = matches[0].value
                else:
                    extracted = [match.value for match in matches]
            elif extract_type in ('regex', 'regexp'):
                if not expression:
                    raise ValueError('正则表达式不能为空')
                match = re.search(expression, source_text, re.S)
                if not match:
                    extracted = None
                elif match.lastindex:
                    extracted = match.group(1)
                else:
                    extracted = match.group(0)
            else:
                raise ValueError(f'不支持的提取类型: {extract_type}')

            if extracted is None or extracted == '':
                extracted = default_value
                result['used_default'] = True

            serialized = _serialize_extracted_value(extracted)
            result['value'] = serialized
            result['success'] = True
            extracted_variables[variable] = serialized
        except Exception as exc:
            # 提取失败时尝试使用默认值
            if default_value not in (None, ''):
                serialized = _serialize_extracted_value(default_value)
                result['value'] = serialized
                result['success'] = True
                result['used_default'] = True
                result['error'] = str(exc)
                extracted_variables[variable] = serialized
            else:
                result['error'] = str(exc)
                result['success'] = False

        results.append(result)

    return results, extracted_variables


class _SkipVariables:
    """供跳过条件表达式使用的 variables 对象，兼容 variables.get('key')"""

    def __init__(self, data=None):
        self._data = data or {}

    def get(self, key, default=None):
        value = self._data.get(key, default)
        if isinstance(value, dict) and ('currentValue' in value or 'initialValue' in value):
            current = value.get('currentValue')
            initial = value.get('initialValue')
            if current not in (None, ''):
                return current
            if initial not in (None, ''):
                return initial
            return default
        return value if value is not None else default


def evaluate_skip_condition(expression, variables):
    """
    使用受限 Python 表达式评估跳过条件。
    表达式为 True 时跳过该请求。示例：
      variables.get("env") == "dev"
      variables.get("skip_flag") == True
      variables.get("count", 0) > 10
    """
    expr = (expression or '').strip()
    if not expr:
        return False, None

    safe_globals = {'__builtins__': {}}
    safe_locals = {
        'variables': _SkipVariables(variables),
        'True': True,
        'False': False,
        'None': None,
    }

    try:
        result = eval(expr, safe_globals, safe_locals)  # noqa: S307 - intentional restricted eval
        return bool(result), None
    except Exception as exc:
        return False, str(exc)


def apply_extracted_variables_to_env(environment, extracted_variables, variables_cache=None):
    """将提取结果写入环境变量（currentValue），并同步到内存缓存"""
    if not environment or not extracted_variables:
        return

    env_variables = environment.variables or {}
    if not isinstance(env_variables, dict):
        env_variables = {}

    for key, value in extracted_variables.items():
        existing = env_variables.get(key)
        if isinstance(existing, dict):
            existing = dict(existing)
            existing['currentValue'] = value if value is not None else ''
            if 'initialValue' not in existing:
                existing['initialValue'] = existing['currentValue']
            env_variables[key] = existing
        else:
            env_variables[key] = {
                'initialValue': value if value is not None else '',
                'currentValue': value if value is not None else '',
            }

        if isinstance(variables_cache, dict):
            variables_cache[key] = env_variables[key]

    environment.variables = env_variables
    environment.save(update_fields=['variables'])


def execute_assertions(response, assertions):
    """执行断言验证"""
    results = []
    
    for assertion in assertions:
        result = {
            'name': assertion.get('name', '未命名断言'),
            'type': assertion.get('type'),
            'passed': False,
            'expected': assertion.get('expected'),
            'actual': None,
            'error': None
        }
        
        try:
            assertion_type = assertion.get('type')
            expected = assertion.get('expected')
            actual = None
            passed = False
            
            if assertion_type == 'status_code':
                actual = response.status_code
                passed = actual == expected
                
            elif assertion_type == 'response_time':
                # 响应时间断言在调用方处理
                actual = assertion.get('actual_time')
                passed = actual <= expected if actual else False
                
            elif assertion_type == 'contains':
                text = response.text or ''
                pattern = str(expected)
                actual = text[:200] + '...' if len(text) > 200 else text
                passed = pattern in str(text)
                
            elif assertion_type == 'json_path':
                json_path = assertion.get('json_path', '')
                expected_value = assertion.get('expected')
                actual = None
                passed = False
                
                try:
                    # 检查响应是否为JSON格式
                    content_type = response.headers.get('content-type', '').lower()
                    if 'application/json' not in content_type:
                        raise ValueError(f"响应不是JSON格式，Content-Type: {content_type}")
                    
                    response_json = json.loads(response.text)
                    
                    # 检查JSONPath表达式是否为空
                    if not json_path:
                        raise ValueError("JSON路径表达式不能为空")
                    
                    from jsonpath_ng import parse
                    matches = parse(json_path).find(response_json)
                    actual = matches[0].value if matches else None
                    passed = str(actual) == str(expected_value)
                    
                    # 确保actual值被正确设置到result中
                    result['actual'] = actual
                except json.JSONDecodeError as e:
                    actual = None
                    passed = False
                    result['error'] = f"JSON解析失败: {str(e)}"
                    result['actual'] = actual
                except ImportError as e:
                    actual = None
                    passed = False
                    result['error'] = f"缺少依赖库: {str(e)}，请安装jsonpath-ng"
                    result['actual'] = actual
                except Exception as e:
                    actual = None
                    passed = False
                    result['error'] = f"执行错误: {str(e)}"
                    result['actual'] = actual
                    
            elif assertion_type == 'header':
                header_name = assertion.get('header_name', '')
                expected_value = assertion.get('expected_value')
                actual = response.headers.get(header_name)
                passed = actual == expected_value
                
            elif assertion_type == 'equals':
                actual = response.text.strip()
                passed = actual == str(expected).strip()
            
            # 确保在所有情况下都设置actual值
            if 'actual' not in result or result['actual'] is None:
                result['actual'] = actual
            result['passed'] = passed
            
        except Exception as e:
            result['error'] = str(e)
            result['passed'] = False
        
        results.append(result)
    
    return results


def run_suite_request(suite_request, environment, executed_by):
    """
    执行套件中的单条请求（供 Allure-Pytest / 同步回退共用）。
    返回标准化结果字典，不直接写入 TestExecution。
    """
    import requests

    api_request = suite_request.request
    resolver = VariableResolver()

    variables = {}
    if environment:
        environment.refresh_from_db()
        variables.update(environment.variables or {})

    should_skip, skip_error = evaluate_skip_condition(
        getattr(suite_request, 'skip_condition', ''),
        variables,
    )
    if skip_error:
        return {
            'name': api_request.name,
            'method': api_request.method,
            'url': api_request.url,
            'passed': False,
            'skipped': False,
            'skip_error': True,
            'error': f'跳过条件执行失败: {skip_error}',
            'skip_condition': suite_request.skip_condition or '',
        }

    if should_skip:
        return {
            'name': api_request.name,
            'method': api_request.method,
            'url': api_request.url,
            'passed': True,
            'skipped': True,
            'error': '',
            'skip_condition': suite_request.skip_condition or '',
            'message': '跳过条件为 True，已跳过执行',
        }

    url = _replace_variables(api_request.url, variables)
    url = resolver.resolve(url)

    headers = {}
    if isinstance(api_request.headers, list):
        for header_item in api_request.headers:
            if header_item.get('enabled', True) and header_item.get('key'):
                key = header_item['key']
                value = _replace_variables(str(header_item.get('value', '')), variables)
                value = resolver.resolve(value)
                headers[key] = value
    else:
        headers = (api_request.headers or {}).copy()
        for key, value in headers.items():
            headers[key] = _replace_variables(str(value), variables)
            headers[key] = resolver.resolve(headers[key])

    params = (api_request.params or {}).copy()
    for key, value in params.items():
        params[key] = _replace_variables(str(value), variables)
        params[key] = resolver.resolve(params[key])

    body_data = None
    if api_request.body and api_request.method in ['POST', 'PUT', 'PATCH']:
        if api_request.body.get('type') == 'json':
            body_data = api_request.body.get('data', {})
            body_data = _replace_variables_in_dict(body_data, variables)
            body_data = _resolve_variables_in_dict(body_data, resolver)

    start_time = time.time()
    response = requests.request(
        method=api_request.method,
        url=url,
        headers=headers,
        params=params,
        json=body_data,
        timeout=30,
    )
    response_time = (time.time() - start_time) * 1000

    suite_assertions = getattr(suite_request, 'assertions', None)
    if isinstance(suite_assertions, list) and len(suite_assertions) > 0:
        assertions = suite_assertions
    else:
        assertions = api_request.assertions or []

    normalized_assertions = []
    for item in assertions:
        assertion = dict(item or {})
        if assertion.get('expected') in (None, '') and assertion.get('value') is not None:
            assertion['expected'] = assertion.get('value')
        if assertion.get('type') == 'header' and assertion.get('expected_value') in (None, ''):
            assertion['expected_value'] = assertion.get('expected')
        if assertion.get('type') == 'response_time':
            assertion['actual_time'] = response_time
        normalized_assertions.append(assertion)

    assertions_results = execute_assertions(response, normalized_assertions)

    suite_extractors = getattr(suite_request, 'extractors', None)
    if isinstance(suite_extractors, list) and len(suite_extractors) > 0:
        extractors = suite_extractors
    else:
        extractors = getattr(api_request, 'extractors', None) or []
    extractors_results, extracted_variables = execute_extractors(response, extractors)
    if environment and extracted_variables:
        apply_extracted_variables_to_env(
            environment, extracted_variables, variables_cache=variables
        )

    passed = True
    error_message = ''
    for assertion_result in assertions_results or []:
        if not assertion_result.get('passed', True):
            passed = False
            error_message = (
                f"断言失败: {assertion_result.get('name', '未命名断言')} - "
                f"{assertion_result.get('error', '断言不通过')}"
            )
            break

    response_json = None
    content_type = response.headers.get('content-type', '') or ''
    if 'application/json' in content_type:
        try:
            response_json = response.json()
        except Exception:
            response_json = None

    RequestHistory.objects.create(
        request=api_request,
        environment=environment,
        request_data={
            'url': url,
            'method': api_request.method,
            'headers': headers,
            'params': params,
            'body': body_data,
        },
        response_data={
            'headers': dict(response.headers),
            'body': response.text,
            'json': response_json,
        },
        status_code=response.status_code,
        response_time=response_time,
        assertions_results=assertions_results,
        executed_by=executed_by,
    )

    return {
        'name': api_request.name,
        'method': api_request.method,
        'url': url,
        'status_code': response.status_code,
        'response_time': response_time,
        'passed': passed,
        'skipped': False,
        'error': error_message,
        'assertions_results': assertions_results,
        'extractors_results': extractors_results,
        'extracted_variables': extracted_variables,
    }


def append_execution_result(execution_id, result):
    """将单条请求结果追加到执行记录（pytest 子进程内调用）"""
    from django.db import transaction
    from .models import TestExecution

    with transaction.atomic():
        execution = TestExecution.objects.select_for_update().get(id=execution_id)
        results = execution.results if isinstance(execution.results, list) else []
        results.append(result)
        execution.results = results

        if result.get('skipped') or result.get('passed'):
            execution.passed_requests = (execution.passed_requests or 0) + 1
        else:
            execution.failed_requests = (execution.failed_requests or 0) + 1
        execution.save(update_fields=['results', 'passed_requests', 'failed_requests'])


def execute_test_suite(test_suite, environment, executed_by):
    """
    执行测试套件：优先使用 Allure-Pytest 驱动，失败时回退到进程内同步执行。
    """
    from .models import TestExecution

    try:
        suite_requests = test_suite.testsuiterequest_set.filter(enabled=True).order_by('order')
        total = suite_requests.count()

        execution = TestExecution.objects.create(
            test_suite=test_suite,
            status='RUNNING',
            start_time=timezone.now(),
            executed_by=executed_by,
            total_requests=total,
            passed_requests=0,
            failed_requests=0,
            results=[],
        )

        if total == 0:
            execution.end_time = timezone.now()
            execution.status = 'COMPLETED'
            execution.save()
            return {
                'success': True,
                'execution_id': execution.id,
                'passed_count': 0,
                'failed_count': 0,
                'total_count': 0,
                'results': [],
            }

        try:
            from .executors.api_suite_executor import ApiSuiteExecutor

            executor = ApiSuiteExecutor()
            pytest_result = executor.run_suite(
                suite_id=test_suite.id,
                execution_id=execution.id,
                environment_id=environment.id if environment else None,
                username=getattr(executed_by, 'username', None),
            )
        except Exception as pytest_exc:
            # pytest / allure 不可用时回退
            pytest_result = {'success': False, 'error': str(pytest_exc), 'fallback': True}

        execution.refresh_from_db()
        results = execution.results if isinstance(execution.results, list) else []

        # pytest 进程已正常结束（含有失败用例 / 无用例）时不再回退，避免重复请求
        if pytest_result.get('success'):
            passed_count = sum(1 for r in results if r.get('skipped') or r.get('passed'))
            failed_count = sum(
                1 for r in results if not r.get('skipped') and not r.get('passed')
            )
            # 子进程崩溃导致结果不足时，按未执行计失败
            if len(results) < total:
                failed_count += total - len(results)

            execution.passed_requests = passed_count
            execution.failed_requests = failed_count
            execution.end_time = timezone.now()
            execution.status = 'COMPLETED' if failed_count == 0 else 'FAILED'
            execution.save()
            return {
                'success': True,
                'execution_id': execution.id,
                'passed_count': passed_count,
                'failed_count': failed_count,
                'total_count': execution.total_requests,
                'results': results,
                'report_url': pytest_result.get('report_url'),
                'driver': 'allure-pytest',
            }

        # 仅在 pytest 无法启动时回退进程内同步执行
        return _execute_test_suite_inline(
            execution=execution,
            suite_requests=suite_requests,
            environment=environment,
            executed_by=executed_by,
            pytest_error=pytest_result.get('error'),
        )

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


def _execute_test_suite_inline(execution, suite_requests, environment, executed_by, pytest_error=None):
    """进程内同步执行套件（pytest 不可用或未产出结果时的回退）"""
    results = []
    passed_count = 0
    failed_count = 0

    for suite_request in suite_requests:
        api_request = suite_request.request
        try:
            result = run_suite_request(suite_request, environment, executed_by)
        except Exception as e:
            result = {
                'name': api_request.name,
                'method': api_request.method,
                'url': api_request.url,
                'passed': False,
                'skipped': False,
                'error': str(e),
            }

        results.append(result)
        if result.get('skipped') or result.get('passed'):
            passed_count += 1
        else:
            failed_count += 1

    execution.end_time = timezone.now()
    execution.passed_requests = passed_count
    execution.failed_requests = failed_count
    execution.status = 'COMPLETED' if failed_count == 0 else 'FAILED'
    execution.results = results
    execution.save()

    return {
        'success': True,
        'execution_id': execution.id,
        'passed_count': passed_count,
        'failed_count': failed_count,
        'total_count': execution.total_requests,
        'results': results,
        'driver': 'inline',
        'pytest_error': pytest_error,
    }


def execute_api_request(api_request, environment, executed_by):
    """执行单个API请求并返回结果"""
    import requests
    import time
    
    try:
        # 创建变量解析器
        resolver = VariableResolver()
        
        # 解析环境变量
        variables = {}
        if environment:
            variables.update(environment.variables)
        
        # 替换URL中的变量（先解析动态函数，再替换环境变量）
        url = _replace_variables(api_request.url, variables)
        url = resolver.resolve(url)
        
        # 准备请求头
        headers = {}
        if isinstance(api_request.headers, list):
            for header_item in api_request.headers:
                if header_item.get('enabled', True) and header_item.get('key'):
                    key = header_item['key']
                    value = _replace_variables(str(header_item.get('value', '')), variables)
                    value = resolver.resolve(value)
                    headers[key] = value
        else:
            headers = api_request.headers.copy()
            for key, value in headers.items():
                headers[key] = _replace_variables(str(value), variables)
                headers[key] = resolver.resolve(headers[key])
        
        # 准备请求参数
        params = api_request.params.copy() if api_request.params else {}
        for key, value in params.items():
            params[key] = _replace_variables(str(value), variables)
            params[key] = resolver.resolve(params[key])
        
        # 准备请求体
        body_data = None
        if api_request.body and api_request.method in ['POST', 'PUT', 'PATCH']:
            if api_request.body.get('type') == 'json':
                body_data = api_request.body.get('data', {})
                body_data = _replace_variables_in_dict(body_data, variables)
                body_data = _resolve_variables_in_dict(body_data, resolver)
        
        # 执行请求
        start_time = time.time()
        response = requests.request(
            method=api_request.method,
            url=url,
            headers=headers,
            params=params,
            json=body_data,
            timeout=30
        )
        end_time = time.time()
        response_time = (end_time - start_time) * 1000
        
        # 执行断言验证
        assertions = api_request.assertions or []
        for assertion in assertions:
            if assertion.get('type') == 'response_time':
                assertion['actual_time'] = response_time
        
        assertions_results = execute_assertions(response, assertions)

        extractors_results, extracted_variables = execute_extractors(
            response, getattr(api_request, 'extractors', None) or []
        )
        if environment and extracted_variables:
            apply_extracted_variables_to_env(environment, extracted_variables)
        
        # 保存请求历史
        history = RequestHistory.objects.create(
            request=api_request,
            environment=environment,
            request_data={
                'url': url,
                'method': api_request.method,
                'headers': headers,
                'params': params,
                'body': body_data
            },
            response_data={
                'headers': dict(response.headers),
                'body': response.text,
                'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            },
            status_code=response.status_code,
            response_time=response_time,
            assertions_results=assertions_results,
            executed_by=executed_by
        )
        
        return {
            'success': True,
            'history_id': history.id,
            'status_code': response.status_code,
            'response_time': response_time,
            'assertions_results': assertions_results,
            'extractors_results': extractors_results,
            'extracted_variables': extracted_variables,
            'response_data': {
                'headers': dict(response.headers),
                'body': response.text,
                'json': response.json() if response.headers.get('content-type', '').startswith('application/json') else None
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def _replace_variables(text, variables):
    """替换文本中的变量"""
    if not isinstance(text, str):
        return text
    
    result = text
    for key, value in (variables or {}).items():
        if isinstance(value, dict):
            replacement = str(value.get('currentValue', '') or value.get('initialValue', ''))
        else:
            replacement = str(value) if value is not None else ''
        result = result.replace(f'{{{{{key}}}}}', replacement)
    return result

def _replace_variables_in_dict(data, variables):
    """递归替换字典中的变量"""
    if isinstance(data, dict):
        return {k: _replace_variables_in_dict(v, variables) for k, v in data.items()}
    elif isinstance(data, list):
        return [_replace_variables_in_dict(item, variables) for item in data]
    elif isinstance(data, str):
        return _replace_variables(data, variables)
    else:
        return data

def _resolve_variables_in_dict(data, resolver):
    """递归解析字典中的动态函数占位符"""
    if isinstance(data, dict):
        return {k: _resolve_variables_in_dict(v, resolver) for k, v in data.items()}
    elif isinstance(data, list):
        return [_resolve_variables_in_dict(item, resolver) for item in data]
    elif isinstance(data, str):
        return resolver.resolve(data)
    else:
        return data
