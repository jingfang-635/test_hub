"""recorded_ef2885c275cb UI 自动化用例（确定性生成）。"""

import pytest
from playwright.sync_api import Page, expect

from tests.pages.home_page import HomePage
from tests.data.home_factory import create_home


class TestRecordedEf2885c275cb:
    @pytest.mark.positive
    def test_tc_001(self, page: Page, base_url: str) -> None:
        """TC-001 TestLogin"""
        data = create_home()
        pom = HomePage(page)
        page.goto("http://mall.lemonban.com:3344/")
        page.get_by_role("link", name="登录").click()
        page.get_by_role("textbox", name="请输入手机号/用户名").click()
        # TODO: 参数化原值 '15183871603'
        page.get_by_role("textbox", name="请输入手机号/用户名").fill("15183871603")
        page.get_by_role("textbox", name="请输入密码").click()
        # TODO: 参数化原值 '123456'
        page.get_by_role("textbox", name="请输入密码").fill("123456")
        page.get_by_role("spinbutton").click()
        # TODO: 参数化原值 '3'
        page.get_by_role("spinbutton").fill("3")
        page.get_by_text("+").click()
        page.get_by_role("link", name="去购物").click()
        page.get_by_text("+").click()
        page.get_by_role("link", name="手机商城").click()
        page.get_by_text("商城首页").click()
        page.get_by_role("link", name="加入购物车").click()
        page.get_by_role("link", name="加入购物车").click()
        page.get_by_role("link", name="加入购物车").click()
        page.get_by_role("link", name="收藏商品").click()
        page.get_by_text("-", exact=True).click()
        page.get_by_role("link", name="结算").click()
        page.get_by_role("link", name="提交订单").click()

    @pytest.mark.negative
    def test_tc_004(self, page: Page, base_url: str) -> None:
        """TC-004 TestCart"""
        data = create_home()
        pom = HomePage(page)
        pom.goto(base_url)
        # TODO: 按计划补齐负向/边界步骤
        assert data

    @pytest.mark.negative
    def test_tc_007(self, page: Page, base_url: str) -> None:
        """TC-007 TestOrder"""
        data = create_home()
        pom = HomePage(page)
        pom.goto(base_url)
        # TODO: 按计划补齐负向/边界步骤
        assert data

    @pytest.mark.negative
    def test_tc_001(self, page: Page, base_url: str) -> None:
        """TC-001 正向"""
        data = create_home()
        pom = HomePage(page)
        pom.goto(base_url)
        # TODO: 按计划补齐负向/边界步骤
        assert data

    @pytest.mark.negative
    def test_tc_002(self, page: Page, base_url: str) -> None:
        """TC-002 负向"""
        data = create_home()
        pom = HomePage(page)
        pom.goto(base_url)
        # TODO: 按计划补齐负向/边界步骤
        assert data

    @pytest.mark.negative
    def test_tc_003(self, page: Page, base_url: str) -> None:
        """TC-003 负向"""
        data = create_home()
        pom = HomePage(page)
        pom.goto(base_url)
        # TODO: 按计划补齐负向/边界步骤
        assert data

    @pytest.mark.negative
    def test_tc_004(self, page: Page, base_url: str) -> None:
        """TC-004 正向"""
        data = create_home()
        pom = HomePage(page)
        pom.goto(base_url)
        # TODO: 按计划补齐负向/边界步骤
        assert data

    @pytest.mark.negative
    def test_tc_005(self, page: Page, base_url: str) -> None:
        """TC-005 正向"""
        data = create_home()
        pom = HomePage(page)
        pom.goto(base_url)
        # TODO: 按计划补齐负向/边界步骤
        assert data
