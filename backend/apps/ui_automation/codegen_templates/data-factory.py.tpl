"""{{EntityName}} 测试数据工厂。"""

from __future__ import annotations

import time
from typing import TypedDict

from faker import Faker

# 按项目语言环境修改；默认 en_US，中文项目可改为 zh_CN
faker = Faker("{{faker_locale}}")


class {{EntityClassName}}(TypedDict, total=False):
    # TODO: 按录制/计划定义字段
    pass


def create_{{entity_snake}}(overrides: dict | None = None) -> dict:
    data: dict = {
        # TODO: 按实体填默认值，例如唯一名用时间戳
        "name": f"item_{int(time.time() * 1000)}",
    }
    if overrides:
        data.update(overrides)
    return data
