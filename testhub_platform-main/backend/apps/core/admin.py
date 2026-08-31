# -*- coding: utf-8 -*-
"""Core 应用 Admin：统一通知配置、通知模板、性能监控"""
import logging

from django.contrib import admin
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.html import format_html, mark_safe

from apps.core.models import (
    UnifiedNotificationConfig, NotificationTemplate,
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
    list_display = (
        'name', 'template_type_display', 'is_default_display',
        'is_active_display', 'updated_at', 'edit_action',
    )
    list_filter = ('template_type', 'is_default', 'is_active')
    search_fields = ('name', 'subject', 'content')
    sortable_by = ()

    def template_type_display(self, obj):
        kind_map = {'markdown': 'info', 'html': 'primary', 'text': 'muted'}
        return _pill(obj.get_template_type_display(), kind_map.get(obj.template_type, 'primary'))
    template_type_display.short_description = '模板类型'
    template_type_display.admin_order_field = 'template_type'

    def is_default_display(self, obj):
        return _pill('默认', 'warning') if obj.is_default else _pill('否', 'muted')
    is_default_display.short_description = '是否默认'
    is_default_display.admin_order_field = 'is_default'

    def is_active_display(self, obj):
        return _pill('启用', 'success') if obj.is_active else _pill('停用', 'danger')
    is_active_display.short_description = '是否启用'
    is_active_display.admin_order_field = 'is_active'

    def edit_action(self, obj):
        """列表行操作：跳转编辑页，可修改模板内容。"""
        from django.urls import reverse
        url = reverse('admin:core_notificationtemplate_change', args=[obj.pk])
        return format_html('<a class="th-edit-btn" href="{}">编辑</a>', url)
    edit_action.short_description = '操作'
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
        # CSS：对齐用例表单风格 + 隐藏多余按钮/历史
        if isinstance(response, TemplateResponse):
            response.render()
            content = response.rendered_content
            style = '''<style id="th-notification-template-form">
body.model-notificationtemplate{background:#f5f7fa!important}
#content-main.form-main,.form-main{
  background:#fff!important;border-radius:12px!important;padding:28px 32px 24px!important;
  border:1px solid #ebeef5!important;box-shadow:0 1px 4px rgba(0,0,0,.04)!important;
  max-width:960px!important;margin:0 auto!important;box-sizing:border-box!important
}
.page-header{margin:0 0 20px!important;padding:0 0 12px!important;border-bottom:1px solid #ebeef5!important}
.form-row{margin:0 0 20px!important;padding:0!important;border:none!important}
.form-row label{color:#606266!important;font-size:14px!important;font-weight:500!important}
.form-row label.required:before,.required label:before{content:"*"!important;color:#f56c6c!important;margin-right:4px!important}
.form-row input[type=text],.form-row input[type=url],.form-row select,.form-row textarea,
.el-input__inner,.el-textarea__inner{
  background:#fff!important;border:1px solid #dcdfe6!important;border-radius:4px!important;
  color:#606266!important;font-size:14px!important;padding:8px 12px!important;box-shadow:none!important
}
.form-row textarea,.el-textarea__inner{min-height:120px!important}
.form-row.field-content textarea{min-height:180px!important}
.form-row input:focus,.form-row select:focus,.form-row textarea:focus,
.el-input.is-focus .el-input__inner,.el-textarea__inner:focus{
  border-color:#6c5ce7!important;outline:none!important;box-shadow:0 0 0 1px rgba(108,92,231,.15)!important
}
.form-row .help{color:#909399!important;font-size:12px!important;line-height:1.6!important}
.submit-row{border-top:1px solid #ebeef5!important;padding-top:20px!important;background:transparent!important;text-align:left!important}
.submit-row .el-button--primary,button[name=_save]{
  background:#6c5ce7!important;border-color:#6c5ce7!important;color:#fff!important;
  border-radius:4px!important;padding:10px 20px!important;
  box-shadow:0 4px 12px rgba(108,92,231,.28)!important
}
.submit-row .el-button--primary:hover,button[name=_save]:hover{background:#8b7cf0!important;border-color:#8b7cf0!important}
input[name=_continue],input[name=_addanother],button[name=_continue],button[name=_addanother],
.deletelink,.historylink,.history-link,li.history{display:none!important}
.form-row.field-subject label,.form-row.field-is_default label,
.form-row.field-is_active label,.form-row.field-description label{font-weight:600!important}
input[type=checkbox]{accent-color:#6c5ce7!important}
</style>'''
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

