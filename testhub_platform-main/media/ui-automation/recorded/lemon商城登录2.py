import re
from playwright.sync_api import Page, expect


def test_example(page: Page) -> None:
    page.goto("http://mall.lemonban.com:3344/")
