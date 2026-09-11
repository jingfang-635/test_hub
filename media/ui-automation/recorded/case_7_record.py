import pytest
import re
from playwright.sync_api import Page, expect


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, playwright):
    return {"no_viewport": True}


def test_example(page: Page) -> None:
    page.locator("span").filter(has_text="个人中心").click()
