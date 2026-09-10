"""home 页面对象（由录制确定性生成）。"""

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

    def click_spinbutton(self) -> None:
        self.page.get_by_role("spinbutton").click()

    def fill_spinbutton(self, value: str) -> None:
        self.page.get_by_role("spinbutton").fill(value)

    def click_el_8(self) -> None:
        self.page.get_by_text("+").click()

    def click_去购物(self) -> None:
        self.page.get_by_role("link", name="去购物").click()

    def click_el_10(self) -> None:
        self.page.get_by_text("+").click()

    def click_手机商城(self) -> None:
        self.page.get_by_role("link", name="手机商城").click()

    def click_商城首页(self) -> None:
        self.page.get_by_text("商城首页").click()

    def click_加入购物车(self) -> None:
        self.page.get_by_role("link", name="加入购物车").click()

    def click_加入购物车(self) -> None:
        self.page.get_by_role("link", name="加入购物车").click()

    def click_加入购物车(self) -> None:
        self.page.get_by_role("link", name="加入购物车").click()

    def click_收藏商品(self) -> None:
        self.page.get_by_role("link", name="收藏商品").click()

    def click_el_17(self) -> None:
        self.page.get_by_text("-", exact=True).click()

    def click_结算(self) -> None:
        self.page.get_by_role("link", name="结算").click()

    def click_提交订单(self) -> None:
        self.page.get_by_role("link", name="提交订单").click()
