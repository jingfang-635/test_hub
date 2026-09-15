# -*- coding: utf-8 -*-
"""Core 应用 Admin：统一通知配置、通知模板、性能监控"""
import logging

from django.contrib import admin
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.html import format_html

from apps.core.models import (
    EmailConfig, UnifiedNotificationConfig, NotificationTemplate,
    RequestPerformanceLog, PerformanceStatistics, Skill,
    MCPServer, ModuleSwitch,
)

logger = logging.getLogger(__name__)



def _pill(text, kind='primary'):
    """生成与前端测试报告列表一致的圆角标签 HTML（内联样式，不依赖外部 CSS）。"""
    styles = {
        'success': 'background:#f0f9eb;color:#67c23a',
        'danger': 'background:#fef0f0;color:#f56c6c',
        'warning': 'background:#fdf6ec;color:#e6a23c',
        'info': 'background:#f3e8ff;color:#9b59b6',
        'primary': 'background:rgba(108,92,231,0.12);color:#6c5ce7',
        'muted': 'background:#f4f4f5;color:#909399',
    }
    style = styles.get(kind, styles['primary'])
    return format_html(
        '<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
        'font-size:12px;line-height:20px;font-weight:500;white-space:nowrap;{}">{}</span>',
        style, text
    )


def _rate_dot(text, color):
    """通过率/占比：圆点 + 文本（对齐测试报告通过率列）。"""
    return format_html(
        '<span style="display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#303133;">'
        '<i style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{};flex-shrink:0;"></i>{}</span>',
        color, text
    )


def _hide_history_button(response):
    """向 change form 响应注入 CSS，隐藏右上角"历史"按钮（兼容 SimpleUI）。"""
    if isinstance(response, TemplateResponse):
        response.render()
        content = response.rendered_content
        style = '<style>.historylink,.history-link,li.history{display:none!important}</style>'
        if '</head>' in content:
            return HttpResponse(content.replace('</head>', style + '</head>', 1))
    return response


@admin.register(EmailConfig)
class EmailConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'sender_email', 'smtp_host', 'smtp_port', 'use_ssl', 'is_active', 'updated_at')
    list_filter = ('is_active', 'use_ssl', 'use_tls')
    readonly_fields = ('created_at', 'updated_at')
    search_fields = ('name', 'sender_email', 'smtp_host')

    fieldsets = (
        (None, {
            'fields': ('name', 'is_active')
        }),
        ('SMTP 服务器', {
            'fields': ('smtp_host', 'smtp_port', 'use_ssl', 'use_tls')
        }),
        ('账号', {
            'fields': ('sender_email', 'smtp_password')
        }),
        ('通知收件人', {
            'fields': ('recipient_emails',),
            'description': 'JSON 数组，例如 ["qa@example.com", "dev@example.com"]；将作为定时任务「通知邮箱」下拉的候选列表'
        }),
    )


@admin.register(UnifiedNotificationConfig)
class UnifiedNotificationConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'config_type', 'is_default', 'is_active', 'has_email', 'created_at')
    list_filter = ('config_type', 'is_default', 'is_active')
    search_fields = ('name',)
    readonly_fields = ('created_at', 'updated_at')

    def has_email(self, obj):
        return bool(obj.email_recipients)
    has_email.boolean = True
    has_email.short_description = '邮件通知'


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'template_type', 'is_default', 'is_active', 'updated_at')
    list_filter = ('template_type', 'is_default', 'is_active')
    search_fields = ('name', 'subject', 'content')
    exclude = ('variables',)  # 变量由模板内容中的 {{变量}} 占位符决定，无需手工维护


