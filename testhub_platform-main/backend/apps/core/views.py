"""
Core 应用视图
"""
import logging

import yaml
from django.http import HttpResponse
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .mcp_client import discover_tools, get_preset, list_presets_public
from .models import (
    UnifiedNotificationConfig,
    NotificationTemplate,
    RequestPerformanceLog,
    PerformanceStatistics,
    Skill,
    MCPServer,
    ModuleSwitch,
)
from .serializers import (
    UnifiedNotificationConfigSerializer,
    NotificationTemplateSerializer,
    RequestPerformanceLogSerializer,
    PerformanceStatisticsSerializer,
    SkillSerializer,
    MCPServerSerializer,
    ModuleSwitchSerializer,
)
from .skill_parser import parse_skill_markdown

logger = logging.getLogger(__name__)


def _parse_bool(value, default=False):
    """将 'false' / 'true' / 0 / 1 / 布尔等安全解析为布尔值。

    Python 内置 bool('false') 会返回 True，故需显式处理字符串。
    """
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value != 0
    return str(value).strip().lower() in ('1', 'true', 'yes', 'on')


class UnifiedNotificationConfigViewSet(viewsets.ModelViewSet):
    """统一通知配置视图集"""
    queryset = UnifiedNotificationConfig.objects.all()
    serializer_class = UnifiedNotificationConfigSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['config_type', 'is_default', 'is_active']
    search_fields = ['name']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        """创建通知配置"""
        instance = serializer.save(created_by=self.request.user)
        logger.info(f"创建统一通知配置: {instance.name}")

    def perform_update(self, serializer):
        """更新通知配置"""
        instance = serializer.save()
        logger.info(f"更新统一通知配置: {instance.name}")

    def perform_destroy(self, instance):
        """删除通知配置"""
        logger.info(f"删除统一通知配置: {instance.name}")
        instance.delete()

    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """设置为默认配置"""
        config = self.get_object()
        # 取消其他默认配置
        UnifiedNotificationConfig.objects.filter(is_default=True).update(is_default=False)
        # 设置当前为默认
        config.is_default = True
        config.save()
        return Response({'message': '已设置为默认配置'})

    @action(detail=False, methods=['get'])
    def active_configs(self, request):
        """获取所有启用的配置"""
        configs = UnifiedNotificationConfig.objects.filter(is_active=True)
        serializer = self.get_serializer(configs, many=True)
        return Response(serializer.data)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """通知模板视图集"""
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['template_type', 'is_default', 'is_active']
    search_fields = ['name', 'subject', 'content']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def perform_create(self, serializer):
        instance = serializer.save()
        logger.info(f"创建通知模板: {instance.name}")

    def perform_update(self, serializer):
        instance = serializer.save()
        logger.info(f"更新通知模板: {instance.name}")

    def perform_destroy(self, instance):
        logger.info(f"删除通知模板: {instance.name}")
        instance.delete()


class RequestPerformanceLogViewSet(viewsets.ReadOnlyModelViewSet):
    """请求性能日志视图集（只读，用于详情弹窗）"""
    queryset = RequestPerformanceLog.objects.select_related('user').all()
    serializer_class = RequestPerformanceLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['method', 'status_code']
    search_fields = ['path', 'user_agent', 'ip_address']
    ordering_fields = ['created_at', 'response_time']
    ordering = ['-created_at']


class PerformanceStatisticsViewSet(viewsets.ReadOnlyModelViewSet):
    """性能统计视图集（只读，用于详情弹窗）"""
    queryset = PerformanceStatistics.objects.all()
    serializer_class = PerformanceStatisticsSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['date']
    ordering_fields = ['date', 'total_requests']
    ordering = ['-date']


