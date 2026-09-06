import pytest
import re
from playwright.sync_api import Page, expect


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, playwright):
    return {"no_viewport": True}


def test_example(page: Page) -> None:
    page.locator("span").filter(has_text="个人中心").click()
    page.get_by_role("link", name="查看订单").nth(1).click()
    page.get_by_role("link", name="再次购买").click()
    page.get_by_role("link", name="立即购买").click()
    page.get_by_text("有效期至：2026-09-").first.click()
    page.get_by_text("￥ 20 满100元可用 有效期至：2026-09-").first.click()
    page.get_by_role("link", name="提交订单").click()
