# -*- coding: utf-8 -*-
"""
通知发送服务：模板渲染 + 邮件/Webhook 发送
- 支持通知模板变量替换（{{变量}}）
- 支持邮件通知（收件人可为用户ID或邮箱地址）
"""
import logging

logger = logging.getLogger(__name__)


def render_template(template, context):
    """渲染通知模板，返回 (content, subject)"""
    return template.render(context), template.render_subject(context)


def resolve_recipients(email_recipients):
    """解析收件人：用户ID自动获取邮箱，邮箱地址直接使用"""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    emails = []
    for item in email_recipients or []:
        if isinstance(item, int) or (isinstance(item, str) and item.isdigit()):
            try:
                user = User.objects.get(id=int(item))
                if user.email:
                    emails.append(user.email)
            except User.DoesNotExist:
                logger.warning(f"通知收件人用户ID {item} 不存在")
        elif '@' in str(item):
            emails.append(str(item))
    return emails


def send_email_notification(template, context, recipients, attach_report_path=None):
    """发送邮件通知

    Args:
        template: NotificationTemplate 实例
        context: 变量字典
        recipients: 邮箱列表
        attach_report_path: 可选报告附件路径
    Returns:
        bool: 是否发送成功
    """
    from .email_service import send_notification_mail

    if not recipients:
        logger.warning("邮件通知收件人为空，跳过发送")
        return False

    content, subject = render_template(template, context)
    if not subject:
        subject = template.name

    ok, detail = send_notification_mail(
        subject,
        content,
        recipients,
        attach_report_path=attach_report_path,
        html=(getattr(template, 'template_type', '') == 'html'),
    )
    if not ok:
        logger.error('发送邮件通知失败: %s', detail)
    return ok


def send_notification_by_config(config, context, task_name='', status_text=''):
    """根据 UnifiedNotificationConfig 发送通知（Webhook + 邮件）
    Args:
        config: UnifiedNotificationConfig 实例
        context: 模板变量字典
        task_name: 任务名称（用于默认文案）
        status_text: 状态文本（成功/失败）
    """
    # 选择模板：优先 config.notification_template，否则用默认模板
    from apps.core.models import NotificationTemplate
    template = config.notification_template
    if not template:
        template = NotificationTemplate.objects.filter(is_default=True, is_active=True).first()

    # 邮件通知
    if config.email_recipients:
        recipients = resolve_recipients(config.email_recipients)
        if recipients:
            if template:
                send_email_notification(template, context, recipients,
                                        attach_report_path=config.email_attach_report or None)
            else:
                # 无模板时用简单文本
                from .email_service import send_notification_mail
                subject = f"TestHub通知: {task_name} {status_text}"
                content = "\n".join(f"{k}: {v}" for k, v in context.items())
                send_notification_mail(subject, content, recipients)

    # Webhook 通知（复用现有 get_webhook_bots 逻辑）
    # 此处仅做框架，具体 Webhook 发送逻辑保留在原有模块（app_automation/tasks.py 等）
    # 避免与现有 webhook 发送重复


def send_test_webhook(webhook_url, bot_name='', timeout=10):
    """向 Webhook 地址发送一条测试消息（当前仅支持飞书机器人）。

    Args:
        webhook_url: 飞书自定义机器人 Webhook 地址
        bot_name: 机器人名称（仅用于日志）
        timeout: 请求超时秒数

    Returns:
        (ok: bool, detail: str)
    """
    import requests

    webhook_url = (webhook_url or '').strip()
    if not webhook_url:
        return False, 'Webhook URL 为空'

    message_data = {
        'msg_type': 'interactive',
        'card': {
            'elements': [
                {
                    'tag': 'div',
                    'text': {
                        'content': '**TestHub 通知测试**\n\n这是一条测试消息，说明该机器人配置可用。\n\n如收到本消息，说明执行关键词与 Webhook 均配置正确。',
                        'tag': 'lark_md',
                    },
                }
            ],
            'header': {
                'title': {'content': 'TestHub 通知测试', 'tag': 'plain_text'},
                'template': 'blue',
            },
        },
    }

    try:
        resp = requests.post(
            webhook_url,
            json=message_data,
            headers={'Content-Type': 'application/json'},
            timeout=timeout,
        )
    except Exception as exc:
        logger.warning('Webhook 测试请求失败 (%s): %s', bot_name, exc)
        return False, f'请求失败: {exc}'

    if resp.status_code != 200:
        return False, f'HTTP {resp.status_code}: {resp.text[:200]}'

    # 飞书成功返回 code=0；非 0 通常是安全设置不匹配
    try:
        payload = resp.json()
    except Exception:
        return True, '已发送（响应非 JSON，请到群里确认）'

    code = payload.get('code', payload.get('StatusCode', 0))
    if code not in (0, None):
        msg = payload.get('msg') or payload.get('StatusMessage') or ''
        hint = ''
        if code == 19021:
            hint = '（机器人安全设置勾选了「签名校验」，TestHub 暂不支持，请改用「自定义关键词」）'
        elif code == 19024:
            hint = '（机器人安全设置勾选了「IP 白名单」，请把本服务出口 IP 加入白名单，或改用「自定义关键词」）'
        elif code == 19001:
            hint = '（Webhook 地址无效或已被重置，请到飞书群重新复制）'
        logger.warning('Webhook 测试失败 (%s): code=%s msg=%s', bot_name, code, msg)
        return False, f'飞书返回错误 code={code}: {msg}{hint}'

    logger.info('Webhook 测试消息已发送 (%s)', bot_name)
    return True, '测试消息已发送，请到飞书群确认'
