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
    page.get_by_role("textbox", name="请输入手机号/用户名").fill("1518 3871603")
    page.get_by_role("textbox", name="请输入手机号/用户名").click()
    page.get_by_role("textbox", name="请输入手机号/用户名").click()
    page.get_by_role("textbox", name="请输入手机号/用户名").press("ArrowLeft")
    page.get_by_role("textbox", name="请输入手机号/用户名").press("ArrowLeft")
    page.get_by_role("textbox", name="请输入手机号/用户名").press("ArrowLeft")
    page.get_by_role("textbox", name="请输入手机号/用户名").press("ArrowLeft")
    page.get_by_role("textbox", name="请输入手机号/用户名").press("ArrowLeft")
    page.get_by_role("textbox", name="请输入手机号/用户名").press("ArrowLeft")
    page.get_by_role("textbox", name="请输入手机号/用户名").press("ArrowLeft")
    page.get_by_role("textbox", name="请输入手机号/用户名").press("ArrowLeft")
    page.get_by_role("textbox", name="请输入手机号/用户名").fill("15183871603")
    page.get_by_role("textbox", name="请输入密码").click()
    page.get_by_role("textbox", name="请输入密码").fill("123456")
    page.get_by_role("link", name="登录").nth(1).click()
        page.get_by_text(re.compile(r"购物车\s*\d*")).click()
        page.get_by_role("link", name="删除").first.click()
        page.get_by_role("link", name="删除").nth(3).click()
        page.get_by_text("+").click()
        page.get_by_role("checkbox").nth(1).check()
        page.get_by_role("link", name="结算").click()
        page.get_by_role("link", name="提交订单").click()
