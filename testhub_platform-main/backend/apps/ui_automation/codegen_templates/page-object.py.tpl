"""{{PageName}} 页面对象。"""

from playwright.sync_api import Page, Locator


class {{PageClassName}}:
    def __init__(self, page: Page):
        self.page = page
    # TODO: 定义 Locator，优先 get_by_role / get_by_label / get_by_test_id
    # self.submit_button: Locator = page.get_by_role("button", name="...")

    def goto(self) -> None:
        self.page.goto("{{page_url}}")

    # TODO: 按录制步骤封装方法（勿在模板写死业务字段名）
