import pytest
import re
from playwright.sync_api import Page, expect


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, playwright):
    return {"no_viewport": True}


def test_example(page: Page) -> None:
    page.goto("http://mall.lemonban.com:3344/")
    page.get_by_text("商城首页").click()
    page.get_by_text("我的订单").click()
    page.get_by_role("link", name="《服务条款》").click()
    page.locator("span").filter(has_text="个人中心").click()
    page.get_by_role("link", name="立即注册").click()
