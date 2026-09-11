"""
Core 应用模型
"""
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class UnifiedNotificationConfig(models.Model):
    """统一通知配置模型 - 用于配置飞书、企微、钉钉机器人"""

    CONFIG_TYPE_CHOICES = [
        ('webhook_feishu', '飞书机器人'),
        ('webhook_wechat', '企业微信机器人'),
        ('webhook_dingtalk', '钉钉机器人'),
    ]

    name = models.CharField(max_length=100, verbose_name='配置名称', help_text='用于标识该通知配置的名称')
    config_type = models.CharField(max_length=20, choices=CONFIG_TYPE_CHOICES, default='webhook_feishu',
                                   verbose_name='配置类型')
    webhook_bots = models.JSONField(default=dict, blank=True, null=True, verbose_name='Webhook机器人配置',
                                    help_text='飞书、企微、钉钉机器人配置')
    is_default = models.BooleanField(default=False, verbose_name='是否默认配置')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    # 邮件通知配置（通知模板系统增强）
    email_recipients = models.JSONField(default=list, blank=True, verbose_name='邮件收件人',
                                        help_text='用户ID或邮箱地址列表')
    email_attach_report = models.BooleanField(default=False, verbose_name='邮件附件报告')
    # 关联通知模板
    notification_template = models.ForeignKey(
        'core.NotificationTemplate', on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='通知模板', related_name='notification_configs'
    )

    class Meta:
        db_table = 'unified_notification_configs'
        verbose_name = '统一通知配置'
        verbose_name_plural = '统一通知配置'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['config_type']),
            models.Index(fields=['is_default']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return f"{self.name} - {self.get_config_type_display()}"

    def get_webhook_bots(self):
        """获取配置的所有webhook机器人"""
        bots = []
        if self.webhook_bots:
            for bot_type, bot_config in self.webhook_bots.items():
                bot_data = {
                    'type': bot_type,
                    'name': bot_config.get('name', f'{bot_type}机器人'),
                    'webhook_url': bot_config.get('webhook_url'),
                    'enabled': bot_config.get('enabled', True),
                    # 业务类型勾选框
                    'enable_ui_automation': bot_config.get('enable_ui_automation', True),
                    'enable_api_testing': bot_config.get('enable_api_testing', True)
                }
                # 钉钉机器人需要额外包含secret字段
                if bot_type == 'dingtalk' and bot_config.get('secret'):
                    bot_data['secret'] = bot_config.get('secret')
                bots.append(bot_data)
        return bots


class NotificationTemplate(models.Model):
    """通知模板 - 支持 Markdown/HTML/纯文本，变量替换"""
    TEMPLATE_TYPE_CHOICES = [
        ('markdown', 'Markdown'),
        ('html', 'HTML'),
        ('text', '纯文本'),
    ]

    name = models.CharField(max_length=100, verbose_name='模板名称')
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPE_CHOICES, default='markdown', verbose_name='模板类型')
    subject = models.CharField(max_length=200, blank=True, verbose_name='邮件主题',
                               help_text='邮件通知使用的主题，支持 {{变量}} 替换')
    description = models.TextField(blank=True, verbose_name='模板描述',
                                  help_text='对该模板用途的简要描述')
    content = models.TextField(verbose_name='模板内容',
                               help_text='支持 {{变量}} 替换。可用变量：{{task_name}}、{{status_text}}、{{execution_time}}、{{task_type}}、'
                                         '{{title}}、{{tester}}、{{total_cases}}、{{passed_cases}}、{{failed_cases}}、'
                                         '{{error_cases}}、{{skipped_cases}}、{{runtime}}、{{begin_time}}')
    variables = models.JSONField(default=list, blank=True, verbose_name='模板变量')
    is_default = models.BooleanField(default=False, verbose_name='是否默认模板')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'notification_templates'
        verbose_name = '通知模板'
        verbose_name_plural = '通知模板'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_template_type_display()})"

    def render(self, context):
        """渲染模板内容，替换 {{变量}} / {{ 变量 }}"""
        rendered = self.content
        for key, value in (context or {}).items():
            rendered = rendered.replace('{{' + key + '}}', str(value))
            rendered = rendered.replace('{{ ' + key + ' }}', str(value))
        return rendered

    def render_subject(self, context):
        """渲染邮件主题"""
        if not self.subject:
            return ''
        rendered = self.subject
        for key, value in (context or {}).items():
            rendered = rendered.replace('{{' + key + '}}', str(value))
            rendered = rendered.replace('{{ ' + key + ' }}', str(value))
        return rendered


class RequestPerformanceLog(models.Model):
    """请求性能日志"""
    path = models.CharField(max_length=500, verbose_name='请求路径')
    method = models.CharField(max_length=10, verbose_name='请求方法')
    response_time = models.FloatField(verbose_name='响应时间(ms)')
    status_code = models.IntegerField(verbose_name='状态码')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='用户')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP地址')
    user_agent = models.CharField(max_length=500, blank=True, verbose_name='User-Agent')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')

    class Meta:
        db_table = 'request_performance_logs'
        verbose_name = '请求性能日志'
        verbose_name_plural = '请求性能日志'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['path']),
            models.Index(fields=['status_code']),
            models.Index(fields=['-response_time']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.method} {self.path} - {self.response_time}ms"


