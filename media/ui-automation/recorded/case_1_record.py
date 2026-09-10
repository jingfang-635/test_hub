import pytest
import re
from playwright.sync_api import Page, expect


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, playwright):
    return {"no_viewport": True}


def test_example(page: Page) -> None:
    page.goto("http://mall.lemonban.com:3344/")
    page.get_by_role("link", name="登录").click()
    page.get_by_role("textbox", name="请输入手机号/用户名").click()
    page.get_by_role("textbox", name="请输入手机号/用户名").fill("15183871603")
    page.get_by_role("textbox", name="请输入密码").click()
    page.get_by_role("textbox", name="请输入密码").fill("123456")
    page.get_by_role("link", name="登录").nth(1).click()
