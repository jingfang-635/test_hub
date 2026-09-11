import re
from playwright.sync_api import Page, expect


def test_example(page: Page) -> None:
    page.goto("http://mall.lemonban.com:3344/")
    page.get_by_role("link", name="登录").click()
    page.goto("http://mall.lemonban.com:3344/detail/33")
    page.get_by_role("textbox", name="请输入手机号/用户名").fill("15183871603")
    page.get_by_role("textbox", name="请输入密码").fill("123456")
    page.goto("http://mall.lemonban.com:3344/detail/33")
    page.get_by_role("link", name="立即购买").click()
    page.get_by_role("link", name="提交订单").click()
    page.locator(".con > .item.active").click()
    page.get_by_role("link", name="立即付款").click()
