# -*- coding: utf-8 -*-
"""
接口测试套件 pytest 配置
"""
import os

import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()


def pytest_addoption(parser):
    parser.addoption('--suite-id', action='store', default=None, help='测试套件ID')
    parser.addoption('--execution-id', action='store', default=None, help='执行记录ID')
    parser.addoption('--environment-id', action='store', default=None, help='环境ID')


@pytest.fixture(scope='session')
def suite_id(request):
    return request.config.getoption('--suite-id') or os.environ.get('API_SUITE_ID')


@pytest.fixture(scope='session')
def execution_id(request):
    return request.config.getoption('--execution-id') or os.environ.get('API_EXECUTION_ID')


@pytest.fixture(scope='session')
def environment_id(request):
    return request.config.getoption('--environment-id') or os.environ.get('API_ENVIRONMENT_ID')


@pytest.fixture(scope='session')
def username():
    return os.environ.get('API_USERNAME', 'unknown')


def pytest_generate_tests(metafunc):
    """按套件请求顺序参数化用例，保证变量提取链路按 order 执行"""
    if 'suite_request_id' not in metafunc.fixturenames:
        return

    suite_id_value = (
        metafunc.config.getoption('--suite-id')
        or os.environ.get('API_SUITE_ID')
    )
    if not suite_id_value:
        metafunc.parametrize('suite_request_id', [])
        return

    from apps.api_testing.models import TestSuiteRequest

    ids = list(
        TestSuiteRequest.objects.filter(
            test_suite_id=suite_id_value,
            enabled=True,
        )
        .order_by('order', 'id')
        .values_list('id', flat=True)
    )
    metafunc.parametrize(
        'suite_request_id',
        ids,
        ids=[f'req_{i}' for i in ids],
    )
