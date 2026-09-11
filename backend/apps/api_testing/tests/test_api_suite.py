# -*- coding: utf-8 -*-
"""
接口测试套件 - Allure-Pytest 驱动执行
"""
import json
import logging

import allure
import pytest

from apps.api_testing.models import Environment, TestExecution, TestSuite, TestSuiteRequest
from apps.api_testing.utils import append_execution_result, run_suite_request

logger = logging.getLogger(__name__)


def _attach_json(name: str, data):
    try:
        allure.attach(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            name=name,
            attachment_type=allure.attachment_type.JSON,
        )
    except Exception:
        allure.attach(str(data), name=name, attachment_type=allure.attachment_type.TEXT)


@allure.feature('接口自动化测试')
class TestApiSuite:
    """按套件请求逐条执行，结果写入 TestExecution 并输出到 Allure"""

    @allure.story('执行套件请求')
    def test_suite_request(self, suite_request_id, suite_id, execution_id, environment_id, username):
        suite_request = TestSuiteRequest.objects.select_related(
            'request', 'test_suite'
        ).get(id=suite_request_id)
        api_request = suite_request.request
        test_suite = TestSuite.objects.get(id=suite_id) if suite_id else suite_request.test_suite

        allure.dynamic.title(f'[{api_request.method}] {api_request.name}')
        allure.dynamic.suite(test_suite.name if test_suite else '接口测试套件')
        allure.dynamic.parameter('suite_request_id', suite_request_id)
        allure.dynamic.parameter('order', suite_request.order)

        environment = None
        if environment_id:
            environment = Environment.objects.filter(id=environment_id).first()
        elif test_suite and test_suite.environment_id:
            environment = test_suite.environment

        executed_by = None
        if execution_id:
            execution = TestExecution.objects.filter(id=execution_id).select_related('executed_by').first()
            if execution:
                executed_by = execution.executed_by

        with allure.step(f'准备请求: {api_request.method} {api_request.url}'):
            _attach_json('请求配置', {
                'name': api_request.name,
                'method': api_request.method,
                'url': api_request.url,
                'skip_condition': suite_request.skip_condition or '',
                'assertions': suite_request.assertions or api_request.assertions or [],
                'extractors': suite_request.extractors or getattr(api_request, 'extractors', None) or [],
            })

        with allure.step('执行请求 / 跳过条件 / 断言 / 变量提取'):
            try:
                result = run_suite_request(
                    suite_request=suite_request,
                    environment=environment,
                    executed_by=executed_by,
                )
            except Exception as exc:
                result = {
                    'name': api_request.name,
                    'method': api_request.method,
                    'url': api_request.url,
                    'passed': False,
                    'skipped': False,
                    'error': str(exc),
                }
                _attach_json('执行结果', result)
                if execution_id:
                    append_execution_result(execution_id, result)
                raise

            _attach_json('执行结果', result)

        if execution_id:
            append_execution_result(execution_id, result)

        if result.get('skipped'):
            pytest.skip(result.get('message') or '跳过条件为 True，已跳过执行')

        if result.get('skip_error'):
            pytest.fail(result.get('error') or '跳过条件执行失败')

        assert result.get('passed'), result.get('error') or '请求执行失败'
