"""home 页面对象（由录制回退生成）。"""

import re
from playwright.sync_api import Page, Locator


class HomePage:
    def __init__(self, page: Page):
        self.page = page

    def goto(self, url: str | None = None) -> None:
        self.page.goto(url or "https://")

    def click_登录(self) -> None:
        self.page.get_by_role("link", name="登录").click()

    def click_请输入手机号_用户名(self) -> None:
        self.page.get_by_role("textbox", name="请输入手机号/用户名").click()

    def fill_请输入手机号_用户名(self, value: str) -> None:
        self.page.get_by_role("textbox", name="请输入手机号/用户名").fill(value)

    def click_请输入密码(self) -> None:
        self.page.get_by_role("textbox", name="请输入密码").click()

    def fill_请输入密码(self, value: str) -> None:
        self.page.get_by_role("textbox", name="请输入密码").fill(value)

    def click_购物车(self) -> None:
        # 角标数量会变，用正则匹配「购物车」前缀
        self.page.get_by_text(re.compile(r"购物车\s*\d*")).click()

    # 兼容旧方法名
    def click_购物车_2(self) -> None:
        self.click_购物车()

    def click_el_7(self) -> None:
        self.page.get_by_text("+").click()

    def click_结算(self) -> None:
        self.page.get_by_role("link", name="结算").click()

    def click_提交订单(self) -> None:
        self.page.get_by_role("link", name="提交订单").click()
