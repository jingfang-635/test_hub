# -*- coding: utf-8 -*-
"""Core 应用 Admin：统一通知配置、通知模板、性能监控"""
import logging

from django.contrib import admin
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.html import format_html, mark_safe

from apps.core.models import (
    UnifiedNotificationConfig, NotificationTemplate,
    RequestPerformanceLog, PerformanceStatistics,
)

logger = logging.getLogger(__name__)


def _hide_history_button(response):
    """向 change form 响应注入 CSS，隐藏右上角"历史"按钮（兼容 SimpleUI）。"""
    if isinstance(response, TemplateResponse):
        response.render()
        content = response.rendered_content
        style = '<style>.historylink,.history-link,li.history{display:none!important}</style>'
        if '</head>' in content:
            return HttpResponse(content.replace('</head>', style + '</head>', 1))
    return response


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

    def has_delete_permission(self, request, obj=None):
        # 详情页（change form）不显示删除按钮；列表页和删除确认页允许删除
        if obj is not None and '/change/' in request.path:
            return False
        return True

    def get_readonly_fields(self, request, obj=None):
        # 不显示创建/更新时间
        return ()

    def get_fieldsets(self, request, obj=None):
        # 是否默认模板、是否启用移至最后；不显示创建/更新时间
        base_fields = ('name', 'template_type', 'subject',
                       'description', 'content',
                       'is_default', 'is_active')
        return ((None, {'fields': base_fields}),)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # 变量说明显示在"模板内容"文本框下方（覆盖模型 help_text，去掉旧的变量列表）
        form.base_fields['content'].help_text = mark_safe(
            '支持以下变量替换（在模板内容中使用 {{变量名}} 即可）：<br>'
            '<b>任务相关：</b> {{task_name}} 任务名称、{{status_text}} 执行状态、'
            '{{execution_time}} 执行时间、{{task_type}} 任务类型<br>'
            '<b>测试相关：</b> {{title}} 测试标题、{{tester}} 测试人员、'
            '{{total_cases}} 用例总数、{{passed_cases}} 通过用例数、'
            '{{failed_cases}} 失败用例数、{{error_cases}} 错误用例数、'
            '{{skipped_cases}} 跳过用例数、{{runtime}} 执行时长、{{begin_time}} 开始时间'
        )
        return form

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        response = super().render_change_form(request, context, add, change, form_url, obj)
        # 去掉"保存并继续编辑"和"保存并增加另一个"按钮 + 不显示历史按钮（渲染前修改上下文）
        if hasattr(response, 'context_data') and response.context_data is not None:
            response.context_data['show_save_and_add_another'] = False
            response.context_data['show_save_and_continue'] = False
            response.context_data['show_history'] = False
        # CSS：隐藏多余按钮 + 加粗指定字段标签 + 隐藏历史按钮
        if isinstance(response, TemplateResponse):
            response.render()
            content = response.rendered_content
            style = ('<style>'
                     'input[name="_continue"],input[name="_addanother"],'
                     'button[name="_continue"],button[name="_addanother"]'
                     '{display:none!important}'
                     '.form-row.field-subject label,'
                     '.form-row.field-is_default label,'
                     '.form-row.field-is_active label,'
                     '.form-row.field-description label'
                     '{font-weight:bold!important}'
                     '.deletelink{display:none!important}'
                     '.historylink,.history-link,li.history{display:none!important}'
                     '</style>')
            if '</head>' in content:
                return HttpResponse(content.replace('</head>', style + '</head>', 1))
        return response

    def direct_delete_selected(self, request, queryset):
        """自定义批量删除：直接执行删除，跳过确认页。
        进入此方法即代表确认页被成功跳过（action直接执行删除）。"""
        count = queryset.count()
        user = getattr(request.user, 'username', 'unknown')
        ids = list(queryset.values_list('id', flat=True))
        logger.info(
            '[NotificationTemplate][批量删除-跳过确认页✅] 进入自定义 direct_delete_selected，'
            '用户=%s, 待删除数量=%d, IDs=%s', user, count, ids
        )
        deleted_count, _ = queryset.delete()
        logger.info(
            '[NotificationTemplate][批量删除-跳过确认页✅] 删除完成，用户=%s, 实际删除=%d条',
            user, deleted_count
        )
        self.message_user(request, f'成功删除 {deleted_count} 个通知模板')
    direct_delete_selected.short_description = '删除选中的通知模板'

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
            '[NotificationTemplate][get_actions] 原有默认delete_selected=%s, '
            '当前注册的action keys=%s',
            had_default, list(actions.keys())
        )
        return actions

    def changelist_view(self, request, extra_context=None):
        """兜底拦截：如前端仍触发确认页POST，直接执行删除并返回列表页。
        进入此拦截分支代表确认页没有被跳过，走了兜底逻辑。"""
        if request.method == 'POST':
            ids = request.POST.getlist('_selected_action')
            if ids and 'post' in request.POST:
                user = getattr(request.user, 'username', 'unknown')
                logger.warning(
                    '[NotificationTemplate][批量删除-兜底触发⚠️] 确认页未被跳过，'
                    '走了changelist_view兜底分支，用户=%s, 待删除IDs=%s, POST keys=%s',
                    user, ids, list(request.POST.keys())
                )
                deleted_count, _ = NotificationTemplate.objects.filter(id__in=ids).delete()
                logger.info(
                    '[NotificationTemplate][批量删除-兜底触发⚠️] 兜底删除完成，用户=%s, 删除=%d条',
                    user, deleted_count
                )
                self.message_user(request, f'成功删除 {deleted_count} 个通知模板')
                return HttpResponseRedirect(request.path)
        return super().changelist_view(request, extra_context)

    def delete_view(self, request, object_id, extra_context=None):
        """单条删除：拦截确认页POST，直接删除后返回列表页。"""
        user = getattr(request.user, 'username', 'unknown')
        if request.method == 'POST':
            if 'post' in request.POST:
                logger.info(
                    '[NotificationTemplate][单条删除-跳过确认页✅] 进入直接删除分支，'
                    '用户=%s, object_id=%s', user, object_id
                )
                obj = self.get_object(request, object_id)
                if obj:
                    obj.delete()
                    logger.info(
                        '[NotificationTemplate][单条删除-跳过确认页✅] 删除完成，用户=%s, id=%s',
                        user, object_id
                    )
                    self.message_user(request, '成功删除 1 个通知模板')
                else:
                    logger.warning(
                        '[NotificationTemplate][单条删除] 未找到对象，用户=%s, id=%s',
                        user, object_id
                    )
                return HttpResponseRedirect('../')
            else:
                logger.debug(
                    '[NotificationTemplate][单条删除] POST但无post参数，可能走其他流程，'
                    '用户=%s, object_id=%s, POST keys=%s',
                    user, object_id, list(request.POST.keys())
                )
        else:
            logger.debug(
                '[NotificationTemplate][单条删除] GET进入确认页（或还未点击确认），'
                '用户=%s, object_id=%s', user, object_id
            )
        return super().delete_view(request, object_id, extra_context)