class SkillViewSet(viewsets.ModelViewSet):
    """Skills 技能配置视图集"""
    queryset = Skill.objects.all()
    serializer_class = SkillSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_enabled', 'is_builtin']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, is_builtin=False)

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """启用 / 禁用 Skill"""
        skill = self.get_object()
        if 'is_enabled' in request.data:
            skill.is_enabled = bool(request.data.get('is_enabled'))
        else:
            skill.is_enabled = not skill.is_enabled
        skill.save(update_fields=['is_enabled', 'updated_at'])
        return Response(self.get_serializer(skill).data)

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """导出 Skill 为 Markdown（SKILL.md）"""
        skill = self.get_object()
        # 若正文已含 frontmatter 则直接导出；否则补齐标准 frontmatter
        content = (skill.content or '').strip()
        if not content.startswith('---'):
            meta = {
                'name': skill.name,
                'description': skill.description or '',
            }
            if skill.tags:
                meta['tags'] = skill.tags
            front = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
            content = f"---\n{front}\n---\n\n{content}".rstrip() + '\n'

        response = HttpResponse(content, content_type='text/markdown; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="{skill.name}.md"'
        return response

    @action(detail=False, methods=['post'], url_path='import_md')
    def import_md(self, request):
        """从 Markdown（SKILL.md）导入 Skill，自动解析 YAML frontmatter"""
        upload = request.FILES.get('file')
        if not upload:
            return Response({'detail': '请上传 Markdown 文件'}, status=status.HTTP_400_BAD_REQUEST)

        filename = upload.name or ''
        lower = filename.lower()
        if not (lower.endswith('.md') or lower.endswith('.markdown') or lower.endswith('.txt')):
            return Response({'detail': '仅支持 .md / .markdown 文件'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            raw_bytes = upload.read()
            try:
                text = raw_bytes.decode('utf-8')
            except UnicodeDecodeError:
                text = raw_bytes.decode('utf-8', errors='ignore')

            parsed = parse_skill_markdown(text, filename=filename)
            skill, created = Skill.objects.update_or_create(
                name=parsed['name'],
                defaults={
                    'description': parsed['description'],
                    'tags': parsed['tags'],
                    'content': parsed['content'],
                    'files': {},
                    'is_enabled': True,
                    'is_builtin': False,
                    'created_by': request.user,
                },
            )
            serializer = self.get_serializer(skill)
            return Response(
                {'created': created, 'skill': serializer.data},
                status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
            )
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception('导入 Skill 失败')
            return Response({'detail': f'导入失败: {exc}'}, status=status.HTTP_400_BAD_REQUEST)


class MCPServerViewSet(viewsets.ModelViewSet):
    """MCP 服务器配置视图集"""
    queryset = MCPServer.objects.all()
    serializer_class = MCPServerSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_enabled', 'transport', 'connection_status']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['name']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def _apply_tools_result(self, server: MCPServer, tools: list[str]):
        server.tools = tools
        server.connection_status = 'connected'
        server.last_error = ''
        server.last_tested_at = timezone.now()
        server.save(update_fields=[
            'tools', 'connection_status', 'last_error', 'last_tested_at', 'updated_at'
        ])

    def _apply_error(self, server: MCPServer, message: str):
        server.connection_status = 'error'
        server.last_error = (message or '')[:2000]
        server.last_tested_at = timezone.now()
        server.save(update_fields=[
            'connection_status', 'last_error', 'last_tested_at', 'updated_at'
        ])

    @action(detail=False, methods=['get'])
    def status_summary(self, request):
        qs = self.get_queryset()
        total = qs.count()
        connected = qs.filter(connection_status='connected', is_enabled=True).count()
        tools = 0
        for server in qs.filter(is_enabled=True, connection_status='connected'):
            tools += len(server.tools or [])
        return Response({
            'total': total,
            'connected': connected,
            'tools': tools,
        })

    @action(detail=False, methods=['get'])
    def presets(self, request):
        return Response(list_presets_public())

    @action(detail=False, methods=['post'], url_path='add_preset')
    def add_preset(self, request):
        key = (request.data.get('key') or '').strip()
        preset = get_preset(key)
        if not preset:
            return Response({'detail': f'未知预设: {key}'}, status=status.HTTP_400_BAD_REQUEST)
        if MCPServer.objects.filter(name=preset['name']).exists():
            return Response({'detail': f'服务器「{preset["name"]}」已存在'}, status=status.HTTP_400_BAD_REQUEST)

        server = MCPServer.objects.create(
            name=preset['name'],
            description=preset['description'],
            transport=preset['transport'],
            command=preset.get('command') or '',
            args=preset.get('args') or [],
            env=preset.get('env') or {},
            url=preset.get('url') or '',
            is_enabled=True,
            created_by=request.user,
        )
        # 一键添加后尝试连接；失败则用预设工具列表
        try:
            tools = discover_tools(server, allow_preset_fallback=True)
            self._apply_tools_result(server, tools)
        except Exception as exc:
            self._apply_error(server, str(exc))

        return Response(self.get_serializer(server).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        server = self.get_object()
        if 'is_enabled' in request.data:
            server.is_enabled = bool(request.data.get('is_enabled'))
        else:
            server.is_enabled = not server.is_enabled
        if not server.is_enabled and server.connection_status == 'connected':
            server.connection_status = 'disconnected'
            server.save(update_fields=['is_enabled', 'connection_status', 'updated_at'])
        else:
            server.save(update_fields=['is_enabled', 'updated_at'])
        return Response(self.get_serializer(server).data)

    @action(detail=True, methods=['post'], url_path='test_connection')
    def test_connection(self, request, pk=None):
        server = self.get_object()
        try:
            tools = discover_tools(server, allow_preset_fallback=True)
            self._apply_tools_result(server, tools)
            return Response({
                'success': True,
                'tools_count': len(tools),
                'tools': tools,
                'server': self.get_serializer(server).data,
                'message': f'连接测试成功，发现 {len(tools)} 个工具',
            })
        except Exception as exc:
            self._apply_error(server, str(exc))
            return Response({
                'success': False,
                'detail': str(exc),
                'server': self.get_serializer(server).data,
            }, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path='reconnect_all')
    def reconnect_all(self, request):
        results = []
        for server in self.get_queryset().filter(is_enabled=True):
            try:
                tools = discover_tools(server, allow_preset_fallback=True)
                self._apply_tools_result(server, tools)
                results.append({
                    'id': server.id,
                    'name': server.name,
                    'success': True,
                    'tools_count': len(tools),
                })
            except Exception as exc:
                self._apply_error(server, str(exc))
                results.append({
                    'id': server.id,
                    'name': server.name,
                    'success': False,
                    'detail': str(exc),
                })
        connected = sum(1 for r in results if r['success'])
        tools = sum(r.get('tools_count', 0) for r in results if r['success'])
        return Response({
            'results': results,
            'connected': connected,
            'total': len(results),
            'tools': tools,
        })


class ModuleSwitchViewSet(viewsets.ModelViewSet):
    """功能模块开关视图集 - 控制前端各功能模块（侧边栏菜单 / 首页入口）的启用与隐藏"""
    queryset = ModuleSwitch.objects.all()
    serializer_class = ModuleSwitchSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None  # 菜单开关是小型配置列表，关闭分页避免漏读新建记录
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['location', 'is_enabled', 'is_builtin']
    search_fields = ['key', 'name', 'description']
    ordering_fields = ['sort_order', 'name', 'created_at', 'updated_at']
    ordering = ['sort_order', 'id']

    def perform_create(self, serializer):
        # 新增模块默认非内置，可由用户自行删除
        serializer.save(is_builtin=False)

    def perform_destroy(self, instance):
        if instance.is_builtin:
            # 内置模块禁止删除，避免误删导致前端入口丢失
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('内置模块不可删除，请通过「是否启用」控制其显示')
        instance.delete()

    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """启用 / 禁用模块"""
        switch = self.get_object()
        if 'is_enabled' in request.data:
            switch.is_enabled = _parse_bool(request.data.get('is_enabled'), default=switch.is_enabled)
        else:
            switch.is_enabled = not switch.is_enabled
        switch.save(update_fields=['is_enabled', 'updated_at'])
        return Response(self.get_serializer(switch).data)

    @action(detail=False, methods=['get'])
    def enabled(self, request):
        """返回已启用 / 已禁用开关的 key 列表（供前端侧边栏 / 首页过滤）

        采用「默认启用 + 显式禁用」模型：未出现在 disabled 中的 key 视为启用。
        """
        enabled = list(
            ModuleSwitch.objects.filter(is_enabled=True)
            .values_list('key', flat=True)
        )
        disabled = list(
            ModuleSwitch.objects.filter(is_enabled=False)
            .values_list('key', flat=True)
        )
        return Response({'enabled': enabled, 'disabled': disabled})

    @action(detail=False, methods=['post'], url_path='toggle_by_key')
    def toggle_by_key(self, request):
        """按 key 切换开关状态（不存在则自动创建）。

        用于配置页中尚未落库的菜单项（如新增路由），避免必须先创建再来切换。
        """
        key = (request.data.get('key') or '').strip()
        if not key:
            return Response({'detail': 'key 不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        is_enabled = _parse_bool(request.data.get('is_enabled'), default=True)
        name = (request.data.get('name') or '').strip() or key
        location = request.data.get('location') or 'sidebar'
        switch, created = ModuleSwitch.objects.update_or_create(
            key=key,
            defaults={
                'name': name,
                'description': request.data.get('description') or '',
                'location': location,
                'sort_order': request.data.get('sort_order') or 0,
                'is_enabled': is_enabled,
                'is_builtin': True,
            },
        )
        return Response(
            self.get_serializer(switch).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )
