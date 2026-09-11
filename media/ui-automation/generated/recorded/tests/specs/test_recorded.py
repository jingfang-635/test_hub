"""recorded UI 自动化用例（回退生成）。"""

import re

import pytest
from playwright.sync_api import Page, expect

from tests.pages.home_page import HomePage
from tests.data.home_factory import create_home


class TestRecorded:
    @pytest.mark.positive
    def test_tc_001_recorded_main(self, page: Page, base_url: str) -> None:
        """TC-001 recorded 主流程"""
        data = create_home()
        pom = HomePage(page)
        # 下列步骤来自录制，请按需改为 POM 方法调用
        page.goto("http://mall.lemonban.com:3344/")
        page.get_by_role("link", name="登录").click()
        page.get_by_role("textbox", name="请输入手机号/用户名").click()
        # TODO: 参数化原值 '15183871603'
        page.get_by_role("textbox", name="请输入手机号/用户名").fill("15183871603")
        page.get_by_role("textbox", name="请输入密码").click()
        # TODO: 参数化原值 '123456'
        page.get_by_role("textbox", name="请输入密码").fill("123456")
        page.get_by_text(re.compile(r"购物车\s*\d*")).click()
        page.get_by_text("+").click()
        page.get_by_role("link", name="结算").click()
        page.get_by_role("link", name="提交订单").click()