class PerformanceStatistics(models.Model):
    """性能统计（按日聚合）"""
    date = models.DateField(unique=True, verbose_name='日期')
    total_requests = models.IntegerField(default=0, verbose_name='总请求数')
    avg_response_time = models.FloatField(default=0, verbose_name='平均响应时间(ms)')
    max_response_time = models.FloatField(default=0, verbose_name='最大响应时间(ms)')
    min_response_time = models.FloatField(default=0, verbose_name='最小响应时间(ms)')
    error_count = models.IntegerField(default=0, verbose_name='错误请求数')
    slow_requests = models.IntegerField(default=0, verbose_name='慢请求数(>1s)')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'performance_statistics'
        verbose_name = '性能统计'
        verbose_name_plural = '性能统计'
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} - {self.total_requests}请求"


class Skill(models.Model):
    """AI Skills 技能配置（SKILL.md + 附属文件）"""
    name = models.CharField(max_length=100, unique=True, verbose_name='技能名称',
                            help_text='唯一标识，如 api-testcase-generator')
    description = models.TextField(blank=True, verbose_name='技能描述')
    tags = models.JSONField(default=list, blank=True, verbose_name='标签')
    content = models.TextField(blank=True, verbose_name='SKILL.md 内容')
    files = models.JSONField(default=dict, blank=True, verbose_name='附属文件',
                             help_text='相对路径 -> 文件内容，如 references/guide.md')
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用')
    is_builtin = models.BooleanField(default=False, verbose_name='是否内置')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='创建者', related_name='created_skills'
    )

    class Meta:
        db_table = 'core_skills'
        verbose_name = 'Skill 技能'
        verbose_name_plural = 'Skill 技能'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_enabled']),
            models.Index(fields=['is_builtin']),
        ]

    def __str__(self):
        return self.name

    @property
    def file_folders(self):
        folders = set()
        for path in (self.files or {}).keys():
            parts = str(path).replace('\\', '/').split('/')
            if len(parts) > 1 and parts[0]:
                folders.add(parts[0])
        return sorted(folders)

    @property
    def file_count(self):
        # SKILL.md + 附属文件
        return 1 + len(self.files or {})


class MCPServer(models.Model):
    """MCP（Model Context Protocol）外部服务器配置"""

    TRANSPORT_CHOICES = [
        ('stdio', 'stdio'),
        ('sse', 'SSE'),
        ('http', 'HTTP'),
    ]
    STATUS_CHOICES = [
        ('unknown', '未知'),
        ('connected', '已连接'),
        ('disconnected', '未连接'),
        ('error', '错误'),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name='服务器名称')
    description = models.TextField(blank=True, verbose_name='描述')
    transport = models.CharField(max_length=20, choices=TRANSPORT_CHOICES, default='stdio', verbose_name='传输方式')
    command = models.CharField(max_length=255, blank=True, verbose_name='启动命令',
                               help_text='stdio 模式：可执行文件，如 npx / python')
    args = models.JSONField(default=list, blank=True, verbose_name='启动参数')
    env = models.JSONField(default=dict, blank=True, verbose_name='环境变量')
    url = models.URLField(blank=True, verbose_name='服务器 URL',
                          help_text='sse / http 模式使用')
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用')
    connection_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='unknown', verbose_name='连接状态'
    )
    tools = models.JSONField(default=list, blank=True, verbose_name='已发现工具')
    last_error = models.TextField(blank=True, verbose_name='最近错误')
    last_tested_at = models.DateTimeField(null=True, blank=True, verbose_name='最近测试时间')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name='创建者', related_name='created_mcp_servers'
    )

    class Meta:
        db_table = 'core_mcp_servers'
        verbose_name = 'MCP 服务器'
        verbose_name_plural = 'MCP 服务器'
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_enabled']),
            models.Index(fields=['connection_status']),
        ]

    def __str__(self):
        return self.name

    @property
    def tools_count(self):
        return len(self.tools or [])


class ModuleSwitch(models.Model):
    """功能模块开关 - 控制前端各功能模块（侧边栏菜单 / 首页入口）的启用与隐藏"""

    LOCATION_CHOICES = [
        ('all', '全局（菜单+首页）'),
        ('sidebar', '侧边栏菜单'),
        ('home', '首页入口'),
    ]

    key = models.CharField(max_length=50, unique=True, verbose_name='模块标识',
                           help_text='唯一标识，如 ai-generation / api-testing / data-factory')
    name = models.CharField(max_length=100, verbose_name='模块名称')
    description = models.CharField(max_length=255, blank=True, verbose_name='模块描述')
    location = models.CharField(max_length=20, choices=LOCATION_CHOICES, default='all',
                                verbose_name='显示位置')
    sort_order = models.IntegerField(default=0, verbose_name='排序')
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用')
    is_builtin = models.BooleanField(default=True, verbose_name='是否内置',
                                     help_text='内置模块不可删除，避免误删导致入口丢失')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'core_module_switches'
        verbose_name = '功能模块开关'
        verbose_name_plural = '功能模块开关'
        ordering = ['sort_order', 'id']
        indexes = [
            models.Index(fields=['is_enabled']),
            models.Index(fields=['location']),
        ]

    def __str__(self):
        return f"{self.name} ({self.key})"
