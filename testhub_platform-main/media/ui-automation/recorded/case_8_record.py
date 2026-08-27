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
    page.get_by_role("textbox", name="请输入商品名称").click()
    page.get_by_role("textbox", name="请输入商品名称").fill("裙子")
    page.get_by_role("button", name="搜索").click()
    # 列表点商品偶发不跳转，确认进入详情后再操作收藏
    for _ in range(3):
        page.locator(".goods-img > img").first.click()
        try:
            page.wait_for_url(re.compile(r".*/(sec)?detail/\d+"), timeout=5000)
            break
        except Exception:
            page.wait_for_timeout(400)
    else:
        raise AssertionError(f"未进入商品详情: {page.url}")
    # 收藏态不稳定：已收藏 / 收藏商品 二选一出现。先确保未收藏，再收藏。
    page.wait_for_timeout(800)
    collect_toggle = page.get_by_role("link", name=re.compile(r"^(收藏商品|已收藏)$"))
    collect_toggle.first.wait_for(state="visible", timeout=10000)
    if page.get_by_role("link", name="已收藏").count() and page.get_by_role("link", name="已收藏").first.is_visible():
        page.get_by_role("link", name="已收藏").click()
    page.get_by_role("link", name="收藏商品").click()
