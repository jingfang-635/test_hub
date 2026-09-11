import pytest
import re
from playwright.sync_api import Page, expect


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, playwright):
    return {"no_viewport": True}


def test_example(page: Page) -> None:
    page.get_by_role("textbox", name="请输入商品名称").click()
    page.get_by_role("textbox", name="请输入商品名称").fill("裙子")
    page.get_by_role("button", name="搜索").click()
    page.locator(".goods-img > img").click()
    page.get_by_role("link", name="立即购买").click()
    page.get_by_role("link", name="提交订单").click()
    page.get_by_text("我的订单").click()
    page.get_by_role("link", name="订单详情").first.click()
    page.get_by_role("link", name="取消订单").click()
    page.get_by_role("link", name="确定").click()
