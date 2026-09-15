"""AIModelConfig role / scenario 多值（JSON 数组）查询语义的回归测试。

背景：role / scenario 在 0015、0016 迁移中由单值 varchar 改成了 JSON 数组。
一旦有人把 `__contains=[value]` 改回 `__icontains=...`（看起来更"宽松"），
查询就会退化成整列 LIKE，参数被序列化成 Python repr "['writer']"，
而列里存的是 JSON "writer"，于是恒不命中 —— AI 用例生成页会一直显示「未配置」。
本文件锁定这些语义。
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import AIModelConfig

User = get_user_model()


class AIModelConfigRoleQueryTests(TestCase):
    """role/scenario 多值查询必须命中 JSON 数组中的单个元素。"""

    def setUp(self):
        self.user = User.objects.create_user(
            username='role_query_user',
            email='role_query@example.com',
            password='testpass123',
        )
        # 一个承担多个角色的共享配置（同时含 writer + browser_use_text），
        # 这是 0016 迁移后最典型的形态，也是旧 icontains 写法误杀/漏掉的场景。
        self.shared = AIModelConfig.objects.create(
            name='shared-multi-role',
            model_type='other',
            role=['writer', 'browser_use_text', 'code_generator', 'test_oracle',
                  'browser_use_vision', 'reviewer'],
            scenario=['testcase_generation', 'ui_automation', 'other'],
            base_url='http://localhost:11434/v1',
            model_name='test-model',
            created_by=self.user,
        )
        # 纯 browser_use 配置：默认列表应把它排除掉
        self.browser_only = AIModelConfig.objects.create(
            name='browser-only',
            model_type='other',
            role=['browser_use_text'],
            scenario=['testcase_generation'],
            base_url='http://localhost:11434/v1',
            model_name='test-model-2',
            created_by=self.user,
        )

    def test_any_of_matches_element_inside_multi_role_list(self):
        """any_of 是「含任一」，不能用 AND 语义。"""
        qs = AIModelConfig.objects.filter(
            AIModelConfig.any_of(role=['writer', 'reviewer'])
        )
        self.assertIn(self.shared, qs)
        self.assertNotIn(self.browser_only, qs)

    def test_role_contains_single_value_hits_multi_role_row(self):
        """__contains=[x] 必须命中「数组里含 x」的行（JSON_CONTAINS 语义）。"""
        for role in ('writer', 'reviewer', 'code_generator', 'test_oracle'):
            with self.subTest(role=role):
                self.assertTrue(
                    AIModelConfig.objects.filter(role__contains=[role]).exists(),
                    f'role={role} 应命中共享配置',
                )

    def test_icontains_list_form_is_not_used(self):
        """守住回归：icontains 传 list 会生成 LIKE %['writer']%，恒不命中。

        这里断言正确的 __contains 写法可用，同时确保没有误用 icontains 列表写法。
        """
        correct = AIModelConfig.objects.filter(role__contains=['writer'])
        self.assertIn(self.shared, correct)

        broken = AIModelConfig.objects.filter(role__icontains=['writer'])
        self.assertFalse(
            broken.exists(),
            'role__icontains 传 list 会退化成 LIKE %[\'writer\']%，恒为空；'
            '请使用 role__contains=[value]。',
        )

    def test_none_of_excludes_all_listed_values(self):
        """none_of 排除多个角色时必须用 Q 取反，不能漏掉「只含其一」的行。"""
        qs = AIModelConfig.objects.filter(
            AIModelConfig.none_of(role=['browser_use_text', 'browser_use_vision'])
        )
        self.assertNotIn(self.shared, qs)
        self.assertNotIn(self.browser_only, qs)

    def test_scenario_contains_hits_multi_scenario_row(self):
        """scenario 与 role 同为多值 JSON，语义必须一致。"""
        self.assertIn(
            self.shared,
            AIModelConfig.objects.filter(scenario__contains=['testcase_generation']),
        )
        self.assertIn(
            self.shared,
            AIModelConfig.objects.filter(scenario__contains=['ui_automation']),
        )

    def test_get_active_configs_for_role_hits_shared_config(self):
        """模型自带的便捷方法同样要能命中多角色共享配置。"""
        self.assertIn(
            self.shared,
            AIModelConfig.get_active_configs_for_role('writer'),
        )
        self.assertIn(
            self.shared,
            AIModelConfig.get_active_configs_for_role('reviewer', 'testcase_generation'),
        )

    def test_active_and_disabled_split_is_detected(self):
        """config/check 依赖「启用/禁用」两类都存在时能各自检出。"""
        self.browser_only.is_active = False
        self.browser_only.save(update_fields=['is_active'])

        self.assertIsNotNone(
            AIModelConfig.objects.filter(
                role__contains=['writer'], is_active=True
            ).first()
        )
        self.assertIsNotNone(
            AIModelConfig.objects.filter(
                role__contains=['browser_use_text'], is_active=False
            ).first()
        )