@admin.register(RequestPerformanceLog)
class RequestPerformanceLogAdmin(admin.ModelAdmin):
    list_display = ('path', 'method_display', 'response_time_display', 'status_code_display', 'user_display', 'created_at')
    list_filter = ('method', 'status_code', 'created_at')
    search_fields = ('path', 'user_agent')
    sortable_by = ()
    readonly_fields = ('path', 'method', 'response_time', 'status_code', 'user_display', 'ip_address', 'user_agent', 'created_at')
    exclude = ('user',)  # 排除真实字段 user，详情页仅保留 user_display 纯文本展示
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        # 允许查看详情（只读），即使禁止编辑
        return True

    def has_change_permission(self, request, obj=None):
        # 禁止编辑：去掉"保存"、"保存并继续编辑"、"保存并添加另一个"按钮
        return False

    def has_delete_permission(self, request, obj=None):
        # 禁止删除：去掉"删除"按钮
        return False

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = '日志详情'
        extra_context['show_history'] = False  # 原生 Django 生效
        response = super().change_view(request, object_id, form_url, extra_context)
        return _hide_history_button(response)  # SimpleUI 兜底：CSS 隐藏历史按钮

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')

    def method_display(self, obj):
        """请求方法：紫色标签（对齐测试引擎标签风格）。"""
        return _pill(obj.method or '-', 'info')
    method_display.short_description = '请求方法'
    method_display.admin_order_field = 'method'

    def user_display(self, obj):
        """用户字段纯文本展示，去掉指向用户管理页的跳转链接。"""
        return str(obj.user) if obj.user else '-'
    user_display.short_description = '用户'
    user_display.admin_order_field = 'user'

    def direct_delete_selected(self, request, queryset):
        """自定义批量删除：直接执行删除，跳过确认页。
        进入此方法即代表确认页被成功跳过（action直接执行删除）。"""
        count = queryset.count()
        user = getattr(request.user, 'username', 'unknown')
        ids = list(queryset.values_list('id', flat=True))
        logger.info(
            '[RequestPerformanceLog][批量删除-跳过确认页✅] 进入自定义 direct_delete_selected，'
            '用户=%s, 待删除数量=%d, IDs=%s', user, count, ids
        )
        deleted_count, _ = queryset.delete()
        logger.info(
            '[RequestPerformanceLog][批量删除-跳过确认页✅] 删除完成，用户=%s, 实际删除=%d条',
            user, deleted_count
        )
        self.message_user(request, f'成功删除 {deleted_count} 条请求性能日志')
    direct_delete_selected.short_description = '删除选中的请求性能日志'

    def get_actions(self, request):
        actions = super().get_actions(request)
        had_default = 'delete_selected' in actions
        # 移除 Django 默认的 delete_selected（会跳转确认页）
        if had_default:
            del actions['delete_selected']
        # 将自定义的 direct_delete_selected 注册为 delete_selected 名称，
        # 保证 SimpleUI 前端的删除按钮仍能正确识别触发
        actions['delete_selected'] = (
            self.__class__.direct_delete_selected,
            'delete_selected',
            self.__class__.direct_delete_selected.short_description
        )
        logger.debug(
            '[RequestPerformanceLog][get_actions] 原有默认delete_selected=%s, '
            '当前注册的action keys=%s',
            had_default, list(actions.keys())
        )
        return actions

    def changelist_view(self, request, extra_context=None):
        """兜底拦截：如前端仍触发确认页POST，直接执行删除并返回列表页。
        进入此拦截分支代表确认页没有被跳过，走了兜底逻辑。
        支持 select_across=1 时删除当前筛选条件下的全部记录。"""
        if request.method == 'POST':
            ids = request.POST.getlist('_selected_action')
            select_across = request.POST.get('select_across') in ('1', 'true', 'True', 'on')
            if (ids or select_across) and 'post' in request.POST:
                user = getattr(request.user, 'username', 'unknown')
                logger.warning(
                    '[RequestPerformanceLog][批量删除-兜底触发⚠️] 确认页未被跳过，'
                    '走了changelist_view兜底分支，用户=%s, select_across=%s, 待删除IDs=%s, POST keys=%s',
                    user, select_across, ids, list(request.POST.keys())
                )
                if select_across:
                    # 与表头全选跨页语义一致：删除当前筛选下全部记录
                    changelist = self.get_changelist_instance(request)
                    queryset = changelist.get_queryset(request)
                    deleted_count, _ = queryset.delete()
                else:
                    deleted_count, _ = RequestPerformanceLog.objects.filter(id__in=ids).delete()
                logger.info(
                    '[RequestPerformanceLog][批量删除-兜底触发⚠️] 兜底删除完成，用户=%s, 删除=%d条',
                    user, deleted_count
                )
                self.message_user(request, f'成功删除 {deleted_count} 条请求性能日志')
                return HttpResponseRedirect(request.path)
        return super().changelist_view(request, extra_context)

    def delete_view(self, request, object_id, extra_context=None):
        """单条删除：拦截确认页POST，直接删除后返回列表页。"""
        user = getattr(request.user, 'username', 'unknown')
        if request.method == 'POST':
            # 确认页点击"是"后，POST请求带有 post 参数
            if 'post' in request.POST:
                logger.info(
                    '[RequestPerformanceLog][单条删除-跳过确认页✅] 进入直接删除分支，'
                    '用户=%s, object_id=%s', user, object_id
                )
                obj = self.get_object(request, object_id)
                if obj:
                    obj.delete()
                    logger.info(
                        '[RequestPerformanceLog][单条删除-跳过确认页✅] 删除完成，用户=%s, id=%s',
                        user, object_id
                    )
                    self.message_user(request, '成功删除 1 条请求性能日志')
                else:
                    logger.warning(
                        '[RequestPerformanceLog][单条删除] 未找到对象，用户=%s, id=%s',
                        user, object_id
                    )
                return HttpResponseRedirect('../')
            else:
                logger.debug(
                    '[RequestPerformanceLog][单条删除] POST但无post参数，可能走其他流程，'
                    '用户=%s, object_id=%s, POST keys=%s',
                    user, object_id, list(request.POST.keys())
                )
        else:
            logger.debug(
                '[RequestPerformanceLog][单条删除] GET进入确认页（或还未点击确认），'
                '用户=%s, object_id=%s', user, object_id
            )
        return super().delete_view(request, object_id, extra_context)

    def response_time_display(self, obj):
        """慢请求颜色标记: >1s红, >500ms橙, 正常绿"""
        value = float(obj.response_time or 0)
        label = f"{value:.2f}ms"
        if value > 1000:
            return _pill(label, 'danger')
        if value > 500:
            return _pill(label, 'warning')
        return _pill(label, 'success')
    response_time_display.short_description = '响应时间'
    response_time_display.admin_order_field = 'response_time'

    def status_code_display(self, obj):
        """状态码颜色标记: 5xx红, 4xx橙, 2xx绿"""
        code = int(obj.status_code or 0)
        if code >= 500:
            return _pill(str(code), 'danger')
        if code >= 400:
            return _pill(str(code), 'warning')
        return _pill(str(code), 'success')
    status_code_display.short_description = '状态码'
    status_code_display.admin_order_field = 'status_code'


