# -*- coding: utf-8 -*-
"""飞书云文档客户端：用户 OAuth（user_access_token）拉取 docx / wiki 正文。"""
from __future__ import annotations

import logging
import re
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Optional
from urllib.parse import quote, urlencode, urlparse

import httpx
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

MAX_CONTENT_LENGTH = 100_000
TOKEN_REFRESH_MARGIN_SECONDS = 300
OAUTH_STATE_TTL_SECONDS = 600

DEFAULT_OAUTH_SCOPES = 'offline_access docx:document:readonly wiki:wiki:readonly'


class FeishuError(Exception):
    """飞书业务/配置错误，message 可直接返回给前端。"""

    def __init__(self, message: str, code: str = 'feishu_error', status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


@dataclass
class ParsedDocUrl:
    doc_type: str  # 'docx' | 'wiki'
    token: str
    source_url: str


class FeishuClient:
    """封装 OAuth、user_access_token、URL 解析与文档正文拉取。"""

    _tenant_lock = threading.Lock()
    _cached_tenant_token: Optional[str] = None
    _tenant_token_expire_at: float = 0.0

    def __init__(self, user=None):
        self.user = user
        self.app_id = (getattr(settings, 'FEISHU_APP_ID', '') or '').strip()
        self.app_secret = (getattr(settings, 'FEISHU_APP_SECRET', '') or '').strip()
        self.base_url = (getattr(settings, 'FEISHU_BASE_URL', '') or 'https://open.feishu.cn').rstrip('/')
        self.accounts_url = (
            getattr(settings, 'FEISHU_ACCOUNTS_URL', '') or 'https://accounts.feishu.cn'
        ).rstrip('/')
        self.redirect_uri = (getattr(settings, 'FEISHU_REDIRECT_URI', '') or '').strip()
        self.frontend_redirect = (
            getattr(settings, 'FEISHU_FRONTEND_REDIRECT', '') or ''
        ).strip()
        self.oauth_scopes = (
            getattr(settings, 'FEISHU_OAUTH_SCOPES', '') or DEFAULT_OAUTH_SCOPES
        ).strip()
        self._user_access_token: Optional[str] = None
        self._auth_record = None

    def ensure_configured(self) -> None:
        if not self.app_id or not self.app_secret:
            raise FeishuError(
                '飞书应用未配置，请在 config.yaml 或环境变量中设置 FEISHU_APP_ID / FEISHU_APP_SECRET',
                code='not_configured',
                status_code=503,
            )

    def ensure_oauth_configured(self) -> None:
        self.ensure_configured()
        if not self.redirect_uri:
            raise FeishuError(
                '飞书 OAuth 回调地址未配置，请设置 FEISHU_REDIRECT_URI',
                code='not_configured',
                status_code=503,
            )

    # ---------- OAuth ----------

    def create_oauth_state(self, user_id: int) -> str:
        from .models import FeishuOAuthState

        state = secrets.token_urlsafe(32)
        FeishuOAuthState.objects.create(
            state=state,
            user_id=user_id,
            expires_at=timezone.now() + timedelta(seconds=OAUTH_STATE_TTL_SECONDS),
        )
        # 顺带清理过期 state，避免表膨胀
        FeishuOAuthState.objects.filter(expires_at__lt=timezone.now()).delete()
        return state

    def pop_oauth_state(self, state: str) -> Optional[Dict[str, Any]]:
        """校验并消费 state（取出即删除，防止重放）。"""
        from .models import FeishuOAuthState

        if not state:
            return None
        row = FeishuOAuthState.objects.filter(state=state).select_related('user').first()
        if not row:
            return None
        user_id = row.user_id
        expired = row.expires_at <= timezone.now()
        row.delete()
        if expired:
            return None
        return {'user_id': user_id}

    def build_authorize_url(self, user_id: int) -> Dict[str, str]:
        self.ensure_oauth_configured()
        state = self.create_oauth_state(user_id)
        params = {
            'client_id': self.app_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': self.oauth_scopes,
            'state': state,
        }
        # 飞书要求 scope 空格编码为 %20（不要用 +）
        url = (
            f'{self.accounts_url}/open-apis/authen/v1/authorize?'
            f'{urlencode(params, quote_via=quote)}'
        )
        return {'authorize_url': url, 'state': state}

    def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        self.ensure_oauth_configured()
        return self._oauth_token_request({
            'grant_type': 'authorization_code',
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'code': code,
            'redirect_uri': self.redirect_uri,
        })

    def refresh_user_access_token(self, refresh_token: str) -> Dict[str, Any]:
        self.ensure_configured()
        return self._oauth_token_request({
            'grant_type': 'refresh_token',
            'client_id': self.app_id,
            'client_secret': self.app_secret,
            'refresh_token': refresh_token,
        })

    def _oauth_token_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f'{self.base_url}/open-apis/authen/v2/oauth/token'
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, json=payload)
                data = resp.json()
        except Exception as e:
            logger.exception('飞书 OAuth token 请求失败')
            raise FeishuError(
                f'无法连接飞书开放平台: {e}',
                code='network_error',
                status_code=502,
            ) from e

        # v2 成功时 code=0，并直接带 access_token；失败也可能无 code
        if data.get('code') not in (0, None) and not data.get('access_token'):
            raise FeishuError(
                f"飞书授权失败: {data.get('error_description') or data.get('msg') or data}",
                code='oauth_failed',
                status_code=400,
            )
        if not data.get('access_token'):
            raise FeishuError(
                f"飞书授权失败: {data.get('error_description') or data.get('error') or data}",
                code='oauth_failed',
                status_code=400,
            )
        return data

    def fetch_user_info(self, access_token: str) -> Dict[str, Any]:
        url = f'{self.base_url}/open-apis/authen/v1/user_info'
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(url, headers={'Authorization': f'Bearer {access_token}'})
                data = resp.json()
        except Exception as e:
            logger.warning('获取飞书用户信息失败: %s', e)
            return {}
        if data.get('code') != 0:
            return {}
        return data.get('data') or {}

    def save_user_tokens(self, user, token_payload: Dict[str, Any]):
        from .models import FeishuUserAuth

        access_token = token_payload['access_token']
        refresh_token = token_payload.get('refresh_token') or ''
        expires_in = int(token_payload.get('expires_in') or 7200)
        refresh_expires_in = int(token_payload.get('refresh_token_expires_in') or 0)
        now = timezone.now()

        user_info = self.fetch_user_info(access_token)
        defaults = {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_expires_at': now + timedelta(seconds=expires_in),
            'refresh_expires_at': (
                now + timedelta(seconds=refresh_expires_in) if refresh_expires_in else None
            ),
            'scope': token_payload.get('scope') or self.oauth_scopes,
            'open_id': user_info.get('open_id') or '',
            'union_id': user_info.get('union_id') or '',
            'feishu_name': user_info.get('name') or user_info.get('en_name') or '',
        }
        auth, _ = FeishuUserAuth.objects.update_or_create(user=user, defaults=defaults)
        return auth

    def get_oauth_status(self, user) -> Dict[str, Any]:
        from .models import FeishuUserAuth

        auth = FeishuUserAuth.objects.filter(user=user).first()
        if not auth:
            return {'connected': False}
        return {
            'connected': True,
            'feishu_name': auth.feishu_name or '',
            'open_id': auth.open_id or '',
            'scope': auth.scope or '',
            'token_expires_at': (
                auth.token_expires_at.isoformat() if auth.token_expires_at else None
            ),
            'updated_at': auth.updated_at.isoformat() if auth.updated_at else None,
        }

    def disconnect_user(self, user) -> None:
        from .models import FeishuUserAuth

        FeishuUserAuth.objects.filter(user=user).delete()

    def get_valid_user_access_token(self, user=None) -> str:
        """获取可用的 user_access_token，必要时自动 refresh。"""
        from .models import FeishuUserAuth

        user = user or self.user
        if not user or not getattr(user, 'is_authenticated', False):
            raise FeishuError('请先登录平台', code='login_required', status_code=401)

        auth = FeishuUserAuth.objects.filter(user=user).first()
        if not auth:
            raise FeishuError(
                '尚未连接飞书账号，请先完成飞书授权',
                code='need_oauth',
                status_code=401,
            )

        now = timezone.now()
        margin = timedelta(seconds=TOKEN_REFRESH_MARGIN_SECONDS)
        if auth.token_expires_at and auth.token_expires_at > now + margin:
            self._auth_record = auth
            self._user_access_token = auth.access_token
            return auth.access_token

        if not auth.refresh_token:
            raise FeishuError(
                '飞书授权已过期，请重新连接飞书账号',
                code='need_reauth',
                status_code=401,
            )
        if auth.refresh_expires_at and auth.refresh_expires_at <= now:
            raise FeishuError(
                '飞书授权已过期，请重新连接飞书账号',
                code='need_reauth',
                status_code=401,
            )

        try:
            payload = self.refresh_user_access_token(auth.refresh_token)
        except FeishuError:
            raise FeishuError(
                '飞书授权已失效，请重新连接飞书账号',
                code='need_reauth',
                status_code=401,
            )

        auth = self.save_user_tokens(user, payload)
        self._auth_record = auth
        self._user_access_token = auth.access_token
        return auth.access_token

    # ---------- App credentials (ops) ----------

    def test_connection(self) -> Dict[str, Any]:
        """换取 tenant_access_token 以验证应用凭证。"""
        token = self.get_tenant_access_token(force_refresh=True)
        return {
            'ok': True,
            'message': '飞书应用凭证有效',
            'token_prefix': f'{token[:8]}...' if token and len(token) > 8 else '***',
        }

    def get_tenant_access_token(self, force_refresh: bool = False) -> str:
        self.ensure_configured()
        now = time.time()
        with self._tenant_lock:
            if (
                not force_refresh
                and self._cached_tenant_token
                and now < self._tenant_token_expire_at - TOKEN_REFRESH_MARGIN_SECONDS
            ):
                return self._cached_tenant_token

            url = f'{self.base_url}/open-apis/auth/v3/tenant_access_token/internal'
            try:
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(url, json={
                        'app_id': self.app_id,
                        'app_secret': self.app_secret,
                    })
                    data = resp.json()
            except Exception as e:
                logger.exception('获取飞书 tenant_access_token 失败')
                raise FeishuError(
                    f'无法连接飞书开放平台: {e}',
                    code='network_error',
                    status_code=502,
                ) from e

            if data.get('code') != 0:
                raise FeishuError(
                    f"飞书凭证无效或获取 token 失败: {data.get('msg', data)}",
                    code='auth_failed',
                    status_code=400,
                )

            token = data.get('tenant_access_token')
            expire = int(data.get('expire', 7200))
            if not token:
                raise FeishuError('飞书返回的 token 为空', code='auth_failed', status_code=400)

            FeishuClient._cached_tenant_token = token
            FeishuClient._tenant_token_expire_at = now + expire
            return token

    # ---------- Document APIs ----------

    @staticmethod
    def parse_doc_url(url: str) -> ParsedDocUrl:
        if not url or not str(url).strip():
            raise FeishuError('请输入飞书文档链接', code='invalid_url')

        raw = str(url).strip()
        parsed = urlparse(raw)
        host = (parsed.netloc or '').lower()
        if not host or (
            'feishu.cn' not in host
            and 'larksuite.com' not in host
            and 'feishu.com' not in host
        ):
            raise FeishuError(
                '链接无效：仅支持飞书/Lark 文档域名（feishu.cn / larksuite.com）',
                code='invalid_url',
            )

        path = parsed.path or ''
        match = re.search(r'/(docx|wiki)/([A-Za-z0-9_-]+)', path)
        if not match:
            raise FeishuError(
                '链接格式不支持：请使用新版文档（/docx/...）或知识库（/wiki/...）链接',
                code='unsupported_url',
            )

        doc_type, token = match.group(1), match.group(2)
        return ParsedDocUrl(doc_type=doc_type, token=token, source_url=raw)

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        retry_on_auth: bool = True,
    ) -> Dict[str, Any]:
        if not self._user_access_token:
            self.get_valid_user_access_token()
        token = self._user_access_token
        url = f'{self.base_url}{path}'
        headers = {'Authorization': f'Bearer {token}'}

        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.request(method, url, headers=headers, params=params)
                data = resp.json()
        except FeishuError:
            raise
        except Exception as e:
            logger.exception('调用飞书 API 失败: %s %s', method, path)
            raise FeishuError(
                f'飞书服务暂时不可用，请稍后重试: {e}',
                code='network_error',
                status_code=502,
            ) from e

        code = data.get('code')
        if code == 0:
            return data.get('data') or {}

        # user token 失效：尝试 refresh 一次
        if retry_on_auth and self.user and code in (99991663, 99991661, 99991668, 99991677, 99991679):
            from .models import FeishuUserAuth

            auth = FeishuUserAuth.objects.filter(user=self.user).first()
            if auth and auth.refresh_token:
                try:
                    payload = self.refresh_user_access_token(auth.refresh_token)
                    self.save_user_tokens(self.user, payload)
                    self._user_access_token = None
                    self.get_valid_user_access_token(self.user)
                    return self._request(method, path, params=params, retry_on_auth=False)
                except FeishuError:
                    raise FeishuError(
                        '飞书授权已失效，请重新连接飞书账号',
                        code='need_reauth',
                        status_code=401,
                    )

        msg = data.get('msg') or str(data)
        if resp.status_code == 403 or code in (1770032, 131006):
            raise FeishuError(
                '当前飞书账号无权阅读该文档，请确认文档已分享给你（或你所在的群/部门）',
                code='permission_denied',
                status_code=403,
            )

        if resp.status_code >= 500:
            raise FeishuError(
                f'飞书服务异常，请稍后重试: {msg}',
                code='feishu_server_error',
                status_code=502,
            )

        raise FeishuError(f'飞书 API 错误: {msg}', code='api_error', status_code=400)

    def resolve_wiki_to_docx(self, wiki_token: str) -> str:
        data = self._request(
            'GET',
            '/open-apis/wiki/v2/spaces/get_node',
            params={'token': wiki_token},
        )
        node = data.get('node') or data
        obj_type = node.get('obj_type') or ''
        obj_token = node.get('obj_token') or ''
        if obj_type != 'docx':
            raise FeishuError(
                f'该 Wiki 节点类型为「{obj_type or "未知"}」，仅支持挂载为新版文档（docx）的知识库页面',
                code='unsupported_wiki_type',
            )
        if not obj_token:
            raise FeishuError('无法解析 Wiki 节点对应的文档 ID', code='wiki_resolve_failed')
        return obj_token

    def get_document_title(self, document_id: str) -> str:
        data = self._request('GET', f'/open-apis/docx/v1/documents/{document_id}')
        document = data.get('document') or data
        return (document.get('title') or '').strip()

    def get_raw_content(self, document_id: str) -> str:
        data = self._request(
            'GET',
            f'/open-apis/docx/v1/documents/{document_id}/raw_content',
        )
        content = data.get('content')
        if content is None and isinstance(data, dict):
            content = data.get('content', '')
        return content if isinstance(content, str) else ''

    @staticmethod
    def normalize_content(content: str) -> str:
        text = (content or '').replace('\r\n', '\n').replace('\r', '\n')
        text = re.sub(r'\n{3,}', '\n\n', text).strip()
        if len(text) > MAX_CONTENT_LENGTH:
            raise FeishuError(
                f'文档正文过长（{len(text)} 字符），超过上限 {MAX_CONTENT_LENGTH}，请拆分文档后重试',
                code='content_too_long',
            )
        return text

    def fetch_requirement(self, url: str, user=None) -> Dict[str, Any]:
        if user is not None:
            self.user = user
        self.get_valid_user_access_token(self.user)

        parsed = self.parse_doc_url(url)
        document_id = parsed.token
        doc_type = parsed.doc_type

        if parsed.doc_type == 'wiki':
            document_id = self.resolve_wiki_to_docx(parsed.token)
            doc_type = 'wiki'

        title = self.get_document_title(document_id)
        content = self.normalize_content(self.get_raw_content(document_id))
        if not content:
            raise FeishuError(
                '文档正文为空，请确认文档有内容且当前飞书账号可阅读',
                code='empty_content',
            )

        if not title:
            title = '飞书需求文档'

        return {
            'title': title,
            'content': content,
            'source_url': parsed.source_url,
            'document_id': document_id,
            'doc_type': doc_type,
        }