@admin.register(RequestPerformanceLog)
class RequestPerformanceLogAdmin(admin.ModelAdmin):
    list_display = ('path', 'method', 'response_time_display', 'status_code_display', 'user_display', 'created_at')
    list_filter = ('method', 'status_code', 'created_at')
    search_fields = ('path', 'user_agent')
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
        进入此拦截分支代表确认页没有被跳过，走了兜底逻辑。"""
        if request.method == 'POST':
            ids = request.POST.getlist('_selected_action')
            if ids and 'post' in request.POST:
                user = getattr(request.user, 'username', 'unknown')
                logger.warning(
                    '[RequestPerformanceLog][批量删除-兜底触发⚠️] 确认页未被跳过，'
                    '走了changelist_view兜底分支，用户=%s, 待删除IDs=%s, POST keys=%s',
                    user, ids, list(request.POST.keys())
                )
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
        if value > 1000:
            color = 'red'
        elif value > 500:
            color = 'orange'
        else:
            color = 'green'
        return format_html('<span style="color:{};font-weight:bold;">{}ms</span>', color, f"{value:.2f}")
    response_time_display.short_description = '响应时间'
    response_time_display.admin_order_field = 'response_time'

    def status_code_display(self, obj):
        """状态码颜色标记: 5xx红, 4xx橙, 2xx绿"""
        code = int(obj.status_code or 0)
        if code >= 500:
            color = 'red'
        elif code >= 400:
            color = 'orange'
        else:
            color = 'green'
        return format_html('<span style="color:{};font-weight:bold;">{}</span>', color, code)
    status_code_display.short_description = '状态码'
    status_code_display.admin_order_field = 'status_code'


@admin.register(PerformanceStatistics)
class PerformanceStatisticsAdmin(admin.ModelAdmin):
    list_display = ('date', 'total_requests', 'avg_response_time_display', 'error_rate', 'slow_rate')
    list_filter = ('date',)
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

    def avg_response_time_display(self, obj):
        """平均响应时间颜色标记: >1s红, >500ms橙, 正常绿"""
        value = float(obj.avg_response_time or 0)
        if value > 1000:
            color = 'red'
        elif value > 500:
            color = 'orange'
        else:
            color = 'green'
        return format_html('<span style="color:{};font-weight:bold;">{}ms</span>', color, f"{value:.2f}")
    avg_response_time_display.short_description = '平均响应时间'
    avg_response_time_display.admin_order_field = 'avg_response_time'

    def error_rate(self, obj):
        """错误率颜色标记: >5%红, >1%橙, 正常绿"""
        total = int(obj.total_requests or 0)
        if total == 0:
            return '0%'
        errors = int(obj.error_count or 0)
        rate = errors / total * 100
        color = 'red' if rate > 5 else ('orange' if rate > 1 else 'green')
        return format_html('<span style="color:{};">{}%</span>', color, f"{rate:.2f}")
    error_rate.short_description = '错误率'

    def slow_rate(self, obj):
        """慢请求率颜色标记: >10%红, >5%橙, 正常绿"""
        total = int(obj.total_requests or 0)
        if total == 0:
            return '0%'
        slow = int(obj.slow_requests or 0)
        rate = slow / total * 100
        color = 'red' if rate > 10 else ('orange' if rate > 5 else 'green')
        return format_html('<span style="color:{};">{}%</span>', color, f"{rate:.2f}")
    slow_rate.short_description = '慢请求率'