@admin.register(PerformanceStatistics)
class PerformanceStatisticsAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_requests_display', 'avg_response_time_display', 'error_rate', 'slow_rate')
    list_filter = ('date',)
    sortable_by = ()
    readonly_fields = ('date', 'total_requests', 'avg_response_time', 'max_response_time',
                       'min_response_time', 'error_count', 'slow_requests', 'created_at', 'updated_at')

    def has_add_permission(self, request):
        return False

    def has_view_permission(self, request, obj=None):
        # 允许查看详情（只读），即使禁止编辑
        return True

    def has_change_permission(self, request, obj=None):
        # 禁止编辑：去掉“保存”、“保存并继续编辑”、“保存并添加另一个”按钮
        return False

    def has_delete_permission(self, request, obj=None):
        # 列表页（obj=None）：允许删除→显示勾选框和批量删除
        # 详情页（obj存在）：禁止删除→去掉“删除”按钮
        return obj is None

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['title'] = '性能统计详情'
        extra_context['show_history'] = False  # 原生 Django 生效
        response = super().change_view(request, object_id, form_url, extra_context)
        return _hide_history_button(response)  # SimpleUI 兜底：CSS 隐藏历史按钮

    def total_requests_display(self, obj):
        return format_html('<span style="color:#67c23a;font-weight:600;">{}</span>', obj.total_requests or 0)
    total_requests_display.short_description = '总请求数'
    total_requests_display.admin_order_field = 'total_requests'

    def avg_response_time_display(self, obj):
        """平均响应时间颜色标记: >1s红, >500ms橙, 正常绿"""
        value = float(obj.avg_response_time or 0)
        label = f"{value:.2f}ms"
        if value > 1000:
            return _pill(label, 'danger')
        if value > 500:
            return _pill(label, 'warning')
        return _pill(label, 'success')
    avg_response_time_display.short_description = '平均响应时间'
    avg_response_time_display.admin_order_field = 'avg_response_time'

    def error_rate(self, obj):
        """错误率颜色标记: >5%红, >1%橙, 正常绿（圆点样式对齐通过率列）"""
        total = int(obj.total_requests or 0)
        if total == 0:
            return _rate_dot('0%', '#c0c4cc')
        errors = int(obj.error_count or 0)
        rate = errors / total * 100
        color = '#f56c6c' if rate > 5 else ('#e6a23c' if rate > 1 else '#67c23a')
        return _rate_dot(f"{rate:.2f}%", color)
    error_rate.short_description = '错误率'

    def slow_rate(self, obj):
        """慢请求率颜色标记: >10%红, >5%橙, 正常绿（圆点样式对齐通过率列）"""
        total = int(obj.total_requests or 0)
        if total == 0:
            return _rate_dot('0%', '#c0c4cc')
        slow = int(obj.slow_requests or 0)
        rate = slow / total * 100
        color = '#f56c6c' if rate > 10 else ('#e6a23c' if rate > 5 else '#67c23a')
        return _rate_dot(f"{rate:.2f}%", color)
    slow_rate.short_description = '慢请求率'


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_enabled', 'is_builtin', 'updated_at')
    list_filter = ('is_enabled', 'is_builtin')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'is_builtin')


@admin.register(MCPServer)
class MCPServerAdmin(admin.ModelAdmin):
    list_display = ('name', 'transport', 'is_enabled', 'connection_status', 'updated_at')
    list_filter = ('transport', 'is_enabled', 'connection_status')
    search_fields = ('name', 'description')
    readonly_fields = ('connection_status', 'tools', 'last_error', 'last_tested_at', 'created_at', 'updated_at')


@admin.register(ModuleSwitch)
class ModuleSwitchAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'location_display', 'sort_order', 'is_enabled', 'is_builtin', 'updated_at')
    list_filter = ('location', 'is_enabled', 'is_builtin')
    search_fields = ('key', 'name', 'description')
    list_editable = ('is_enabled',)
    readonly_fields = ('created_at', 'updated_at', 'is_builtin')

    def location_display(self, obj):
        return obj.get_location_display()
    location_display.short_description = '显示位置'
    location_display.admin_order_field = 'location'

