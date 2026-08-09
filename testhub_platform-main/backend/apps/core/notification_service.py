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
    from django.core.mail import send_mail
    from django.conf import settings

    if not recipients:
        logger.warning("邮件通知收件人为空，跳过发送")
        return False

    content, subject = render_template(template, context)
    if not subject:
        subject = template.name

    try:
        if attach_report_path:
            from django.core.mail import EmailMessage
            msg = EmailMessage(subject=subject, body=content,
                               from_email=settings.DEFAULT_FROM_EMAIL, to=recipients)
            msg.attach_file(attach_report_path)
            msg.send(fail_silently=False)
        else:
            send_mail(subject=subject, message=content,
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      recipient_list=recipients, fail_silently=False)
        logger.info(f"邮件通知已发送至 {recipients}: {subject}")
        return True
    except Exception as e:
        logger.error(f"发送邮件通知失败: {e}", exc_info=True)
        return False


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
                from django.core.mail import send_mail
                from django.conf import settings
                subject = f"TestHub通知: {task_name} {status_text}"
                content = "\n".join(f"{k}: {v}" for k, v in context.items())
                try:
                    send_mail(subject=subject, message=content,
                              from_email=settings.DEFAULT_FROM_EMAIL,
                              recipient_list=recipients, fail_silently=False)
                except Exception as e:
                    logger.error(f"发送邮件通知失败: {e}")

    # Webhook 通知（复用现有 get_webhook_bots 逻辑）
    # 此处仅做框架，具体 Webhook 发送逻辑保留在原有模块（app_automation/tasks.py 等）
    # 避免与现有 webhook 发送重复
