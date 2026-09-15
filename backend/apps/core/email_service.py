# -*- coding: utf-8 -*-
"""
邮箱配置服务：让定时任务邮件通知使用「配置中心 → 定时任务配置」中维护的 SMTP 配置。

优先级：数据库 EmailConfig（已启用且必填项完整）> settings 的 EMAIL_* / DEFAULT_FROM_EMAIL。

保存邮箱配置后立即生效，无需修改 config.yaml、环境变量或重启服务。
"""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def get_active_email_config():
    """返回已启用且配置完整的邮箱配置；否则返回 None（由调用方回退到 settings）"""
    try:
        from .models import EmailConfig
        config = EmailConfig.get_solo()
    except Exception:  # 表未迁移等异常不应中断通知流程
        logger.debug('读取 EmailConfig 失败，回退到 settings 邮件配置', exc_info=True)
        return None

    if config and config.is_active and config.is_configured:
        # 非 SSL/TLS 直连也需要端口，缺端口视为配置不完整
        if config.smtp_port:
            return config
    return None


def _sender_from_settings():
    """回退发件人：DEFAULT_FROM_EMAIL > EMAIL_HOST_USER"""
    return (
        getattr(settings, 'DEFAULT_FROM_EMAIL', '')
        or getattr(settings, 'EMAIL_HOST_USER', '')
        or ''
    )


def get_sender_address(config=None):
    """获取发件人地址"""
    if config is not None and config.sender_email:
        return config.sender_email
    return _sender_from_settings()


def build_email_connection(config=None):
    """构建邮件连接。

    传入 config 时使用数据库中的 SMTP 配置，否则使用 settings 默认连接。
    """
    from django.core.mail import get_connection

    timeout = getattr(settings, 'EMAIL_TIMEOUT', 30) or 30

    if config is None:
        return get_connection(fail_silently=False)

    return get_connection(
        backend=getattr(settings, 'EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend'),
        host=config.smtp_host,
        port=config.smtp_port,
        username=config.sender_email,
        password=config.smtp_password,
        use_tls=config.use_tls,
        use_ssl=config.use_ssl,
        timeout=timeout,
        fail_silently=False,
    )


def send_notification_mail(subject, message, recipients, config=None, attach_report_path=None, html=False):
    """发送通知邮件。

    Args:
        subject: 邮件主题
        message: 邮件正文
        recipients: 收件人邮箱列表
        config: EmailConfig 实例；为 None 时自动取启用的配置，取不到则回退 settings
        attach_report_path: 可选附件路径
        html: 是否按 HTML 邮件发送

    Returns:
        (ok: bool, detail: str)
    """
    from django.core.mail import EmailMessage

    recipients = [r for r in (recipients or []) if r]
    if not recipients:
        return False, '收件人为空'

    if config is None:
        config = get_active_email_config()

    from_email = get_sender_address(config)

    try:
        connection = build_email_connection(config)
        mail = EmailMessage(
            subject=subject,
            body=message,
            from_email=from_email,
            to=recipients,
            connection=connection,
        )
        if html:
            mail.content_subtype = 'html'
        if attach_report_path:
            mail.attach_file(attach_report_path)
        mail.send(fail_silently=False)
        logger.info('邮件通知已发送至 %s: %s (发件人 %s)', recipients, subject, from_email)
        return True, ''
    except Exception as exc:
        logger.error('发送邮件通知失败: %s', exc, exc_info=True)
        return False, str(exc)


def test_email_config(config, recipient=None):
    """测试邮箱配置：校验连接并按需发送一封测试邮件。

    Returns:
        (ok: bool, detail: str)
    """
    from django.core.mail import EmailMessage

    try:
        connection = build_email_connection(config)
        # open() 即完成握手 + 登录，能直接暴露账号/授权码/端口错误
        connection.open()
        connection.close()
    except Exception as exc:
        logger.warning('邮箱连接测试失败: %s', exc)
        return False, f'连接失败: {exc}'

    target = (recipient or '').strip() or config.sender_email
    if not target:
        return True, '连接成功（未提供收件人，跳过发送测试邮件）'

    try:
        mail = EmailMessage(
            subject='[TestHub] 邮箱配置测试',
            body='这是一封来自 TestHub 定时任务配置的测试邮件，说明邮箱配置可用。',
            from_email=get_sender_address(config),
            to=[target],
            connection=build_email_connection(config),
        )
        mail.send(fail_silently=False)
        return True, f'连接成功，测试邮件已发送至 {target}'
    except Exception as exc:
        logger.warning('测试邮件发送失败: %s', exc)
        return False, f'连接成功但发送失败: {exc}'


def get_notification_recipients():
    """返回「通知邮箱」候选列表。

    优先取邮箱配置中的收件人列表，其次回退到 settings 的 EMAIL_HOST_USER。
    """
    config = get_active_email_config()
    if config and config.recipient_emails:
        return list(config.recipient_emails)

    fallback = (getattr(settings, 'EMAIL_HOST_USER', '') or '').strip()
    return [fallback] if fallback else []
