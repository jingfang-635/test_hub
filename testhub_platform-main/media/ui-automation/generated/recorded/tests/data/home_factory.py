"""数据工厂（回退生成）。"""
import os
from faker import Faker

fake = Faker("zh_CN")

def create_home(**overrides):
    data = {
        "field_1": os.getenv("TEST_FIELD_1", "15183871603"),
        "field_2": fake.user_name(),
    }
    data.update(overrides)
    return data
