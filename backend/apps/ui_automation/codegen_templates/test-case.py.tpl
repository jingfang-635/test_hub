"""{{FeatureName}} UI 自动化用例。

本文件仅对应单一功能模块；多模块勿写入同一 specs 文件。
"""

import pytest
from playwright.sync_api import Page, expect

from tests.pages.{{page_module}} import {{PageClassName}}
from tests.data.{{data_module}} import create_{{entity_snake}}


class Test{{FeatureClassName}}:
    @pytest.mark.positive
    def test_tc_001_{{case_snake}}(self, page: Page, base_url: str) -> None:
        """TC-001 {{case_name}}"""
        # TODO: 前置条件
        {{page_var}} = {{PageClassName}}(page)
        data = create_{{entity_snake}}()
        # TODO: 步骤
        # TODO: 断言 expect(...)

    @pytest.mark.negative
    def test_tc_002_{{case_snake}}(self, page: Page, base_url: str) -> None:
        """TC-002 {{case_name}}"""
        pass
