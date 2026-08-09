# -*- coding: utf-8 -*-
"""飞书 URL 解析与正文规范化单元测试（不依赖真实飞书网络）。"""
from django.test import SimpleTestCase, override_settings

from .feishu_client import FeishuClient, FeishuError, MAX_CONTENT_LENGTH


class FeishuParseUrlTests(SimpleTestCase):
    def test_parse_docx_url(self):
        parsed = FeishuClient.parse_doc_url(
            'https://example.feishu.cn/docx/doxcnABCDEFG123?from=space'
        )
        self.assertEqual(parsed.doc_type, 'docx')
        self.assertEqual(parsed.token, 'doxcnABCDEFG123')

    def test_parse_wiki_url(self):
        parsed = FeishuClient.parse_doc_url(
            'https://my.larksuite.com/wiki/wikcnXYZ789'
        )
        self.assertEqual(parsed.doc_type, 'wiki')
        self.assertEqual(parsed.token, 'wikcnXYZ789')

    def test_reject_non_feishu_host(self):
        with self.assertRaises(FeishuError) as ctx:
            FeishuClient.parse_doc_url('https://example.com/docx/abc')
        self.assertEqual(ctx.exception.code, 'invalid_url')

    def test_reject_old_docs_path(self):
        with self.assertRaises(FeishuError) as ctx:
            FeishuClient.parse_doc_url('https://example.feishu.cn/docs/doccnOldToken')
        self.assertEqual(ctx.exception.code, 'unsupported_url')

    def test_normalize_content_trims_and_limits(self):
        text = FeishuClient.normalize_content('a\n\n\n\nb\n')
        self.assertEqual(text, 'a\n\nb')
        with self.assertRaises(FeishuError) as ctx:
            FeishuClient.normalize_content('x' * (MAX_CONTENT_LENGTH + 1))
        self.assertEqual(ctx.exception.code, 'content_too_long')


@override_settings(FEISHU_APP_ID='', FEISHU_APP_SECRET='')
class FeishuConfigTests(SimpleTestCase):
    def test_not_configured(self):
        client = FeishuClient()
        with self.assertRaises(FeishuError) as ctx:
            client.ensure_configured()
        self.assertEqual(ctx.exception.code, 'not_configured')
        self.assertEqual(ctx.exception.status_code, 503)


@override_settings(
    FEISHU_APP_ID='cli_test',
    FEISHU_APP_SECRET='secret',
    FEISHU_REDIRECT_URI='http://localhost:3000/ai-generation/requirement-analysis',
    FEISHU_ACCOUNTS_URL='https://accounts.feishu.cn',
    FEISHU_OAUTH_SCOPES='offline_access docx:document:readonly wiki:wiki:readonly',
)
class FeishuOAuthUrlTests(SimpleTestCase):
    def test_build_authorize_url_contains_required_params(self):
        client = FeishuClient()
        # 仅校验 URL 拼装；state 落库逻辑在集成环境验证
        from unittest.mock import patch
        with patch.object(FeishuClient, 'create_oauth_state', return_value='test-state'):
            result = client.build_authorize_url(user_id=1)
        self.assertIn('authorize_url', result)
        self.assertIn('client_id=cli_test', result['authorize_url'])
        self.assertIn('offline_access', result['authorize_url'])
        self.assertIn('state=test-state', result['authorize_url'])
        # scope 空格须编码为 %20
        self.assertIn('offline_access%20docx', result['authorize_url'])
        self.assertEqual(result['state'], 'test-state')
