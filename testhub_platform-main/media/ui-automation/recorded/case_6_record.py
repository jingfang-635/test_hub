import pytest
import re
from playwright.sync_api import Page, expect


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, playwright):
    return {"no_viewport": True}


def test_example(page: Page) -> None:
    page.get_by_role("link", name="领劵中心").click()
    page.get_by_role("link", name="立即领取").first.click()
