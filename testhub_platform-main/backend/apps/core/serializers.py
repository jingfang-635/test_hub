"""
Core 应用序列化器
"""
from rest_framework import serializers
from .models import (
    UnifiedNotificationConfig,
    NotificationTemplate,
    RequestPerformanceLog,
    PerformanceStatistics,
    Skill,
    MCPServer,
)


class UnifiedNotificationConfigSerializer(serializers.ModelSerializer):
    """统一通知配置序列化器"""

    webhook_bots_display = serializers.SerializerMethodField()

    class Meta:
        model = UnifiedNotificationConfig
        fields = [
            'id', 'name', 'config_type', 'webhook_bots',
            'is_default', 'is_active', 'created_at', 'updated_at',
            'created_by', 'webhook_bots_display'
        ]
        read_only_fields = ['created_at', 'updated_at', 'created_by', 'webhook_bots_display']

    def get_webhook_bots_display(self, obj):
        """获取webhook机器人显示信息"""
        bots = obj.get_webhook_bots()
        display_list = []
        for bot in bots:
            display_list.append({
                'type': bot.get('type'),
                'name': bot.get('name'),
                'enabled': bot.get('enabled'),
                'enable_ui_automation': bot.get('enable_ui_automation'),
                'enable_api_testing': bot.get('enable_api_testing')
            })
        return display_list


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """通知模板序列化器"""

    template_type_display = serializers.CharField(
        source='get_template_type_display', read_only=True
    )

    class Meta:
        model = NotificationTemplate
        fields = [
            'id', 'name', 'template_type', 'template_type_display',
            'subject', 'description', 'content', 'variables',
            'is_default', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at', 'template_type_display']

    def create(self, validated_data):
        if validated_data.get('is_default'):
            NotificationTemplate.objects.filter(is_default=True).update(is_default=False)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get('is_default'):
            NotificationTemplate.objects.filter(is_default=True).exclude(
                pk=instance.pk
            ).update(is_default=False)
        return super().update(instance, validated_data)


class RequestPerformanceLogSerializer(serializers.ModelSerializer):
    """请求性能日志序列化器（只读详情）"""

    user_display = serializers.SerializerMethodField()

    class Meta:
        model = RequestPerformanceLog
        fields = [
            'id', 'path', 'method', 'response_time', 'status_code',
            'user', 'user_display', 'ip_address', 'user_agent', 'created_at',
        ]
        read_only_fields = fields

    def get_user_display(self, obj):
        return str(obj.user) if obj.user else '-'


class PerformanceStatisticsSerializer(serializers.ModelSerializer):
    """性能统计序列化器（只读详情）"""

    error_rate = serializers.SerializerMethodField()
    slow_rate = serializers.SerializerMethodField()

    class Meta:
        model = PerformanceStatistics
        fields = [
            'id', 'date', 'total_requests', 'avg_response_time',
            'max_response_time', 'min_response_time', 'error_count',
            'slow_requests', 'error_rate', 'slow_rate',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_error_rate(self, obj):
        total = obj.total_requests or 0
        if total <= 0:
            return 0.0
        return round((obj.error_count or 0) * 100.0 / total, 2)

    def get_slow_rate(self, obj):
        total = obj.total_requests or 0
        if total <= 0:
            return 0.0
        return round((obj.slow_requests or 0) * 100.0 / total, 2)


class SkillSerializer(serializers.ModelSerializer):
    """Skill 技能序列化器"""
    file_count = serializers.IntegerField(read_only=True)
    file_folders = serializers.ListField(child=serializers.CharField(), read_only=True)

    class Meta:
        model = Skill
        fields = [
            'id', 'name', 'description', 'tags', 'content', 'files',
            'is_enabled', 'is_builtin', 'file_count', 'file_folders',
            'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = [
            'created_at', 'updated_at', 'created_by',
            'file_count', 'file_folders', 'is_builtin',
        ]

    def validate_name(self, value):
        name = (value or '').strip()
        if not name:
            raise serializers.ValidationError('技能名称不能为空')
        if ' ' in name:
            raise serializers.ValidationError('技能名称不能包含空格，建议使用 kebab-case')
        return name

    def validate_tags(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('标签必须是数组')
        return [str(t).strip() for t in value if str(t).strip()]

    def validate_files(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError('附属文件必须是对象')
        return value


class MCPServerSerializer(serializers.ModelSerializer):
    """MCP 服务器序列化器"""
    tools_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = MCPServer
        fields = [
            'id', 'name', 'description', 'transport', 'command', 'args', 'env', 'url',
            'is_enabled', 'connection_status', 'tools', 'tools_count', 'last_error',
            'last_tested_at', 'created_at', 'updated_at', 'created_by',
        ]
        read_only_fields = [
            'connection_status', 'tools', 'tools_count', 'last_error',
            'last_tested_at', 'created_at', 'updated_at', 'created_by',
        ]

    def validate_name(self, value):
        name = (value or '').strip()
        if not name:
            raise serializers.ValidationError('服务器名称不能为空')
        if ' ' in name:
            raise serializers.ValidationError('服务器名称不能包含空格')
        return name

    def validate_args(self, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError('启动参数必须是数组')
        return [str(v) for v in value]

    def validate_env(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError('环境变量必须是对象')
        return {str(k): str(v) for k, v in value.items()}

    def validate(self, attrs):
        transport = attrs.get('transport') or getattr(self.instance, 'transport', 'stdio')
        command = attrs.get('command') if 'command' in attrs else getattr(self.instance, 'command', '')
        url = attrs.get('url') if 'url' in attrs else getattr(self.instance, 'url', '')
        if transport == 'stdio' and not (command or '').strip():
            raise serializers.ValidationError({'command': 'stdio 模式必须填写启动命令'})
        if transport in ('sse', 'http') and not (url or '').strip():
            raise serializers.ValidationError({'url': 'sse/http 模式必须填写服务器 URL'})
        return attrs
