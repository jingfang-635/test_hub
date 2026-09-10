from rest_framework import viewsets, status, views
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, FileResponse
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models
from django.utils import timezone
from pathlib import Path
from urllib.parse import quote
import logging
import json
import os
import re
import random
import time
import shutil
import subprocess
import glob
import uuid

from .models import (
    UiProject, LocatorStrategy, Element, TestScript, TestSuite,
    TestSuiteScript, TestExecution, Screenshot,
    ElementGroup, PageObject, PageObjectElement, ScriptStep, ScriptElementUsage,
    TestCase, TestCaseStep, TestCaseExecution, OperationRecord,
    TestCase, TestCaseStep, TestCaseExecution, OperationRecord,
    UiScheduledTask, UiNotificationLog, UiTaskNotificationSetting,
    AICase, AIExecutionRecord
)
from .serializers import (
    UiProjectSerializer, UiProjectCreateSerializer, UiProjectUpdateSerializer,
    LocatorStrategySerializer,
    ElementSerializer, ElementEnhancedSerializer,
    TestScriptSerializer, TestScriptCreateSerializer, TestScriptUpdateSerializer,
    TestSuiteSerializer, TestSuiteCreateSerializer, TestSuiteUpdateSerializer, TestSuiteWithScriptsSerializer,
    TestSuiteScriptSerializer, TestSuiteTestCaseSerializer,
    TestExecutionSerializer, TestExecutionCreateSerializer,
    ScreenshotSerializer,
    ElementGroupSerializer, ElementGroupCreateSerializer,
    PageObjectSerializer, PageObjectCreateSerializer, PageObjectElementSerializer,
    ScriptStepSerializer, ScriptElementUsageSerializer,
    ScriptAnalysisSerializer, ElementValidationSerializer, CodeGenerationSerializer,
    TestCaseSerializer, TestCaseStepSerializer, TestCaseExecutionSerializer, TestCaseRunSerializer,
    OperationRecordSerializer,
    UiScheduledTaskSerializer, UiNotificationLogSerializer, UiTaskNotificationSettingSerializer,
    AICaseSerializer, AIExecutionRecordSerializer
)
from .operation_logger import log_operation

logger = logging.getLogger(__name__)
User = get_user_model()


def extract_step_info(s, step_index):
    """提取步骤信息的辅助函数，确保返回可读的步骤描述"""
    step_info = {'step': step_index}

    # 尝试多种方式提取可读信息
    if hasattr(s, 'action'):
        # 如果有action属性
        action_data = s.action
        if isinstance(action_data, str):
            step_info['action'] = action_data
        elif hasattr(action_data, '__dict__'):
            # 如果是对象，提取关键属性
            attrs = {}
            for key in ['type', 'description', 'goal', 'coordinate', 'text', 'output', 'result']:
                if hasattr(action_data, key):
                    value = getattr(action_data, key)
                    if isinstance(value, str):
                        attrs[key] = value
                    elif callable(value):
                        attrs[key] = getattr(value, '__name__', str(value))
                    else:
                        attrs[key] = str(value)
            if attrs:
                step_info['action'] = attrs
        else:
            step_info['action'] = str(action_data)
    elif hasattr(s, 'model_output'):
        # 如果有model_output属性
        output_data = s.model_output
        if isinstance(output_data, str):
            step_info['action'] = output_data
        elif hasattr(output_data, '__dict__'):
            # 提取model_output的关键信息
            attrs = {'type': 'model_output'}
            for key in ['action', 'description', 'goal', 'coordinate', 'text']:
                if hasattr(output_data, key):
                    value = getattr(output_data, key)
                    attrs[key] = str(value) if value else None
            step_info['action'] = attrs
        else:
            step_info['action'] = str(output_data)
    elif hasattr(s, '__dict__'):
        # 通用的对象提取
        attrs = {}
        for key in dir(s):
            if not key.startswith('_'):
                try:
                    value = getattr(s, key)
                    if not callable(value):
                        attrs[key] = str(value)
                except:
                    pass
        if attrs:
            step_info['action'] = attrs
    else:
        # 最后回退，但检查是否是函数对象
        if callable(s):
            step_info['action'] = f"<Action: {getattr(s, '__name__', 'unknown action')}>"
        else:
            step_info['action'] = str(s)

    return step_info


from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000


def ensure_ui_project_for_hub(user, hub_project_id):
    """按「项目与版本」主项目 get-or-create 对应的 UiProject。"""
    from apps.projects.models import Project

    if not hub_project_id:
        return None, Response({'error': '请提供 hub_project_id'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        hub_project = Project.objects.get(id=hub_project_id)
    except Project.DoesNotExist:
        return None, Response({'error': '主项目不存在'}, status=status.HTTP_404_NOT_FOUND)

    if hub_project.owner_id != user.id and not hub_project.members.filter(id=user.id).exists():
        return None, Response({'error': '无权限访问该项目'}, status=status.HTTP_403_FORBIDDEN)

    if 'ui_automation' not in (hub_project.project_types or []):
        return None, Response(
            {'error': '该项目未关联 UI自动化 模块'},
            status=status.HTTP_400_BAD_REQUEST
        )

    ui_project = UiProject.objects.filter(hub_project=hub_project).first()
    created = False
    if not ui_project:
        # 兼容历史数据：同名未关联的 UiProject 优先绑定
        ui_project = UiProject.objects.filter(
            hub_project__isnull=True,
            name=hub_project.name,
        ).filter(
            models.Q(owner=user) | models.Q(members=user)
        ).first()
        if ui_project:
            ui_project.hub_project = hub_project
            ui_project.description = ui_project.description or (hub_project.description or '')
            ui_project.save(update_fields=['hub_project', 'description', 'updated_at'])
        else:
            status_map = {
                'active': 'IN_PROGRESS',
                'paused': 'NOT_STARTED',
                'completed': 'COMPLETED',
                'archived': 'COMPLETED',
            }
            ui_project = UiProject.objects.create(
                name=hub_project.name,
                description=hub_project.description or '',
                status=status_map.get(hub_project.status, 'IN_PROGRESS'),
                owner=hub_project.owner,
                hub_project=hub_project,
            )
            member_ids = list(hub_project.members.values_list('id', flat=True))
            if member_ids:
                ui_project.members.set(member_ids)
            created = True
    else:
        # 主项目改名后同步到 UiProject，避免脚本列表等仍显示旧名称
        sync_fields = []
        if ui_project.name != hub_project.name:
            ui_project.name = hub_project.name
            sync_fields.append('name')
        if sync_fields:
            sync_fields.append('updated_at')
            ui_project.save(update_fields=sync_fields)

    return (ui_project, created), None


class UiProjectEnsureView(views.APIView):
    """独立 ensure 接口，避免被 ViewSet detail 路由抢占导致 POST 405。"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        hub_project_id = request.data.get('hub_project_id')
        result, error_response = ensure_ui_project_for_hub(request.user, hub_project_id)
        if error_response:
            return error_response
        ui_project, created = result
        return Response(
            UiProjectSerializer(ui_project).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class UiProjectViewSet(viewsets.ModelViewSet):
    queryset = UiProject.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'owner', 'members']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return UiProjectCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UiProjectUpdateSerializer
        return UiProjectSerializer

    def get_queryset(self):
        # 只显示用户有权限访问的项目
        user = self.request.user
        return UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).select_related('hub_project').distinct()

    def perform_create(self, serializer):
        # 创建项目时，当前用户自动成为负责人
        instance = serializer.save(owner=self.request.user)
        # 记录操作
        log_operation('create', 'project', instance.id, instance.name, self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        # 记录操作
        log_operation('edit', 'project', instance.id, instance.name, self.request.user)

    def perform_destroy(self, instance):
        # 记录操作（在删除前记录）
        log_operation('delete', 'project', instance.id, instance.name, self.request.user)
        instance.delete()

    @action(detail=False, methods=['post'], url_path='ensure')
    def ensure_for_hub_project(self, request):
        """按「项目与版本」主项目 get-or-create 对应的 UiProject。"""
        hub_project_id = request.data.get('hub_project_id')
        result, error_response = ensure_ui_project_for_hub(request.user, hub_project_id)
        if error_response:
            return error_response
        ui_project, created = result
        return Response(
            UiProjectSerializer(ui_project).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class LocatorStrategyViewSet(viewsets.ModelViewSet):
    queryset = LocatorStrategy.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = LocatorStrategySerializer
    ordering = ['id']


class ElementViewSet(viewsets.ModelViewSet):
    queryset = Element.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['project', 'locator_strategy', 'element_type', 'validation_status', 'group']
    search_fields = ['name', 'description', 'page', 'component_name']

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return ElementEnhancedSerializer
        return ElementSerializer

    def get_queryset(self):
        # 只显示用户有权限访问的项目的元素
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return Element.objects.filter(project__in=accessible_projects).select_related(
            'project', 'group', 'locator_strategy', 'created_by', 'parent_element'
        ).prefetch_related('script_usages__script').order_by('page', 'name')

    def filter_queryset(self, queryset):
        # 先应用默认的过滤器
        queryset = super().filter_queryset(queryset)

        # 处理页面筛选（使用page_name参数避免与分页page冲突）
        page_name = self.request.query_params.get('page_name', None)
        if page_name:
            queryset = queryset.filter(page=page_name)

        return queryset

    def perform_create(self, serializer):
        # 创建元素时自动设置创建人
        instance = serializer.save(created_by=self.request.user)
        # 记录操作
        log_operation('create', 'element', instance.id, instance.name, self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        # 记录操作
        log_operation('edit', 'element', instance.id, instance.name, self.request.user)

    def perform_destroy(self, instance):
        # 记录操作（在删除前记录）
        log_operation('delete', 'element', instance.id, instance.name, self.request.user)
        instance.delete()

    @action(detail=True, methods=['post'])
    def validate_locator(self, request, pk=None):
        """验证元素定位器有效性"""
        element = self.get_object()

        # 这里可以集成实际的浏览器验证逻辑
        # 现在只是模拟验证
        validation_result = self._perform_element_validation(element)

        element.validation_status = 'VALID' if validation_result['is_valid'] else 'INVALID'
        element.validation_message = validation_result['validation_message']
        element.last_validated = timezone.now()
        element.save()

        serializer = ElementValidationSerializer(validation_result)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def usages(self, request, pk=None):
        """获取元素在脚本中的使用情况"""
        element = self.get_object()
        usages = ScriptElementUsage.objects.filter(element=element).select_related('script')
        serializer = ScriptElementUsageSerializer(usages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """获取元素树形结构；未传 project 或 project=all 时返回全部可访问项目。"""
        project_id = request.query_params.get('project')
        elements = self.get_queryset()
        if project_id and str(project_id) not in ('', 'all', 'null', 'undefined'):
            elements = elements.filter(project_id=project_id)
        tree_data = self._build_element_tree(elements)
        return Response(tree_data)

    @action(detail=True, methods=['post'])
    def add_backup_locator(self, request, pk=None):
        """添加备用定位器"""
        element = self.get_object()
        strategy = request.data.get('strategy')
        value = request.data.get('value')

        if not strategy or not value:
            return Response({'error': '策略和值都是必需的'}, status=status.HTTP_400_BAD_REQUEST)

        backup_locators = list(element.backup_locators or [])
        # 策略可重复；同一策略下同一表达式不可重复
        if any(
            (b.get('strategy') or '').lower() == strategy.lower()
            and (b.get('value') or '') == value
            for b in backup_locators
        ):
            return Response({'message': '备用定位器已存在'})
        backup_locators.append({'strategy': strategy, 'value': value})
        element.backup_locators = backup_locators
        element.save()

        return Response({'message': '备用定位器添加成功'})

    @action(detail=True, methods=['post'])
    def generate_suggestions(self, request, pk=None):
        """生成元素使用建议"""
        element = self.get_object()
        suggestions = self._generate_element_suggestions(element)
        return Response({'suggestions': suggestions})

    def _perform_element_validation(self, element):
        """执行元素验证（模拟实现）"""
        try:
            # 这里可以集成实际的浏览器自动化工具进行验证
            # 现在只是简单的语法检查
            is_valid = True
            message = "定位器验证通过"
            suggestions = []

            # 简单的语法检查
            if element.locator_strategy.name == 'css':
                if not element.locator_value.strip():
                    is_valid = False
                    message = "CSS选择器不能为空"
            elif element.locator_strategy.name == 'xpath':
                if not element.locator_value.strip():
                    is_valid = False
                    message = "XPath表达式不能为空"

            return {
                'is_valid': is_valid,
                'validation_message': message,
                'suggestions': suggestions
            }
        except Exception as e:
            return {
                'is_valid': False,
                'validation_message': f'验证过程中出现错误: {str(e)}',
                'suggestions': []
            }

    def _build_element_tree(self, elements):
        """构建元素树形结构 - 返回元素列表而不是页面分组，因为前端会自己处理页面关联"""
        element_data_list = []
        for element in elements:
            element_data = {
                'id': element.id,
                'name': element.name,
                'type': 'element',
                'element_type': element.element_type,
                'locator_strategy': element.locator_strategy.name if element.locator_strategy else None,
                'locator_value': element.locator_value,
                'validation_status': element.validation_status,
                'usage_count': element.usage_count,
                'group_id': element.group_id,  # 用于前端关联到页面
                'page': element.page,  # 保留向后兼容
                'project_id': element.project_id,
                'children': []
            }
            element_data_list.append(element_data)

        return element_data_list

    def _generate_element_suggestions(self, element):
        """生成元素使用建议"""
        suggestions = []

        # 基于元素类型生成建议
        if element.element_type == 'INPUT':
            suggestions.append("建议为输入框元素添加清空和输入验证操作")
        elif element.element_type == 'BUTTON':
            suggestions.append("建议验证按钮点击后的页面跳转或状态变化")
        elif element.element_type == 'DROPDOWN':
            suggestions.append("建议测试下拉框的所有选项")

        # 基于使用频率生成建议
        if element.usage_count == 0:
            suggestions.append("此元素尚未在任何脚本中使用，考虑是否需要删除")
        elif element.usage_count > 10:
            suggestions.append("此元素使用频率较高，建议添加到页面对象中以提高复用性")

        return suggestions


class ElementGroupViewSet(viewsets.ModelViewSet):
    queryset = ElementGroup.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['project', 'parent_group']
    search_fields = ['name', 'description']

    def get_serializer_class(self):
        if self.action == 'create':
            return ElementGroupCreateSerializer
        return ElementGroupSerializer

    def get_queryset(self):
        # 只显示用户有权限访问的项目的元素分组
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return ElementGroup.objects.filter(project__in=accessible_projects).select_related('project',
                                                                                           'parent_group').order_by(
            'order', 'name')

    def perform_update(self, serializer):
        """分组改名时同步元素 page 字段与用例步骤 page_filter，保证用例详情页面下拉一致。"""
        old_name = serializer.instance.name
        project_id = serializer.instance.project_id
        group_id = serializer.instance.id
        instance = serializer.save()
        new_name = instance.name
        if not old_name or old_name == new_name:
            return

        # 本分组下的元素
        Element.objects.filter(group_id=instance.id).update(page=new_name)
        # 同项目下仍使用旧页面名的元素（兼容仅写了 page、未绑 group 的数据）
        Element.objects.filter(project_id=project_id, page=old_name).update(page=new_name)

        # 1) 步骤 page_filter 仍为旧分组名
        TestCaseStep.objects.filter(
            test_case__project_id=project_id,
            page_filter=old_name,
        ).update(page_filter=new_name)

        # 2) 引用了本分组元素的步骤（即使 page_filter 与旧名不一致也强制跟随）
        element_ids = list(
            Element.objects.filter(group_id=group_id).values_list('id', flat=True)
        )
        if element_ids:
            TestCaseStep.objects.filter(element_id__in=element_ids).update(page_filter=new_name)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """获取分组树形结构；未传 project 或 project=all 时返回全部可访问项目。"""
        project_id = request.query_params.get('project')
        groups = self.get_queryset().filter(parent_group__isnull=True)
        if project_id and str(project_id) not in ('', 'all', 'null', 'undefined'):
            groups = groups.filter(project_id=project_id)
        serializer = ElementGroupSerializer(groups, many=True)
        return Response(serializer.data)


class PageObjectViewSet(viewsets.ModelViewSet):
    queryset = PageObject.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['project']
    search_fields = ['name', 'class_name', 'description']

    def get_serializer_class(self):
        if self.action == 'create':
            return PageObjectCreateSerializer
        return PageObjectSerializer

    def get_queryset(self):
        # 只显示用户有权限访问的项目的页面对象
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return PageObject.objects.filter(project__in=accessible_projects).select_related(
            'project', 'created_by'
        ).prefetch_related('page_object_elements__element').order_by('-created_at')

    @action(detail=True, methods=['post'])
    def generate_code(self, request, pk=None):
        """生成页面对象代码"""
        page_object = self.get_object()
        serializer = CodeGenerationSerializer(data=request.data)

        if serializer.is_valid():
            language = serializer.validated_data['language']
            framework = serializer.validated_data['framework']
            include_comments = serializer.validated_data['include_comments']

            try:
                generated_code = page_object.generate_code(language)

                # 保存生成的代码模板
                page_object.template_code = generated_code
                page_object.save()

                return Response({
                    'code': generated_code,
                    'language': language,
                    'framework': framework
                })
            except Exception as e:
                return Response({
                    'error': f'代码生成失败: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def add_element(self, request, pk=None):
        """向页面对象添加元素"""
        page_object = self.get_object()
        serializer = PageObjectElementSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(page_object=page_object)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def elements(self, request, pk=None):
        """获取页面对象的所有元素"""
        page_object = self.get_object()
        po_elements = page_object.page_object_elements.select_related('element').all()
        serializer = PageObjectElementSerializer(po_elements, many=True)
        return Response(serializer.data)


class PageObjectElementViewSet(viewsets.ModelViewSet):
    queryset = PageObjectElement.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = PageObjectElementSerializer

    def get_queryset(self):
        # 只显示用户有权限访问的页面对象元素
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return PageObjectElement.objects.filter(
            page_object__project__in=accessible_projects
        ).select_related('page_object', 'element').order_by('id')


class ScriptStepViewSet(viewsets.ModelViewSet):
    queryset = ScriptStep.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ScriptStepSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['script', 'action_type', 'target_element', 'page_object']

    def get_queryset(self):
        # 只显示用户有权限访问的脚本步骤
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return ScriptStep.objects.filter(
            script__project__in=accessible_projects
        ).select_related('script', 'target_element', 'page_object').order_by('step_order')

    @action(detail=False, methods=['post'])
    def batch_create(self, request):
        """批量创建脚本步骤"""
        steps_data = request.data.get('steps', [])
        created_steps = []

        for step_data in steps_data:
            serializer = ScriptStepSerializer(data=step_data)
            if serializer.is_valid():
                step = serializer.save()
                created_steps.append(step)
            else:
                return Response({
                    'error': f'步骤创建失败: {serializer.errors}'
                }, status=status.HTTP_400_BAD_REQUEST)

        response_serializer = ScriptStepSerializer(created_steps, many=True)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ScriptElementUsageViewSet(viewsets.ModelViewSet):
    queryset = ScriptElementUsage.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ScriptElementUsageSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['script', 'element', 'usage_type']

    def get_queryset(self):
        # 只显示用户有权限访问的脚本元素使用记录
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return ScriptElementUsage.objects.filter(
            script__project__in=accessible_projects
        ).select_related('script', 'element').order_by('script', 'line_number')

    @action(detail=False, methods=['post'])
    def analyze_script(self, request):
        """分析脚本中的元素使用情况"""
        script_id = request.data.get('script_id')
        if not script_id:
            return Response({'error': '需要指定脚本ID'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            script = TestScript.objects.get(id=script_id)
            analysis_result = self._analyze_script_elements(script)

            serializer = ScriptAnalysisSerializer(analysis_result)
            return Response(serializer.data)
        except TestScript.DoesNotExist:
            return Response({'error': '脚本不存在'}, status=status.HTTP_404_NOT_FOUND)

    def _analyze_script_elements(self, script):
        """分析脚本中的元素使用"""
        # 解析脚本内容，查找元素使用情况
        content = script.content
        usages = []
        missing_elements = []
        recommendations = []

        # 简单的元素使用分析（实际实现会更复杂）
        if script.script_type == 'CODE':
            # 分析代码中的定位器使用
            locator_patterns = [
                r'locator\(["\']([^"\']+)["\']\)',
                r'findElement\(["\']([^"\']+)["\']\)',
                r'css\(["\']([^"\']+)["\']\)',
                r'xpath\(["\']([^"\']+)["\']\)'
            ]

            for pattern in locator_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                for match in matches:
                    # 查找对应的元素
                    try:
                        element = Element.objects.get(
                            project=script.project,
                            locator_value=match
                        )
                        usage, created = ScriptElementUsage.objects.get_or_create(
                            script=script,
                            element=element,
                            defaults={
                                'usage_type': 'CLICK',  # 默认类型
                                'line_number': 1,  # 需要实际解析
                                'frequency': 1
                            }
                        )
                        if not created:
                            usage.frequency += 1
                            usage.save()

                        element.increment_usage_count()
                        usages.append(usage)
                    except Element.DoesNotExist:
                        missing_elements.append(match)

        # 生成建议
        if missing_elements:
            recommendations.append(f"发现 {len(missing_elements)} 个未定义的元素定位器")

        if len(usages) > 20:
            recommendations.append("脚本复杂度较高，建议拆分为多个小脚本")

        complexity_score = min(100, len(usages) * 5)

        return {
            'element_usages': usages,
            'missing_elements': missing_elements,
            'recommendations': recommendations,
            'complexity_score': complexity_score
        }


class TestScriptViewSet(viewsets.ModelViewSet):
    queryset = TestScript.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['project', 'script_type']
    search_fields = ['name', 'description']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return TestScriptCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TestScriptUpdateSerializer
        return TestScriptSerializer

    def get_queryset(self):
        # 只显示用户有权限访问的项目的测试脚本
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return TestScript.objects.filter(project__in=accessible_projects).select_related(
            'project', 'project__hub_project'
        )

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """直接运行脚本（后台执行，写入 TestExecution）"""
        script = self.get_object()
        content = (script.content or '').strip()
        if not content:
            return Response({'error': '脚本内容为空，无法执行'}, status=status.HTTP_400_BAD_REQUEST)

        browser = request.data.get('browser', 'chrome')
        headless = request.data.get('headless', False)
        if isinstance(headless, str):
            headless = headless.lower() in ('1', 'true', 'yes', 'on')

        log_operation('run', 'script', script.id, script.name, request.user)

        import threading
        from .script_runner import ScriptRunner

        runner = ScriptRunner(
            script=script,
            browser=browser,
            headless=headless,
            executed_by=request.user,
        )
        execution = runner.create_execution_record()
        execution_id = execution.id

        def run_in_background():
            try:
                bg_runner = ScriptRunner(
                    script=TestScript.objects.select_related('project').get(pk=script.id),
                    browser=browser,
                    headless=headless,
                    executed_by=request.user,
                )
                bg_runner.execution = TestExecution.objects.get(pk=execution_id)
                bg_runner.run()
            except Exception:
                logger.exception('脚本后台线程异常: script_id=%s execution_id=%s', script.id, execution_id)

        thread = threading.Thread(target=run_in_background, daemon=False)
        thread.start()

        return Response({
            'message': '脚本开始执行',
            'script_id': script.id,
            'script_name': script.name,
            'execution_id': execution_id,
            'browser': browser,
            'headless': headless,
        }, status=status.HTTP_200_OK)


class TestSuiteViewSet(viewsets.ModelViewSet):
    queryset = TestSuite.objects.all()
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['project']
    search_fields = ['name', 'description']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return TestSuiteCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return TestSuiteUpdateSerializer
        elif self.action == 'retrieve':
            return TestSuiteWithScriptsSerializer
        return TestSuiteSerializer

    def get_queryset(self):
        # 只显示用户有权限访问的项目的测试套件
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return TestSuite.objects.filter(project__in=accessible_projects)

    def perform_create(self, serializer):
        instance = serializer.save()
        # 记录操作
        log_operation('create', 'suite', instance.id, instance.name, self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()
        # 记录操作
        log_operation('edit', 'suite', instance.id, instance.name, self.request.user)

    def perform_destroy(self, instance):
        # 记录操作（在删除前记录）
        log_operation('delete', 'suite', instance.id, instance.name, self.request.user)
        instance.delete()

    @action(detail=True, methods=['get'])
    def scripts(self, request, pk=None):
        """获取测试套件中的所有脚本"""
        test_suite = self.get_object()
        scripts = test_suite.suite_scripts.all()
        serializer = TestSuiteScriptSerializer(scripts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_script(self, request, pk=None):
        """向测试套件添加脚本"""
        test_suite = self.get_object()
        data = request.data
        data['test_suite'] = pk
        serializer = TestSuiteScriptSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def remove_script(self, request, pk=None, script_id=None):
        """从测试套件移除脚本"""
        test_suite = self.get_object()
        try:
            suite_script = TestSuiteScript.objects.get(test_suite=test_suite, id=script_id)
            suite_script.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TestSuiteScript.DoesNotExist:
            return Response({'error': '脚本不存在于该测试套件中'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'])
    def test_cases(self, request, pk=None):
        """获取测试套件中的所有测试用例"""
        test_suite = self.get_object()
        test_cases = test_suite.suite_test_cases.all()
        serializer = TestSuiteTestCaseSerializer(test_cases, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_test_case(self, request, pk=None):
        """向测试套件添加测试用例"""
        test_suite = self.get_object()
        test_case_id = request.data.get('test_case_id')
        order = request.data.get('order', 0)

        try:
            from .models import TestSuiteTestCase
            suite_test_case = TestSuiteTestCase.objects.create(
                test_suite=test_suite,
                test_case_id=test_case_id,
                order=order
            )
            serializer = TestSuiteTestCaseSerializer(suite_test_case)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['delete'])
    def remove_test_case(self, request, pk=None):
        """从测试套件移除测试用例"""
        test_suite = self.get_object()
        test_case_id = request.data.get('test_case_id')

        try:
            from .models import TestSuiteTestCase
            suite_test_case = TestSuiteTestCase.objects.get(
                test_suite=test_suite,
                test_case_id=test_case_id
            )
            suite_test_case.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except TestSuiteTestCase.DoesNotExist:
            return Response({'error': '测试用例不存在于该测试套件中'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'])
    def update_test_case_order(self, request, pk=None):
        """更新测试套件中测试用例的顺序"""
        test_suite = self.get_object()
        test_case_orders = request.data.get('test_case_orders', [])

        try:
            from .models import TestSuiteTestCase
            for item in test_case_orders:
                TestSuiteTestCase.objects.filter(
                    test_suite=test_suite,
                    test_case_id=item['test_case_id']
                ).update(order=item['order'])

            return Response({'message': '顺序更新成功'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def run_suite(self, request, pk=None):
        """执行测试套件"""
        test_suite = self.get_object()

        # 传统模式执行（Playwright/Selenium）
        # 检查是否包含测试用例
        test_case_count = test_suite.suite_test_cases.count()
        if test_case_count == 0:
            return Response({
                'error': '该测试套件未包含任何测试用例，无法执行'
            }, status=status.HTTP_400_BAD_REQUEST)

        engine = request.data.get('engine', 'playwright')
        browser = request.data.get('browser', 'chrome')
        headless = request.data.get('headless', False)

        # 更新套件执行状态为运行中
        test_suite.execution_status = 'running'
        test_suite.save()

        # 记录运行操作
        log_operation('run', 'suite', test_suite.id, test_suite.name, request.user)

        # 在后台线程中执行测试
        import threading
        import traceback
        from .test_executor import TestExecutor

        def run_test():
            try:
                print(f"[测试套件] 开始执行: {test_suite.name} (ID: {test_suite.id})")
                print(f"[测试套件] 配置: engine={engine}, browser={browser}, headless={headless}")

                executor = TestExecutor(
                    test_suite=test_suite,
                    engine=engine,
                    browser=browser,
                    headless=headless,
                    executed_by=request.user
                )
                executor.run()

                print(f"[测试套件] 执行完成: {test_suite.name}")
            except Exception as e:
                print(f"[测试套件] 执行异常: {test_suite.name}")
                print(f"[测试套件] 错误: {str(e)}")
                traceback.print_exc()

                # 更新套件状态为失败
                try:
                    test_suite.execution_status = 'failed'
                    test_suite.save()
                    print(f"[测试套件] 已更新状态为失败")
                except Exception as save_error:
                    print(f"[测试套件] 更新状态失败: {save_error}")

        # 启动后台线程执行测试
        thread = threading.Thread(target=run_test, daemon=False)
        thread.start()

        return Response({
            'message': '测试套件开始执行',
            'suite_id': test_suite.id,
            'test_case_count': test_case_count,
            'engine': engine,
            'browser': browser,
            'headless': headless
        }, status=status.HTTP_200_OK)


class TestExecutionViewSet(viewsets.ModelViewSet):
    queryset = TestExecution.objects.all()
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['project', 'test_suite', 'test_script', 'status', 'environment', 'executed_by']
    search_fields = ['error_message']
    ordering = ['-created_at']
    pagination_class = StandardPagination

    def get_queryset(self):
        # 只显示用户有权限访问的项目的测试执行记录
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return TestExecution.objects.filter(
            project__in=accessible_projects
        ).select_related('project', 'project__hub_project', 'test_suite', 'test_script', 'executed_by')

    def get_serializer_class(self):
        if self.action == 'create':
            return TestExecutionCreateSerializer
        return TestExecutionSerializer

    def perform_destroy(self, instance):
        # 记录操作（删除测试报告）
        suite_name = instance.test_suite.name if instance.test_suite else f"执行记录#{instance.id}"
        log_operation('delete', 'report', instance.id, suite_name, self.request.user)
        execution_id = instance.id
        instance.delete()
        for subdir in ('allure-reports', 'allure-results', 'allure-offline', 'reports'):
            target = os.path.join(
                settings.MEDIA_ROOT, 'ui-automation', subdir, f'execution_{execution_id}'
            )
            if os.path.isdir(target):
                shutil.rmtree(target, ignore_errors=True)

    def _find_allure_command(self):
        """定位项目内置 / 系统 Allure 可执行文件。"""
        exe = 'allure.bat' if os.name == 'nt' else 'allure'
        candidates = [
            Path(settings.BASE_DIR) / 'allure' / 'bin' / exe,
            Path(settings.BASE_DIR).parent / 'allure' / 'bin' / exe,
            Path(__file__).resolve().parent.parent.parent.parent / 'allure' / 'bin' / exe,
            Path('/usr/local/bin/allure'),
            Path('/usr/bin/allure'),
        ]
        for path in candidates:
            if path.exists():
                logger.info(f'使用 Allure: {path}')
                return path
        logger.warning('未找到 Allure 可执行文件')
        return None

    def _check_java_environment(self):
        """检查 Java 运行环境是否可用。"""
        try:
            result = subprocess.run(
                ['java', '-version'],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0
        except Exception as e:
            logger.warning(f'Java 环境检查失败: {e}')
            return False

    def _get_allure_results_dir(self, execution):
        return os.path.join(
            settings.MEDIA_ROOT, 'ui-automation', 'allure-results', f'execution_{execution.id}'
        )

    def _get_allure_report_dir(self, execution):
        return os.path.join(
            settings.MEDIA_ROOT, 'ui-automation', 'allure-reports', f'execution_{execution.id}'
        )

    def _get_allure_offline_dir(self, execution):
        return os.path.join(
            settings.MEDIA_ROOT, 'ui-automation', 'allure-offline', f'execution_{execution.id}'
        )

    def _suite_display_name(self, execution):
        if execution.test_suite:
            return execution.test_suite.name
        if execution.test_script:
            return execution.test_script.name
        return f'Execution #{execution.id}'

    def _project_display_name(self, execution):
        if not execution.project:
            return '-'
        if getattr(execution.project, 'hub_project', None):
            return execution.project.hub_project.name
        return execution.project.name

    def _map_allure_status(self, status_value):
        status_map = {
            'passed': 'passed',
            'failed': 'failed',
            'skipped': 'skipped',
            'broken': 'broken',
            'SUCCESS': 'passed',
            'FAILED': 'failed',
            'ABORTED': 'skipped',
            'PENDING': 'skipped',
            'RUNNING': 'broken',
        }
        return status_map.get(status_value, 'broken')

    def _generate_allure_result_files(self, execution, results_dir):
        """将 UI 执行结果转换为 Allure result JSON。"""
        os.makedirs(results_dir, exist_ok=True)
        for old in glob.glob(os.path.join(results_dir, '*')):
            try:
                if os.path.isfile(old):
                    os.remove(old)
            except Exception:
                pass

        cases = []
        if isinstance(execution.result_data, dict):
            cases = execution.result_data.get('test_cases') or []

        suite_name = self._suite_display_name(execution)
        project_name = self._project_display_name(execution)
        start_ms = int((execution.started_at or execution.created_at or timezone.now()).timestamp() * 1000)
        stop_ms = int((execution.finished_at or timezone.now()).timestamp() * 1000)
        if stop_ms <= start_ms:
            stop_ms = start_ms + max(int((execution.duration or 1) * 1000), 1)

        children = []
        if not cases:
            # 无明细时仍生成一条汇总结果，保证 Allure 可出报告
            uid = str(uuid.uuid4())
            children.append(uid)
            result = {
                'uuid': uid,
                'name': suite_name,
                'status': self._map_allure_status(execution.status),
                'stage': 'finished',
                'start': start_ms,
                'stop': stop_ms,
                'description': execution.error_message or '无用例明细',
                'historyId': f'ui-execution-{execution.id}',
                'fullName': f'{suite_name}',
                'labels': [
                    {'name': 'suite', 'value': suite_name},
                    {'name': 'package', 'value': 'ui_automation'},
                    {'name': 'framework', 'value': execution.engine or 'playwright'},
                    {'name': 'project', 'value': project_name},
                ],
                'steps': [],
            }
            if execution.error_message:
                result['statusDetails'] = {
                    'message': execution.error_message[:2000],
                    'trace': execution.error_message,
                }
            with open(os.path.join(results_dir, f'{uid}-result.json'), 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
        else:
            case_span = max((stop_ms - start_ms) // max(len(cases), 1), 1)
            for i, case in enumerate(cases):
                uid = str(uuid.uuid4())
                children.append(uid)
                case_name = case.get('test_case_name') or case.get('name') or f'Case {i + 1}'
                case_status = self._map_allure_status(case.get('status'))
                case_start = start_ms + i * case_span
                case_stop = case_start + case_span
                steps = []
                raw_steps = case.get('steps') or []
                step_span = max(case_span // max(len(raw_steps), 1), 1) if raw_steps else 1
                for j, step in enumerate(raw_steps):
                    step_name = (
                        step.get('description')
                        or step.get('action')
                        or step.get('name')
                        or f'Step {j + 1}'
                    )
                    step_status = self._map_allure_status(step.get('status') or case.get('status'))
                    step_start = case_start + j * step_span
                    steps.append({
                        'name': str(step_name),
                        'status': step_status,
                        'stage': 'finished',
                        'start': step_start,
                        'stop': step_start + step_span,
                        'steps': [],
                    })

                result = {
                    'uuid': uid,
                    'name': case_name,
                    'status': case_status,
                    'stage': 'finished',
                    'start': case_start,
                    'stop': case_stop,
                    'description': case.get('error') or case.get('error_message') or '',
                    'historyId': f'ui-case-{case.get("test_case_id") or i}-execution-{execution.id}',
                    'fullName': f'{suite_name} / {case_name}',
                    'labels': [
                        {'name': 'suite', 'value': suite_name},
                        {'name': 'testClass', 'value': suite_name},
                        {'name': 'package', 'value': 'ui_automation'},
                        {'name': 'framework', 'value': execution.engine or 'playwright'},
                        {'name': 'browser', 'value': execution.browser or 'chrome'},
                        {'name': 'project', 'value': project_name},
                    ],
                    'parameters': [
                        {'name': 'engine', 'value': str(execution.engine or '-')},
                        {'name': 'browser', 'value': str(execution.browser or '-')},
                    ],
                    'steps': steps,
                }
                err = case.get('error') or case.get('error_message')
                if err:
                    result['statusDetails'] = {'message': str(err)[:2000], 'trace': str(err)}

                with open(os.path.join(results_dir, f'{uid}-result.json'), 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

        container = {
            'uuid': str(uuid.uuid4()),
            'name': suite_name,
            'children': children,
            'befores': [],
            'afters': [],
            'start': start_ms,
            'stop': stop_ms,
        }
        with open(os.path.join(results_dir, f'{execution.id}-container.json'), 'w', encoding='utf-8') as f:
            json.dump(container, f, ensure_ascii=False, indent=2)

        env_lines = [
            f'Project={project_name}',
            f'Suite={suite_name}',
            f'Engine={execution.engine or "-"}',
            f'Browser={execution.browser or "-"}',
            f'Executor={(execution.executed_by.username if execution.executed_by else "-")}',
        ]
        with open(os.path.join(results_dir, 'environment.properties'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(env_lines))

    def _run_allure_generate(self, results_dir, output_dir, single_file=False):
        """调用 allure generate，成功返回 True。"""
        allure_cmd = self._find_allure_command()
        if not allure_cmd or not self._check_java_environment():
            return False

        os.makedirs(output_dir, exist_ok=True)
        if os.name == 'nt':
            cmd_list = [
                'cmd', '/c', str(allure_cmd),
                'generate', str(Path(results_dir)),
                '--clean',
            ]
        else:
            cmd_list = [
                str(allure_cmd),
                'generate', str(Path(results_dir)),
                '--clean',
            ]
        if single_file:
            cmd_list.append('--single-file')
        cmd_list.extend(['--output', str(Path(output_dir))])

        result = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            logger.error(
                f'Allure generate 失败 code={result.returncode}: '
                f'{result.stderr or result.stdout}'
            )
            return False
        return True

    def _is_single_file_allure_html(self, html_path):
        try:
            size = os.path.getsize(html_path)
            if size < 50_000:
                return False
            with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
                head = f.read(4000)
            if 'src="app.js"' in head or "src='app.js'" in head:
                return False
            if 'single_file' in head or 'single-file' in head or size > 200_000:
                return True
            return '<script' in head and 'styles.css' not in head
        except Exception:
            return False

    def _ensure_allure_results(self, execution):
        results_dir = self._get_allure_results_dir(execution)
        os.makedirs(results_dir, exist_ok=True)
        existing = glob.glob(os.path.join(results_dir, '*-result.json'))
        if not existing:
            self._generate_allure_result_files(execution, results_dir)
        return results_dir

    def _ensure_online_allure_report(self, execution):
        """生成在线 Allure 报告，返回可访问 URL。"""
        results_dir = self._ensure_allure_results(execution)
        report_dir = self._get_allure_report_dir(execution)
        index_path = os.path.join(report_dir, 'index.html')

        if not os.path.exists(index_path):
            ok = self._run_allure_generate(results_dir, report_dir, single_file=False)
            if not ok or not os.path.exists(index_path):
                raise RuntimeError('Allure 在线报告生成失败，请确认 Java 与 Allure 已配置')

        report_url = f'/media/ui-automation/allure-reports/execution_{execution.id}/index.html'
        if execution.report_url != report_url:
            execution.report_url = report_url
            execution.save(update_fields=['report_url'])
        return report_url

    def _ensure_offline_allure_html(self, execution):
        """生成可离线打开的 Allure 单文件 HTML，返回本地路径。"""
        offline_dir = self._get_allure_offline_dir(execution)
        offline_html = os.path.join(offline_dir, 'index.html')
        if os.path.exists(offline_html) and self._is_single_file_allure_html(offline_html):
            return offline_html

        results_dir = self._ensure_allure_results(execution)
        if os.path.exists(offline_dir):
            shutil.rmtree(offline_dir, ignore_errors=True)
        os.makedirs(offline_dir, exist_ok=True)

        ok = self._run_allure_generate(results_dir, offline_dir, single_file=True)
        if ok:
            for name in ('index.html', 'report.html', 'allure-report.html'):
                candidate = os.path.join(offline_dir, name)
                if os.path.exists(candidate) and self._is_single_file_allure_html(candidate):
                    return candidate

        raise RuntimeError('Allure 离线 HTML 生成失败，请确认 Java 与 Allure 已配置且支持 --single-file')

    @action(detail=True, methods=['post'], url_path='generate-allure-report')
    def generate_allure_report(self, request, pk=None):
        """生成 Allure 在线报告并返回 URL。"""
        execution = self.get_object()
        try:
            # 重新生成 results，保证报告与最新执行数据一致
            results_dir = self._get_allure_results_dir(execution)
            self._generate_allure_result_files(execution, results_dir)
            report_dir = self._get_allure_report_dir(execution)
            if os.path.exists(report_dir):
                shutil.rmtree(report_dir, ignore_errors=True)
            report_url = self._ensure_online_allure_report(execution)
            return Response({
                'report_url': report_url,
                'allure_report_url': report_url,
                'message': 'Allure 报告生成成功',
            })
        except Exception as e:
            logger.exception('生成 UI Allure 报告失败')
            return Response(
                {
                    'error': f'生成 Allure 报告失败: {e}',
                    'suggestion': '请检查 Java 与项目根目录 allure/bin 是否可用',
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=['get'], url_path='download-allure-report')
    def download_allure_report(self, request, pk=None):
        """下载 Allure 离线报告（单文件 HTML）。"""
        execution = self.get_object()
        try:
            results_dir = self._get_allure_results_dir(execution)
            self._generate_allure_result_files(execution, results_dir)
            offline_dir = self._get_allure_offline_dir(execution)
            if os.path.exists(offline_dir):
                shutil.rmtree(offline_dir, ignore_errors=True)
            html_path = self._ensure_offline_allure_html(execution)
            suite_name = self._suite_display_name(execution)
            safe_name = re.sub(r'[\\/:*?"<>|]+', '_', suite_name).strip() or f'execution_{execution.id}'
            filename = f'allure_report_{safe_name}_{execution.id}.html'
            response = FileResponse(open(html_path, 'rb'), content_type='text/html; charset=utf-8')
            response['Content-Disposition'] = (
                f'attachment; filename="allure_report_{execution.id}.html"; '
                f"filename*=UTF-8''{quote(filename)}"
            )
            return response
        except Exception as e:
            logger.exception('下载 UI Allure 报告失败')
            return Response(
                {'error': f'下载 Allure 报告失败: {e}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ScreenshotViewSet(viewsets.ModelViewSet):
    queryset = Screenshot.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = ScreenshotSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['execution']

    def get_queryset(self):
        # 只显示用户有权限访问的项目的截图
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        executions = TestExecution.objects.filter(project__in=accessible_projects)
        return Screenshot.objects.filter(execution__in=executions)


class TestCaseViewSet(viewsets.ModelViewSet):
    """测试用例视图集"""
    queryset = TestCase.objects.all()
    serializer_class = TestCaseSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at', 'name', 'priority', 'status']
    ordering = ['-created_at']
    filterset_fields = ['project', 'status', 'priority', 'created_by']

    def get_queryset(self):
        # 只显示用户有权限访问的项目的测试用例
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()

    def get_queryset(self):
        # 只显示用户有权限访问的项目的测试用例
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return TestCase.objects.filter(project__in=accessible_projects).select_related('project', 'created_by')

    def perform_create(self, serializer):
        # 创建测试用例
        instance = serializer.save(created_by=self.request.user)

        # 记录操作
        log_operation('create', 'test_case', instance.id, instance.name, self.request.user)

        # 处理步骤数据
        steps_data = self.request.data.get('steps', [])
        logger.info(f"创建测试用例 {instance.id} 的步骤数据: {len(steps_data)} 个步骤")

        if steps_data:
            # 创建新步骤
            created_count = 0
            for i, step_data in enumerate(steps_data):
                # 确保步骤数据结构正确
                step_data = dict(step_data)  # 创建副本避免修改原数据
                step_data['test_case'] = instance.id  # 使用测试用例ID
                step_data['step_number'] = i + 1  # 确保步骤序号正确

                # 处理元素ID
                if 'element_id' in step_data:
                    step_data['element'] = step_data.pop('element_id')

                # 移除只读字段
                step_data.pop('id', None)
                step_data.pop('element_name', None)
                step_data.pop('element_locator', None)
                step_data.pop('created_at', None)
                step_data.pop('expanded', None)  # 前端UI状态字段

                # 使用模型直接创建，避免序列化器的复杂性
                try:
                    TestCaseStep.objects.create(
                        test_case=instance,
                        step_number=step_data.get('step_number', i + 1),
                        action_type=step_data.get('action_type', 'click'),
                        page_filter=step_data.get('page_filter', ''),
                        element_id=step_data.get('element') if step_data.get('element') else None,
                        input_value=step_data.get('input_value', ''),
                        wait_time=step_data.get('wait_time', 1000),
                        assert_type=step_data.get('assert_type', ''),
                        assert_value=step_data.get('assert_value', ''),
                        description=step_data.get('description', '')
                    )
                    created_count += 1
                except Exception as e:
                    logger.error(f"创建步骤 {i + 1} 失败: {str(e)}")
                    logger.error(f"步骤数据: {step_data}")

            logger.info(f"成功创建了 {created_count} 个新步骤")

    @action(detail=True, methods=['post'])
    def copy_case(self, request, pk=None):
        """复制测试用例"""
        test_case = self.get_object()

        try:
            # 1. 复制测试用例基本信息
            new_case = TestCase.objects.create(
                project=test_case.project,
                name=f"{test_case.name}_copy",
                description=test_case.description,
                priority=test_case.priority,
                status=test_case.status,
                created_by=request.user
            )

            # 2. 复制测试步骤
            steps = test_case.steps.all().order_by('step_number')
            new_steps = []
            for step in steps:
                new_steps.append(TestCaseStep(
                    test_case=new_case,
                    step_number=step.step_number,
                    action_type=step.action_type,
                    page_filter=step.page_filter,
                    element=step.element,
                    input_value=step.input_value,
                    wait_time=step.wait_time,
                    assert_type=step.assert_type,
                    assert_value=step.assert_value,
                    description=step.description
                ))

            if new_steps:
                TestCaseStep.objects.bulk_create(new_steps)

            # 记录操作
            log_operation('create', 'test_case', new_case.id, new_case.name, request.user)

            serializer = self.get_serializer(new_case)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"复制测试用例失败: {str(e)}")
            return Response({'error': f"复制失败: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_update(self, serializer):
        # 更新测试用例步骤
        instance = serializer.save()

        # 记录操作
        log_operation('edit', 'test_case', instance.id, instance.name, self.request.user)

        # 处理步骤数据
        steps_data = self.request.data.get('steps', [])
        logger.info(f"更新测试用例 {instance.id} 的步骤数据: {len(steps_data)} 个步骤")

        if steps_data:
            # 删除现有步骤
            existing_steps_count = instance.steps.count()
            instance.steps.all().delete()
            logger.info(f"删除了 {existing_steps_count} 个现有步骤")

            # 创建新步骤
            created_count = 0
            for i, step_data in enumerate(steps_data):
                # 确保步骤数据结构正确
                step_data = dict(step_data)  # 创建副本避免修改原数据
                step_data['test_case'] = instance.id  # 使用测试用例ID
                step_data['step_number'] = i + 1  # 确保步骤序号正确

                # 处理元素ID
                if 'element_id' in step_data:
                    step_data['element'] = step_data.pop('element_id')

                # 移除只读字段
                step_data.pop('id', None)
                step_data.pop('element_name', None)
                step_data.pop('element_locator', None)
                step_data.pop('created_at', None)
                step_data.pop('expanded', None)  # 前端UI状态字段

                # 使用模型直接创建，避免序列化器的复杂性
                try:
                    TestCaseStep.objects.create(
                        test_case=instance,
                        step_number=step_data.get('step_number', i + 1),
                        action_type=step_data.get('action_type', 'click'),
                        page_filter=step_data.get('page_filter', ''),
                        element_id=step_data.get('element') if step_data.get('element') else None,
                        input_value=step_data.get('input_value', ''),
                        wait_time=step_data.get('wait_time', 1000),
                        assert_type=step_data.get('assert_type', ''),
                        assert_value=step_data.get('assert_value', ''),
                        description=step_data.get('description', '')
                    )
                    created_count += 1
                except Exception as e:
                    logger.error(f"创建步骤 {i + 1} 失败: {str(e)}")
                    logger.error(f"步骤数据: {step_data}")

            logger.info(f"成功创建了 {created_count} 个新步骤")

    def _generate_step_log(self, step, step_result='success'):
        """根据测试步骤生成执行日志"""
        import time

        # 模拟执行时间（0.1秒到2秒之间）
        execution_time = round(random.uniform(0.1, 2.0), 2)

        # 构建基础日志
        log_parts = []

        # 步骤信息
        if step.element:
            element_name = step.element.name
            locator_info = f"{step.element.locator_strategy.name}={step.element.locator_value}"
        else:
            element_name = "页面"
            locator_info = "无"

        # 根据操作类型生成具体日志
        if step.action_type == 'click':
            log_parts.append(f"点击元素 '{element_name}'")
            log_parts.append(f"- 使用定位器: {locator_info}")
            if step_result == 'success':
                log_parts.append(f"- 元素点击成功 - 耗时 {execution_time}s")
            else:
                log_parts.append(f"- 元素点击失败 - 元素未找到或不可点击")

        elif step.action_type == 'fill':
            log_parts.append(f"在元素 '{element_name}' 中输入文本")
            log_parts.append(f"- 使用定位器: {locator_info}")
            log_parts.append(f"- 输入值: '{step.input_value}'")
            if step_result == 'success':
                log_parts.append(f"- 文本输入成功 - 耗时 {execution_time}s")
            else:
                log_parts.append(f"- 文本输入失败 - 元素未找到或不可编辑")

        elif step.action_type == 'getText':
            log_parts.append(f"获取元素 '{element_name}' 的文本内容")
            log_parts.append(f"- 使用定位器: {locator_info}")
            if step_result == 'success':
                # 模拟获取到的文本
                mock_text = f"示例文本内容_{step.id}" if step.id else "示例文本内容"
                log_parts.append(f"- 获取到文本: '{mock_text}' - 耗时 {execution_time}s")
            else:
                log_parts.append(f"- 获取文本失败 - 元素未找到")

        elif step.action_type == 'waitFor':
            log_parts.append(f"等待元素 '{element_name}' 出现")
            log_parts.append(f"- 使用定位器: {locator_info}")
            log_parts.append(f"- 超时时间: {step.wait_time / 1000}秒")
            if step_result == 'success':
                log_parts.append(f"- 元素在 {execution_time}s 后出现")
            else:
                log_parts.append(f"- 等待超时 - 元素未在指定时间内出现")

        elif step.action_type == 'hover':
            log_parts.append(f"在元素 '{element_name}' 上悬停")
            log_parts.append(f"- 使用定位器: {locator_info}")
            if step_result == 'success':
                log_parts.append(f"- 悬停操作成功 - 耗时 {execution_time}s")
            else:
                log_parts.append(f"- 悬停操作失败 - 元素未找到")

        elif step.action_type == 'scroll':
            log_parts.append(f"滚动到元素 '{element_name}'")
            log_parts.append(f"- 使用定位器: {locator_info}")
            if step_result == 'success':
                log_parts.append(f"- 滚动操作成功 - 耗时 {execution_time}s")
            else:
                log_parts.append(f"- 滚动操作失败 - 元素未找到")

        elif step.action_type == 'screenshot':
            log_parts.append(f"执行截图操作")
            if step.element:
                log_parts.append(f"- 截图范围: 元素 '{element_name}'")
            else:
                log_parts.append(f"- 截图范围: 整个页面")
            if step_result == 'success':
                screenshot_name = f"screenshot_{int(time.time())}.png"
                log_parts.append(f"- 截图保存成功: {screenshot_name} - 耗时 {execution_time}s")
            else:
                log_parts.append(f"- 截图保存失败")

        elif step.action_type == 'assert':
            log_parts.append(f"执行断言验证")
            log_parts.append(f"- 断言类型: {step.assert_type}")
            if step.assert_value:
                log_parts.append(f"- 期望值: '{step.assert_value}'")
            if step_result == 'success':
                log_parts.append(f"- 断言通过 - 耗时 {execution_time}s")
            else:
                log_parts.append(f"- 断言失败 - 实际值与期望值不匹配")

        elif step.action_type == 'wait':
            log_parts.append(f"固定等待")
            log_parts.append(f"- 等待时间: {step.wait_time / 1000}秒")
            log_parts.append(f"- 等待完成")

        elif step.action_type == 'navigateUrl':
            log_parts.append(f"跳转URL")
            log_parts.append(f"- 目标URL: {step.input_value}")
            if step_result == 'success':
                log_parts.append(f"- 跳转成功 - 耗时 {execution_time}s")
            else:
                log_parts.append(f"- 跳转失败")

        else:
            # 默认处理其他操作类型
            log_parts.append(f"执行操作: {step.action_type}")
            if step.element:
                log_parts.append(f"- 目标元素: {element_name}")
            if step.input_value:
                log_parts.append(f"- 输入值: {step.input_value}")
            log_parts.append(f"- 操作{'成功' if step_result == 'success' else '失败'} - 耗时 {execution_time}s")

        # 如果步骤有描述，添加到日志中
        if step.description:
            log_parts.insert(0, f"说明: {step.description}")

        return '\n'.join(log_parts)

    def _generate_failure_screenshot(self, step_number, step_description):
        """生成失败截图的模拟数据（base64格式）"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            import io
            import base64

            # 创建一个模拟的失败截图
            # 实际应用中，这里应该是通过Playwright/Selenium捕获真实的页面截图
            width, height = 1280, 720
            img = Image.new('RGB', (width, height), color=(240, 240, 245))
            draw = ImageDraw.Draw(img)

            # 绘制标题区域
            draw.rectangle([0, 0, width, 80], fill=(220, 53, 69))

            # 添加文本信息（使用默认字体）
            try:
                # 尝试使用系统字体
                font_title = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 40)
                font_text = ImageFont.truetype("/System/Library/Fonts/PingFang.ttc", 24)
            except:
                # 如果系统字体不可用，使用默认字体
                font_title = ImageFont.load_default()
                font_text = ImageFont.load_default()

            # 标题
            draw.text((40, 20), "测试步骤执行失败", fill=(255, 255, 255), font=font_title)

            # 失败信息
            info_y = 120
            draw.text((40, info_y), f"失败步骤: 步骤 {step_number}", fill=(50, 50, 50), font=font_text)
            draw.text((40, info_y + 40), f"步骤说明: {step_description}", fill=(50, 50, 50), font=font_text)
            draw.text((40, info_y + 80), f"失败时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}",
                      fill=(50, 50, 50), font=font_text)

            # 绘制一个模拟的浏览器窗口
            browser_y = info_y + 140
            draw.rectangle([40, browser_y, width - 40, height - 40], outline=(200, 200, 200), width=2)
            draw.rectangle([40, browser_y, width - 40, browser_y + 40], fill=(200, 200, 200))
            draw.text((60, browser_y + 10), "模拟浏览器页面 - 失败截图", fill=(80, 80, 80), font=font_text)

            # 在浏览器窗口中绘制错误提示
            error_y = browser_y + 80
            draw.text((60, error_y), "× 元素定位失败或操作执行异常", fill=(220, 53, 69), font=font_text)
            draw.text((60, error_y + 40), "× 请检查元素定位器是否正确", fill=(220, 53, 69), font=font_text)
            draw.text((60, error_y + 80), "× 或页面加载是否完成", fill=(220, 53, 69), font=font_text)

            # 转换为base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_base64 = base64.b64encode(buffer.getvalue()).decode()

            return f"data:image/png;base64,{img_base64}"

        except Exception as e:
            logger.error(f"生成失败截图时出错: {str(e)}")
            # 返回一个简单的错误占位符
            return None

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """运行单个测试用例 - 支持选择Playwright或Selenium执行引擎"""
        test_case = self.get_object()

        try:
            # 获取执行引擎选择，默认使用playwright
            engine_type = request.data.get('engine', 'playwright')
            browser_name = request.data.get('browser', 'chrome')
            headless_raw = request.data.get('headless', False)
            if isinstance(headless_raw, str):
                headless_mode = headless_raw.strip().lower() in ('1', 'true', 'yes', 'on')
            else:
                headless_mode = bool(headless_raw)

            target_url = (request.data.get('target_url') or request.data.get('url') or '').strip()
            if not target_url or target_url in {'https://', 'http://'}:
                from .codegen_service import codegen_recorder
                target_url = codegen_recorder._resolve_project_base_url(
                    getattr(test_case, 'project_id', None)
                )

            auto_login_raw = request.data.get('auto_login', False)
            if isinstance(auto_login_raw, str):
                auto_login = auto_login_raw.strip().lower() not in {'0', 'false', 'no', 'off'}
            else:
                auto_login = bool(auto_login_raw)

            # 创建执行记录
            execution = TestCaseExecution.objects.create(
                test_case=test_case,
                project=test_case.project,
                execution_source='manual',
                status='running',
                engine=engine_type,
                browser=browser_name,
                headless=headless_mode,
                created_by=request.user,
                started_at=timezone.now()
            )

            # 根据引擎类型导入对应的执行引擎
            if engine_type == 'selenium':
                from .selenium_engine import SeleniumTestEngine

                # Selenium 引擎需要预先检查浏览器是否可用
                browser_type = browser_name
                is_available, error_msg = SeleniumTestEngine.check_browser_available(browser_type)
                if not is_available:
                    # 浏览器不可用，立即返回错误
                    logger.error(f"Selenium 浏览器检查失败: {error_msg}")
                    execution.status = 'failed'
                    execution.error_message = error_msg
                    execution.execution_logs = f"浏览器检查失败\n\n{error_msg}\n\n建议：\n1. 请确认已安装 {browser_type.capitalize()} 浏览器\n2. 或者尝试使用其他浏览器（Chrome、Firefox、Edge）\n3. 或者使用 Playwright 引擎（支持自动下载浏览器）"
                    execution.finished_at = timezone.now()
                    execution.save()

                    return Response({
                        'success': False,
                        'logs': execution.execution_logs,
                        'screenshots': [],
                        'execution_time': 0,
                        'errors': [{
                            'message': f'{browser_type.capitalize()} 浏览器不可用',
                            'details': error_msg,
                            'step_number': None,
                            'action_type': '浏览器检查',
                            'element': '',
                            'description': '执行前浏览器环境检查'
                        }]
                    }, status=status.HTTP_400_BAD_REQUEST)
            else:
                import asyncio
                import threading
                from .playwright_engine import PlaywrightTestEngine

            start_time = time.time()

            # 获取测试用例的所有步骤
            test_steps = list(test_case.steps.all().order_by('step_number'))

            # 预先获取所有步骤的数据,避免在异步上下文中访问ORM
            steps_data = []
            for step in test_steps:
                step_data = {
                    'step': step,
                    'action_type': step.action_type,
                    'description': step.description,
                    'input_value': step.input_value,
                    'wait_time': step.wait_time,
                    'assert_type': step.assert_type,
                    'assert_value': step.assert_value,
                }

                # 获取元素数据
                if step.element:
                    step_data['element_data'] = {
                        'locator_strategy': step.element.locator_strategy.name if step.element.locator_strategy else 'css',
                        'locator_value': step.element.locator_value,
                        'name': step.element.name,
                        'description': getattr(step.element, 'description', '') or '',
                        'element_type': getattr(step.element, 'element_type', '') or '',
                        'wait_timeout': step.element.wait_timeout,  # 添加元素的等待超时设置（秒）
                        'force_action': step.element.force_action,  # 添加强制操作选项
                        'backup_locators': step.element.backup_locators or [],
                    }
                else:
                    step_data['element_data'] = None

                steps_data.append(step_data)

            # 复用登录态：跳过用例中的登录相关步骤（点登录/填账号密码等）
            skipped_login_steps = 0
            if auto_login and steps_data:
                from .auth_state import is_login_related_step

                kept = []
                for sd in steps_data:
                    if is_login_related_step(sd):
                        skipped_login_steps += 1
                    else:
                        kept.append(sd)
                steps_data = kept

            # 存储步骤执行结果（用于JSON格式的execution_logs）
            step_results = []

            # 生成执行日志（保留文本格式用于调试）
            execution_logs = []
            execution_logs.append(f"测试用例 '{test_case.name}' 开始执行")
            execution_logs.append(f"执行时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
            execution_logs.append(f"执行引擎: {engine_type.upper()}")
            execution_logs.append(f"浏览器: {browser_name.capitalize()}")
            mode_text = "无头模式" if headless_mode else "有头模式"
            execution_logs.append(f"执行模式: {mode_text}")
            execution_logs.append(f"执行用户: {request.user.username}")
            execution_logs.append(f"目标URL: {target_url or '(未指定)'}")
            execution_logs.append(f"复用登录态: {'是' if auto_login else '否'}")
            if auto_login and skipped_login_steps:
                execution_logs.append(f"已跳过登录相关步骤: {skipped_login_steps} 个")
            execution_logs.append("")

            # 截图列表
            screenshots = []
            # 详细错误信息列表
            detailed_errors = []
            execution_result = {'status': 'passed', 'error_message': None}

            login_username, login_password = ('', '')
            auth_state_file = None
            storage_to_load = None
            if auto_login:
                from .codegen_service import codegen_recorder
                from .auth_state import auth_path_for_project, ensure_project_auth_state, load_path_if_exists

                # 启动前静默确保登录态：缺失/失效则 headless 登录并写回；运行时只注入文件
                login_username, login_password = codegen_recorder._resolve_project_login(
                    getattr(test_case, 'project_id', None)
                )
                auth_state_file = auth_path_for_project(getattr(test_case, 'project_id', None))
                existing = load_path_if_exists(auth_state_file)
                if not existing and not (login_username and login_password):
                    execution_logs.append(
                        "⚠ 复用登录态失败：未配置登录账号/密码且无已保存登录态"
                    )
                else:
                    ensured = ensure_project_auth_state(
                        getattr(test_case, 'project_id', None),
                        base_url=target_url or '',
                        username=login_username,
                        password=login_password,
                    )
                    storage_to_load = ensured or existing
                    if not storage_to_load:
                        execution_logs.append("⚠ 复用登录态失败：静默登录未成功")

            # 根据引擎类型选择执行方式
            if engine_type == 'selenium':
                # Selenium同步执行
                def run_test_selenium():
                    """使用Selenium执行测试"""
                    browser_type = browser_name
                    headless = headless_mode

                    # 创建Selenium引擎实例
                    engine = SeleniumTestEngine(browser_type=browser_type, headless=headless)

                    try:
                        # 启动浏览器
                        execution_logs.append("========== 初始化浏览器 ==========")
                        try:
                            engine.start()
                            mode_text = "无头模式" if headless else "有头模式"
                            execution_logs.append(
                                f"✓ {browser_type.capitalize()} 浏览器启动成功 (Selenium, {mode_text})")
                            execution_logs.append("")
                        except Exception as browser_error:
                            # 浏览器启动失败
                            execution_logs.append(f"✗ {browser_type.capitalize()} 浏览器启动失败")
                            execution_logs.append(f"  错误: {str(browser_error)}")
                            execution_logs.append("")
                            execution_result['status'] = 'failed'
                            execution_result[
                                'error_message'] = f"{browser_type.capitalize()} 浏览器启动失败: {str(browser_error)}"

                            # 添加详细错误信息
                            detailed_errors.append({
                                'step_number': None,
                                'action_type': '浏览器启动',
                                'element': '',
                                'message': f"{browser_type.capitalize()} 浏览器启动失败",
                                'details': str(browser_error),
                                'description': '执行前浏览器启动检查'
                            })

                            return False

                        # 导航到目标URL
                        if target_url:
                            execution_logs.append("========== 导航到测试页面 ==========")
                            success, nav_log = engine.navigate(target_url)
                            execution_logs.append(nav_log)
                            execution_logs.append("")

                            if not success:
                                execution_result['status'] = 'failed'
                                execution_result['error_message'] = f"导航到测试页面失败: {nav_log}"
                                detailed_errors.append({
                                    'step_number': None,
                                    'action_type': '导航',
                                    'element': '',
                                    'message': '导航到测试页面失败',
                                    'details': nav_log,
                                    'description': f'导航到 {target_url} 失败'
                                })
                                return False

                        if auto_login:
                            execution_logs.append("========== 复用登录态 ==========")
                            execution_logs.append("⚠ Selenium 引擎暂不支持复用登录态，已跳过")
                            execution_logs.append("")

                        if steps_data:
                            execution_logs.append("========== 执行测试步骤 ==========")
                            step_count = len(steps_data)
                            execution_logs.append(f"共有 {step_count} 个步骤需要执行")
                            execution_logs.append("")

                            for i, step_info in enumerate(steps_data, 1):
                                execution_logs.append(f"========== 开始执行步骤 {i}/{step_count} ==========")
                                execution_logs.append(f"步骤 {i}/{step_count}:")

                                step = step_info['step']
                                action_type = step_info['action_type']
                                description = step_info['description']
                                element_data = step_info['element_data']

                                action_choices_dict = dict(TestCaseStep.ACTION_TYPE_CHOICES)
                                action_type_text = action_choices_dict.get(action_type, action_type)
                                execution_logs.append(f"  操作: {action_type_text}")

                                if description:
                                    execution_logs.append(f"  说明: {description}")

                                if element_data:
                                    execution_logs.append(f"  元素: {element_data['name']}")
                                    execution_logs.append(
                                        f"  定位器: {element_data['locator_strategy']}={element_data['locator_value']}")
                                else:
                                    execution_logs.append(f"  (此步骤不需要元素)")

                                try:
                                    success, step_log, screenshot_base64 = engine.execute_step(step, element_data or {})
                                    execution_logs.append(f"  {step_log}")
                                    execution_logs.append("")

                                    # 记录步骤执行结果（用于JSON格式）
                                    step_results.append({
                                        'step_number': i,
                                        'action_type': action_type,
                                        'description': description or '',
                                        'success': success,
                                        'error': None if success else step_log
                                    })

                                    if not success:
                                        logger.info(f"[调试-Selenium] 步骤 {i} 执行失败，设置状态为 failed")
                                        execution_result['status'] = 'failed'
                                        element_info = element_data['name'] if element_data else "未知元素"
                                        execution_result['error_message'] = step_log  # 使用step_log作为错误信息
                                        logger.info(f"[调试-Selenium] execution_result = {execution_result}")

                                        detailed_errors.append({
                                            'step_number': i,
                                            'action_type': action_type_text,
                                            'element': element_info,
                                            'message': f"步骤 {i}/{step_count} 执行失败",
                                            'details': step_log,
                                            'description': description or ''
                                        })

                                        if not screenshot_base64:
                                            screenshot_base64 = engine.capture_screenshot()

                                        if screenshot_base64:
                                            screenshots.append({
                                                'url': screenshot_base64,
                                                'description': f'步骤 {i} 失败截图: {description or action_type_text}',
                                                'step_number': i,
                                                'timestamp': timezone.now().isoformat()
                                                # 移除 loaded 和 error 字段，让前端自行处理
                                            })
                                            execution_logs.append(f"  📸 失败截图已捕获")

                                        return False

                                    if action_type == 'screenshot' and screenshot_base64:
                                        screenshots.append({
                                            'url': screenshot_base64,
                                            'description': f'步骤 {i}: {description or "手动截图"}',
                                            'step_number': i,
                                            'timestamp': timezone.now().isoformat()
                                            # 移除 loaded 和 error 字段，让前端自行处理
                                        })

                                except Exception as e:
                                    execution_logs.append(f"  ✗ 步骤执行异常: {str(e)}")
                                    import traceback
                                    tb_str = traceback.format_exc()
                                    execution_logs.append(f"  [调试] 异常堆栈:\n{tb_str}")

                                    # 记录步骤执行结果（异常情况）
                                    step_results.append({
                                        'step_number': i,
                                        'action_type': action_type,
                                        'description': description or '',
                                        'success': False,
                                        'error': str(e)
                                    })

                                    execution_result['status'] = 'failed'
                                    execution_result['error_message'] = f"步骤 {i} 执行异常: {str(e)}"

                                    element_info = element_data['name'] if element_data else "未知元素"
                                    detailed_errors.append({
                                        'step_number': i,
                                        'action_type': action_type_text,
                                        'element': element_info,
                                        'message': f"步骤 {i}/{step_count} 执行异常",
                                        'details': f"异常: {str(e)}\n\n堆栈跟踪:\n{tb_str}",
                                        'description': description or ''
                                    })

                                    try:
                                        screenshot_base64 = engine.capture_screenshot()
                                        if screenshot_base64:
                                            screenshots.append({
                                                'url': screenshot_base64,
                                                'description': f'步骤 {i} 异常截图: {str(e)}',
                                                'step_number': i,
                                                'timestamp': timezone.now().isoformat()
                                                # 移除 loaded 和 error 字段，让前端自行处理
                                            })
                                    except:
                                        pass

                                    return False

                            execution_logs.append(f"========== 执行完成 ({step_count} 个步骤全部通过) ==========")
                            return True
                        else:
                            execution_logs.append("警告: 测试用例没有定义任何步骤")
                            return True

                    finally:
                        execution_logs.append("")
                        execution_logs.append("========== 清理资源 ==========")
                        engine.stop()
                        execution_logs.append("✓ 浏览器已关闭")

                # 在独立线程中运行Selenium测试
                import threading
                test_thread = threading.Thread(target=run_test_selenium)
                test_thread.start()
                test_thread.join()

            else:
                # Playwright异步执行
                def run_test_in_thread():
                    """在独立线程中运行异步测试"""

                    async def run_test():
                        """异步执行测试"""
                        # 根据浏览器类型选择
                        browser_map = {
                            'chrome': 'chromium',
                            'firefox': 'firefox',
                            'safari': 'webkit',
                            'edge': 'chromium',
                        }
                        browser_type = browser_map.get(browser_name, 'chromium')
                        headless = headless_mode

                        # 创建Playwright引擎实例
                        engine = PlaywrightTestEngine(browser_type=browser_type, headless=headless)

                        try:
                            # 启动浏览器（有未过期登录态则直接注入）
                            execution_logs.append("========== 初始化浏览器 ==========")
                            await engine.start(storage_state=storage_to_load)
                            mode_text = "无头模式" if headless else "有头模式"
                            execution_logs.append(
                                f"✓ {browser_type.capitalize()} 浏览器启动成功 (Playwright, {mode_text})")
                            if storage_to_load:
                                execution_logs.append(f"✓ 已加载项目登录态: {storage_to_load}")
                            execution_logs.append("")

                            # 导航到目标URL
                            if target_url:
                                execution_logs.append("========== 导航到测试页面 ==========")
                                success, nav_log = await engine.navigate(target_url)
                                execution_logs.append(nav_log)
                                execution_logs.append("")

                                if not success:
                                    execution_result['status'] = 'failed'
                                    execution_result['error_message'] = f"导航到测试页面失败: {nav_log}"
                                    detailed_errors.append({
                                        'step_number': None,
                                        'action_type': '导航',
                                        'element': '',
                                        'message': '导航到测试页面失败',
                                        'details': nav_log,
                                        'description': f'导航到 {target_url} 失败'
                                    })
                                    return False

                            if auto_login:
                                execution_logs.append("========== 复用登录态 ==========")
                                if storage_to_load:
                                    execution_logs.append(
                                        f"✓ 已加载项目登录态，跳过登录 "
                                        f"({login_username or '已保存会话'})"
                                    )
                                    # 刷新 cookies / mtime，延长复用窗口
                                    if auth_state_file is not None and getattr(engine, 'context', None):
                                        from .auth_state import save_storage_state
                                        await save_storage_state(engine.context, auth_state_file)
                                elif auth_state_file is not None:
                                    execution_logs.append(
                                        f"⚠ 未找到可用登录态（请在项目中配置登录账号或先手动登录一次）: "
                                        f"{auth_state_file}"
                                    )
                                else:
                                    execution_logs.append("⚠ 无法解析项目登录态路径，已跳过登录")
                                execution_logs.append("")

                            if steps_data:
                                execution_logs.append("========== 执行测试步骤 ==========")
                                step_count = len(steps_data)
                                execution_logs.append(f"共有 {step_count} 个步骤需要执行")
                                execution_logs.append("")

                                for i, step_info in enumerate(steps_data, 1):
                                    execution_logs.append(f"========== 开始执行步骤 {i}/{step_count} ==========")
                                    execution_logs.append(f"步骤 {i}/{step_count}:")

                                    # 从预先获取的数据中获取信息
                                    step = step_info['step']
                                    action_type = step_info['action_type']
                                    description = step_info['description']
                                    element_data = step_info['element_data']

                                    # 获取操作类型的中文显示
                                    action_choices_dict = dict(TestCaseStep.ACTION_TYPE_CHOICES)
                                    action_type_text = action_choices_dict.get(action_type, action_type)
                                    execution_logs.append(f"  操作: {action_type_text}")

                                    if description:
                                        execution_logs.append(f"  说明: {description}")

                                    if element_data:
                                        execution_logs.append(f"  元素: {element_data['name']}")
                                        execution_logs.append(
                                            f"  定位器: {element_data['locator_strategy']}={element_data['locator_value']}")
                                    else:
                                        execution_logs.append(f"  (此步骤不需要元素)")

                                    # 执行步骤
                                    try:
                                        execution_logs.append(f"  [调试] 准备执行步骤...")
                                        success, step_log, screenshot_base64 = await engine.execute_step(step,
                                                                                                         element_data or {})
                                        execution_logs.append(f"  [调试] 步骤执行完成, success={success}")

                                        # AI 自愈：仅当次临时定位，不改元素/步骤；成功时写入结果标记
                                        healed = bool(element_data and element_data.get('_healed'))
                                        healing_reason = (
                                            (element_data or {}).get('_healing_reason') if element_data else None
                                        )
                                        healed_locator = (
                                            (element_data or {}).get('_healed_locator') if element_data else None
                                        )
                                        if healed and success:
                                            from .playwright_engine import PlaywrightTestEngine as _PTE
                                            step_log = _PTE.append_heal_note(step_log, element_data)
                                            execution_logs.append(
                                                f"  ★ AI自愈执行通过: {healing_reason or ''}"
                                            )

                                        execution_logs.append(f"  {step_log}")
                                        execution_logs.append("")

                                        # 记录步骤执行结果（用于JSON格式）
                                        step_results.append({
                                            'step_number': i,
                                            'action_type': action_type,
                                            'description': description or '',
                                            'success': success,
                                            'error': None if success else step_log,
                                            'healed': healed and success,
                                            'healing_reason': healing_reason if (healed and success) else None,
                                            'healed_locator': healed_locator if (healed and success) else None,
                                        })

                                        # 如果步骤失败,保存截图
                                        if not success:
                                            execution_logs.append(f"  [调试] 检测到步骤失败,准备处理...")
                                            execution_result['status'] = 'failed'

                                            # 获取失败的元素信息
                                            element_info = element_data['name'] if element_data else "未知元素"

                                            execution_result['error_message'] = step_log  # 使用step_log作为错误信息

                                            # 添加详细错误信息
                                            detailed_errors.append({
                                                'step_number': i,
                                                'action_type': action_type_text,
                                                'element': element_info,
                                                'message': f"步骤 {i}/{step_count} 执行失败",
                                                'details': step_log,  # 包含详细的错误日志
                                                'description': description or ''
                                            })

                                            # 如果没有截图,捕获一张
                                            if not screenshot_base64:
                                                screenshot_base64 = await engine.capture_screenshot()

                                        if screenshot_base64:
                                            screenshots.append({
                                                'url': screenshot_base64,
                                                'description': f'步骤 {i} 失败截图: {description or action_type_text}',
                                                'step_number': i,
                                                'timestamp': timezone.now().isoformat()
                                                # 移除 loaded 和 error 字段，让前端自行处理
                                            })
                                            execution_logs.append(f"  📸 失败截图已捕获")

                                            execution_logs.append(f"  [调试] 步骤失败,准备退出执行...")
                                            return False

                                        # 如果是截图步骤且成功,也保存截图
                                        if action_type == 'screenshot' and screenshot_base64:
                                            screenshots.append({
                                                'url': screenshot_base64,
                                                'description': f'步骤 {i}: {description or "手动截图"}',
                                                'step_number': i,
                                                'timestamp': timezone.now().isoformat()
                                                # 移除 loaded 和 error 字段，让前端自行处理
                                            })

                                        execution_logs.append(f"  [调试] 步骤 {i} 成功完成,准备执行下一步...")

                                    except Exception as e:
                                        execution_logs.append(f"  ✗ 步骤执行异常: {str(e)}")
                                        execution_logs.append(f"  [调试] 异常详情: {repr(e)}")
                                        import traceback
                                        tb_str = traceback.format_exc()
                                        execution_logs.append(f"  [调试] 异常堆栈:\n{tb_str}")

                                        # 记录步骤执行结果（异常情况）
                                        step_results.append({
                                            'step_number': i,
                                            'action_type': action_type,
                                            'description': description or '',
                                            'success': False,
                                            'error': str(e)
                                        })

                                        execution_result['status'] = 'failed'
                                        execution_result['error_message'] = f"步骤 {i} 执行异常: {str(e)}"

                                        # 添加详细错误信息
                                        element_info = element_data['name'] if element_data else "未知元素"
                                        detailed_errors.append({
                                            'step_number': i,
                                            'action_type': action_type_text,
                                            'element': element_info,
                                            'message': f"步骤 {i}/{step_count} 执行异常",
                                            'details': f"异常: {str(e)}\n\n堆栈跟踪:\n{tb_str}",
                                            'description': description or ''
                                        })

                                        # 捕获异常截图
                                        try:
                                            screenshot_base64 = await engine.capture_screenshot()
                                            if screenshot_base64:
                                                screenshots.append({
                                                    'url': screenshot_base64,
                                                    'description': f'步骤 {i} 异常截图: {str(e)}',
                                                    'step_number': i,
                                                    'timestamp': timezone.now().isoformat()
                                                    # 移除 loaded 和 error 字段，让前端自行处理
                                                })
                                        except:
                                            pass

                                        execution_logs.append(f"  [调试] 发生异常,准备退出执行...")
                                        return False

                                # 所有步骤都成功
                                execution_logs.append(f"========== 执行完成 ({step_count} 个步骤全部通过) ==========")
                                return True

                            else:
                                execution_logs.append("警告: 测试用例没有定义任何步骤")
                                return True

                        finally:
                            # 关闭浏览器
                            execution_logs.append("")
                            execution_logs.append("========== 清理资源 ==========")
                            await engine.stop()
                            execution_logs.append("✓ 浏览器已关闭")

                    # 在新的事件循环中运行测试
                    # 注意：daphne/channels 在 Windows 上会把事件循环策略设置为
                    # WindowsSelectorEventLoopPolicy，而 SelectorEventLoop 不支持子进程，
                    # 会导致 Playwright 启动 node 子进程时抛 NotImplementedError。
                    # 因此在 Windows 上必须显式创建 ProactorEventLoop。
                    import sys
                    if sys.platform == 'win32':
                        loop = asyncio.ProactorEventLoop()
                    else:
                        loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(run_test())
                    except Exception as thread_err:
                        # 捕获子线程内未处理的异常，避免异常被吞掉导致
                        # 前端看到空日志、空错误但 success=true 的迷惑现象
                        logger.error(f"[Playwright] 测试执行线程异常: {thread_err}", exc_info=True)
                        execution_result['status'] = 'failed'
                        execution_result['error_message'] = f"测试执行异常: {thread_err}"
                        detailed_errors.append({
                            'step_number': None,
                            'action_type': '执行引擎',
                            'element': '',
                            'message': '测试执行线程异常',
                            'details': str(thread_err),
                            'description': 'Playwright 执行过程中发生未捕获异常'
                        })
                    finally:
                        loop.close()

                # 在独立线程中运行Playwright测试
                import threading
                test_thread = threading.Thread(target=run_test_in_thread)
                test_thread.start()
                test_thread.join()  # 等待测试完成

            # 计算总执行时间
            total_time = round(time.time() - start_time, 2)
            execution_logs.append("")
            execution_logs.append("执行环境信息:")
            execution_logs.append(f"- 执行引擎: {engine_type.upper()}")
            execution_logs.append(f"- 浏览器: {browser_name.capitalize()}")
            execution_logs.append(f"- 屏幕分辨率: 1920x1080")
            execution_logs.append(f"- 总执行时间: {total_time}秒")
            if target_url:
                execution_logs.append(f"- 目标URL: {target_url}")
            execution_logs.append(f"- 复用登录态: {'是' if auto_login else '否'}")

            if screenshots:
                execution_logs.append(f"- 截图数量: {len(screenshots)} 张")

            # 保存执行日志和截图
            logger.info(f"[调试] 准备保存执行结果: execution_result['status'] = {execution_result['status']}")
            execution.status = execution_result['status']

            # 保存error_message（step_log已经是简洁的错误信息）
            execution.error_message = execution_result['error_message'] or ''

            # 保存步骤执行结果为JSON格式
            execution.execution_logs = json.dumps(step_results, ensure_ascii=False)
            execution.execution_time = total_time
            execution.finished_at = timezone.now()
            execution.screenshots = screenshots
            execution.save()
            logger.info(f"[调试] 执行结果已保存: execution.status = {execution.status}")

            serializer = TestCaseExecutionSerializer(execution)
            # 格式化错误信息为统一的对象格式
            errors = []
            if detailed_errors:
                # 使用详细的错误信息
                for error in detailed_errors:
                    errors.append({
                        'message': error['message'],
                        'details': error['details'],
                        'step_number': error['step_number'],
                        'action_type': error['action_type'],
                        'element': error['element'],
                        'description': error['description']
                    })
            elif execution.error_message:
                # 如果没有详细错误信息，使用简单格式
                errors.append({
                    'message': execution.error_message,
                    'details': ''
                })

            # 记录运行操作
            log_operation('run', 'test_case', test_case.id, test_case.name, request.user)

            healed_steps = [
                {
                    'step_number': s.get('step_number'),
                    'description': s.get('description') or '',
                    'healing_reason': s.get('healing_reason') or '',
                    'healed_locator': s.get('healed_locator'),
                }
                for s in step_results
                if s.get('healed')
            ]
            passed_with_heal = execution.status == 'passed' and len(healed_steps) > 0

            return Response({
                'success': execution.status == 'passed',
                'logs': execution.execution_logs,
                'screenshots': screenshots,
                'execution_time': execution.execution_time,
                'errors': errors,
                'healed': passed_with_heal,
                'ai_healing': {
                    'used': len(healed_steps) > 0,
                    'passed_with_heal': passed_with_heal,
                    'steps': healed_steps,
                },
            })

        except Exception as e:
            logger.error(f"执行测试用例失败: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'logs': f"执行失败: {str(e)}\n\n{traceback.format_exc()}",
                'screenshots': [],
                'execution_time': 0,
                'errors': [{'message': str(e), 'stack': traceback.format_exc()}]
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'])
    def batch_run(self, request):
        """批量运行测试用例"""
        test_case_ids = request.data.get('test_case_ids', [])
        project_id = request.data.get('project_id')

        if not test_case_ids:
            return Response({'error': '请选择要运行的测试用例'}, status=status.HTTP_400_BAD_REQUEST)

        results = []
        for test_case_id in test_case_ids:
            try:
                test_case = TestCase.objects.get(id=test_case_id)
                # 这里调用单个运行逻辑
                # 简化处理，实际应该异步执行
                results.append({
                    'test_case_id': test_case_id,
                    'test_case_name': test_case.name,
                    'status': 'passed'
                })
            except TestCase.DoesNotExist:
                results.append({
                    'test_case_id': test_case_id,
                    'test_case_name': '未知',
                    'status': 'error',
                    'error': '测试用例不存在'
                })

        return Response({'results': results})

    def perform_destroy(self, instance):
        # 记录操作（在删除前记录）
        log_operation('delete', 'test_case', instance.id, instance.name, self.request.user)
        instance.delete()


class TestCaseStepViewSet(viewsets.ModelViewSet):
    """测试用例步骤视图集"""
    queryset = TestCaseStep.objects.all()
    serializer_class = TestCaseStepSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['step_number']
    ordering = ['step_number']
    filterset_fields = ['test_case', 'action_type']

    def get_queryset(self):
        # 只显示用户有权限访问的测试用例的步骤
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        accessible_test_cases = TestCase.objects.filter(project__in=accessible_projects)
        return TestCaseStep.objects.filter(test_case__in=accessible_projects)


class TestCaseExecutionViewSet(viewsets.ModelViewSet):
    """测试用例执行记录视图集"""
    queryset = TestCaseExecution.objects.all().select_related(
        'test_case', 'project', 'test_suite', 'executed_by'
    )
    serializer_class = TestCaseExecutionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['test_case__name', 'error_message']
    ordering_fields = ['created_at', 'started_at', 'finished_at', 'status']
    ordering = ['-created_at']
    filterset_fields = ['project', 'test_suite', 'test_case', 'status', 'execution_source']
    pagination_class = StandardPagination

    def get_queryset(self):
        # 只显示用户有权限访问的项目的执行记录
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return TestCaseExecution.objects.filter(
            project__in=accessible_projects
        ).select_related(
            'test_case', 'project', 'test_suite', 'created_by'
        )

    def perform_destroy(self, instance):
        # 记录操作
        name = instance.test_case.name if instance.test_case else f"执行记录#{instance.id}"
        log_operation('delete', 'report', instance.id, name, self.request.user)
        instance.delete()

    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        """批量删除执行记录"""
        try:
            ids = request.data.get('ids', [])

            # 验证ids参数
            if not ids:
                return Response({'error': '未提供要删除的记录ID'}, status=status.HTTP_400_BAD_REQUEST)

            # 确保ids是列表
            if not isinstance(ids, list):
                return Response({'error': 'ids参数格式错误，应为数组'}, status=status.HTTP_400_BAD_REQUEST)

            # 确保只能删除有权限的记录
            queryset = self.get_queryset()
            records_to_delete = queryset.filter(id__in=ids)

            # 检查是否有记录可删除
            if not records_to_delete.exists():
                return Response({'error': '未找到可删除的记录或没有权限删除'}, status=status.HTTP_404_NOT_FOUND)

            # 获取可删除记录的ID列表，避免对带select_related的queryset调用delete()可能出现的问题
            deletable_ids = list(records_to_delete.values_list('id', flat=True))

            # 使用ID列表直接删除
            deleted_count = TestCaseExecution.objects.filter(id__in=deletable_ids).delete()[0]

            return Response({'message': f'成功删除 {deleted_count} 条记录', 'deleted_count': deleted_count})
        except Exception as e:
            logger.error(f"批量删除测试用例执行记录失败: {str(e)}", exc_info=True)
            return Response({'error': f'批量删除失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OperationRecordViewSet(viewsets.ReadOnlyModelViewSet):
    """操作记录视图集（只读）"""
    queryset = OperationRecord.objects.all()
    serializer_class = OperationRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['operation_type', 'resource_type', 'user']

    def get_queryset(self):
        # 返回最近的操作记录，按创建时间倒序
        # 过滤掉AI智能模式相关的操作记录
        queryset = OperationRecord.objects.exclude(
            resource_type__in=['ai_case', 'ai_execution']
        ).order_by('-created_at')

        # 支持通过查询参数限制返回数量
        limit = self.request.query_params.get('limit', None)
        if limit:
            try:
                limit = int(limit)
                queryset = queryset[:limit]
            except ValueError:
                pass

        return queryset


# ==================== 定时任务和通知相关视图 ====================

class UiScheduledTaskViewSet(viewsets.ModelViewSet):
    """UI定时任务视图集"""
    queryset = UiScheduledTask.objects.all()
    serializer_class = UiScheduledTaskSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['task_type', 'status', 'trigger_type', 'project']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'next_run_time', 'last_run_time']
    ordering = ['-created_at']

    def get_queryset(self):
        """只显示用户有权限访问的项目的定时任务"""
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return UiScheduledTask.objects.filter(project__in=accessible_projects)

    def perform_create(self, serializer):
        """创建定时任务"""
        instance = serializer.save(created_by=self.request.user)
        log_operation('create', 'scheduled_task', instance.id, instance.name, self.request.user)

    def perform_update(self, serializer):
        """更新定时任务"""
        instance = serializer.save()
        log_operation('edit', 'scheduled_task', instance.id, instance.name, self.request.user)

    def perform_destroy(self, instance):
        """删除定时任务"""
        log_operation('delete', 'scheduled_task', instance.id, instance.name, self.request.user)
        instance.delete()

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """暂停定时任务"""
        task = self.get_object()
        task.status = 'PAUSED'
        task.save()
        return Response({'message': '任务已暂停', 'status': task.status})

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """恢复定时任务"""
        task = self.get_object()
        task.status = 'ACTIVE'
        task.next_run_time = task.calculate_next_run()
        task.save()
        return Response({'message': '任务已恢复', 'status': task.status})

    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """立即运行任务"""
        task = self.get_object()

        try:
            # 更新任务执行时间和次数
            task.last_run_time = timezone.now()
            task.total_runs += 1
            # 重新计算下次运行时间
            task.next_run_time = task.calculate_next_run()
            task.save()

            # 根据任务类型执行不同的逻辑
            if task.task_type == 'TEST_SUITE':
                # 执行测试套件
                if not task.test_suite:
                    return Response({
                        'error': '该任务未配置测试套件'
                    }, status=status.HTTP_400_BAD_REQUEST)

                test_suite = task.test_suite
                test_case_count = test_suite.suite_test_cases.count()

                if test_case_count == 0:
                    return Response({
                        'error': '该测试套件未包含任何测试用例，无法执行'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 更新套件执行状态
                test_suite.execution_status = 'running'
                test_suite.save()

                # 在后台线程中执行测试
                import threading
                from .test_executor import TestExecutor

                def run_test():
                    try:
                        executor = TestExecutor(
                            test_suite=test_suite,
                            engine=task.engine,
                            browser=task.browser,
                            headless=task.headless,
                            executed_by=task.created_by
                        )
                        executor.run()

                        # 更新任务执行结果
                        task.successful_runs += 1
                        task.last_result = {'status': 'success', 'message': '测试套件执行成功'}
                        task.error_message = ''
                        task.save()

                        # 发送成功通知
                        self._send_task_notification(task, success=True)

                    except Exception as e:
                        task.failed_runs += 1
                        task.last_result = {'status': 'failed', 'message': str(e)}
                        task.error_message = str(e)
                        test_suite.execution_status = 'failed'
                        test_suite.save()
                        task.save()

                        # 发送失败通知
                        self._send_task_notification(task, success=False)

                # 启动后台线程执行测试
                thread = threading.Thread(target=run_test)
                thread.daemon = True
                thread.start()

                log_operation('run', 'scheduled_task', task.id, task.name, request.user)

                return Response({
                    'message': '测试套件开始执行',
                    'task_id': task.id,
                    'task_name': task.name,
                    'test_suite': test_suite.name,
                    'test_case_count': test_case_count,
                    'engine': task.engine,
                    'browser': task.browser,
                    'headless': task.headless
                }, status=status.HTTP_200_OK)

            elif task.task_type == 'TEST_CASE':
                # 执行测试用例
                if not task.test_cases or len(task.test_cases) == 0:
                    return Response({
                        'error': '该任务未配置测试用例'
                    }, status=status.HTTP_400_BAD_REQUEST)

                test_case_ids = task.test_cases
                test_cases = TestCase.objects.filter(id__in=test_case_ids)
                test_case_count = test_cases.count()

                if test_case_count == 0:
                    return Response({
                        'error': '找不到配置的测试用例'
                    }, status=status.HTTP_400_BAD_REQUEST)

                # 在后台线程中执行测试用例
                import threading

                def run_test_cases():
                    """在后台线程中执行测试用例"""
                    success_count = 0
                    failed_count = 0

                    try:
                        for test_case in test_cases:
                            # 创建执行记录
                            execution = TestCaseExecution.objects.create(
                                test_case=test_case,
                                project=task.project,
                                execution_source='scheduled',
                                status='running',
                                engine=task.engine,
                                browser=task.browser,
                                headless=task.headless,
                                created_by=task.created_by,
                                started_at=timezone.now()
                            )

                            # 实际执行测试用例
                            try:
                                logger.info(f"开始执行定时任务的测试用例: {test_case.name} (ID: {test_case.id})")

                                start_time = time.time()

                                # 获取测试用例的所有步骤
                                test_steps = list(test_case.steps.all().order_by('step_number'))

                                # 预先获取所有步骤的数据
                                steps_data = []
                                for step in test_steps:
                                    step_data = {
                                        'step': step,
                                        'action_type': step.action_type,
                                        'description': step.description,
                                        'input_value': step.input_value,
                                        'wait_time': step.wait_time,
                                        'assert_type': step.assert_type,
                                        'assert_value': step.assert_value,
                                    }

                                    if step.element:
                                        step_data['element_data'] = {
                                            'locator_strategy': step.element.locator_strategy.name if step.element.locator_strategy else 'css',
                                            'locator_value': step.element.locator_value,
                                            'name': step.element.name,
                                            'description': getattr(step.element, 'description', '') or '',
                                            'element_type': getattr(step.element, 'element_type', '') or '',
                                            'wait_timeout': step.element.wait_timeout,
                                            'force_action': step.element.force_action,
                                            'backup_locators': step.element.backup_locators or [],
                                        }
                                    else:
                                        step_data['element_data'] = None

                                    steps_data.append(step_data)

                                # 存储步骤执行结果和截图
                                step_results = []
                                screenshots = []
                                execution_logs = []
                                execution_result = {'status': 'passed', 'error_message': None}

                                # 根据引擎类型执行
                                if task.engine == 'selenium':
                                    from .selenium_engine import SeleniumTestEngine

                                    # 检查浏览器是否可用
                                    is_available, error_msg = SeleniumTestEngine.check_browser_available(task.browser)
                                    if not is_available:
                                        execution.status = 'failed'
                                        execution.error_message = error_msg
                                        execution.execution_logs = json.dumps([{
                                            'step_number': 0,
                                            'action_type': '浏览器检查',
                                            'description': '执行前浏览器环境检查',
                                            'success': False,
                                            'error': error_msg
                                        }], ensure_ascii=False)
                                        execution.finished_at = timezone.now()
                                        execution.save()
                                        failed_count += 1
                                        continue

                                    # 创建Selenium引擎实例并执行
                                    engine = SeleniumTestEngine(browser_type=task.browser, headless=task.headless)

                                    try:
                                        # 启动浏览器
                                        engine.start()
                                        execution_logs.append("✓ 浏览器启动成功")

                                        # 导航到项目环境基础URL
                                        from .codegen_service import codegen_recorder
                                        case_base_url = codegen_recorder._resolve_project_base_url(
                                            getattr(test_case, 'project_id', None)
                                        )
                                        if case_base_url:
                                            success, nav_log = engine.navigate(case_base_url)
                                            execution_logs.append(nav_log)
                                            if not success:
                                                execution_result['status'] = 'failed'
                                                execution_result['error_message'] = f"导航到测试页面失败: {nav_log}"
                                                raise Exception(nav_log)

                                        # 执行测试步骤
                                        for i, step_info in enumerate(steps_data, 1):
                                            step = step_info['step']
                                            action_type = step_info['action_type']
                                            element_data = step_info['element_data']

                                            success, step_log, screenshot_base64 = engine.execute_step(step,
                                                                                                       element_data or {})

                                            step_results.append({
                                                'step_number': i,
                                                'action_type': action_type,
                                                'description': step_info['description'] or '',
                                                'success': success,
                                                'error': None if success else step_log
                                            })

                                            if not success:
                                                execution_result['status'] = 'failed'
                                                execution_result['error_message'] = step_log

                                                if not screenshot_base64:
                                                    screenshot_base64 = engine.capture_screenshot()

                                                if screenshot_base64:
                                                    screenshots.append({
                                                        'url': screenshot_base64,
                                                        'description': f'步骤 {i} 失败截图',
                                                        'step_number': i,
                                                        'timestamp': timezone.now().isoformat()
                                                    })

                                                break

                                            if action_type == 'screenshot' and screenshot_base64:
                                                screenshots.append({
                                                    'url': screenshot_base64,
                                                    'description': f'步骤 {i}: {step_info["description"] or "手动截图"}',
                                                    'step_number': i,
                                                    'timestamp': timezone.now().isoformat()
                                                })

                                    finally:
                                        engine.stop()

                                else:  # Playwright
                                    import asyncio
                                    from asgiref.sync import sync_to_async
                                    from .playwright_engine import PlaywrightTestEngine

                                    async def run_playwright_test():
                                        browser_map = {
                                            'chrome': 'chromium',
                                            'firefox': 'firefox',
                                            'safari': 'webkit'
                                        }
                                        browser_type = browser_map.get(task.browser, 'chromium')

                                        engine = PlaywrightTestEngine(browser_type=browser_type, headless=task.headless)

                                        try:
                                            # 启动浏览器
                                            await engine.start()
                                            execution_logs.append("✓ 浏览器启动成功")

                                            # 获取项目环境基础URL（同步操作）
                                            from .codegen_service import codegen_recorder
                                            base_url = await sync_to_async(
                                                lambda: codegen_recorder._resolve_project_base_url(
                                                    getattr(test_case, 'project_id', None)
                                                )
                                            )()

                                            # 导航到项目环境基础URL
                                            if base_url:
                                                success, nav_log = await engine.navigate(base_url)
                                                execution_logs.append(nav_log)
                                                if not success:
                                                    execution_result['status'] = 'failed'
                                                    execution_result['error_message'] = f"导航到测试页面失败: {nav_log}"
                                                    detailed_errors.append({
                                                        'step_number': None,
                                                        'action_type': '导航',
                                                        'element': '',
                                                        'message': '导航到测试页面失败',
                                                        'details': nav_log,
                                                        'description': f'导航到 {base_url} 失败'
                                                    })
                                                    return False

                                            # 执行测试步骤
                                            for i, step_info in enumerate(steps_data, 1):
                                                step = step_info['step']
                                                action_type = step_info['action_type']
                                                element_data = step_info['element_data']

                                                success, step_log, screenshot_base64 = await engine.execute_step(step,
                                                                                                                 element_data or {})

                                                healed = bool(element_data and element_data.get('_healed'))
                                                healing_reason = (
                                                    (element_data or {}).get('_healing_reason') if element_data else None
                                                )
                                                healed_locator = (
                                                    (element_data or {}).get('_healed_locator') if element_data else None
                                                )
                                                if healed and success:
                                                    from .playwright_engine import PlaywrightTestEngine as _PTE
                                                    step_log = _PTE.append_heal_note(step_log, element_data)

                                                step_results.append({
                                                    'step_number': i,
                                                    'action_type': action_type,
                                                    'description': step_info['description'] or '',
                                                    'success': success,
                                                    'error': None if success else step_log,
                                                    'healed': healed and success,
                                                    'healing_reason': healing_reason if (healed and success) else None,
                                                    'healed_locator': healed_locator if (healed and success) else None,
                                                })

                                                if not success:
                                                    execution_result['status'] = 'failed'
                                                    execution_result['error_message'] = step_log

                                                    if not screenshot_base64:
                                                        screenshot_base64 = await engine.capture_screenshot()

                                                    if screenshot_base64:
                                                        screenshots.append({
                                                            'url': screenshot_base64,
                                                            'description': f'步骤 {i} 失败截图',
                                                            'step_number': i,
                                                            'timestamp': timezone.now().isoformat()
                                                        })

                                                    return False

                                                if action_type == 'screenshot' and screenshot_base64:
                                                    screenshots.append({
                                                        'url': screenshot_base64,
                                                        'description': f'步骤 {i}: {step_info["description"] or "手动截图"}',
                                                        'step_number': i,
                                                        'timestamp': timezone.now().isoformat()
                                                    })

                                            return True

                                        finally:
                                            await engine.stop()

                                    # 在新的事件循环中运行Playwright测试
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    try:
                                        loop.run_until_complete(run_playwright_test())
                                    finally:
                                        loop.close()

                                # 计算执行时间
                                total_time = round(time.time() - start_time, 2)

                                # 保存执行结果
                                execution.status = execution_result['status']
                                execution.error_message = execution_result['error_message'] or ''
                                execution.execution_logs = json.dumps(step_results, ensure_ascii=False)
                                execution.execution_time = total_time
                                execution.screenshots = screenshots
                                execution.finished_at = timezone.now()
                                execution.save()

                                if execution.status == 'passed':
                                    success_count += 1
                                    logger.info(f"测试用例 {test_case.name} 执行成功")
                                else:
                                    failed_count += 1
                                    logger.warning(f"测试用例 {test_case.name} 执行失败: {execution.error_message}")

                            except Exception as e:
                                logger.error(f"执行测试用例 {test_case.name} 时发生异常: {str(e)}")
                                execution.status = 'failed'
                                execution.error_message = str(e)
                                execution.finished_at = timezone.now()
                                execution.save()
                                failed_count += 1

                        # 更新任务执行结果
                        if failed_count == 0:
                            task.successful_runs += 1
                            task.last_result = {
                                'status': 'success',
                                'message': f'执行完成: {success_count}个成功',
                                'success_count': success_count,
                                'failed_count': failed_count
                            }
                            task.error_message = ''
                            task.save()

                            # 发送成功通知
                            self._send_task_notification(task, success=True)
                        else:
                            task.failed_runs += 1
                            task.last_result = {
                                'status': 'partial',
                                'message': f'执行完成: {success_count}个成功, {failed_count}个失败',
                                'success_count': success_count,
                                'failed_count': failed_count
                            }
                            task.error_message = f'{failed_count}个测试用例执行失败'
                            task.save()

                            # 发送失败通知
                            self._send_task_notification(task, success=False)

                    except Exception as e:
                        logger.error(f"执行定时任务测试用例时发生异常: {str(e)}")
                        task.failed_runs += 1
                        task.last_result = {'status': 'failed', 'message': str(e)}
                        task.error_message = str(e)
                        task.save()

                        # 发送失败通知
                        self._send_task_notification(task, success=False)

                # 启动后台线程执行测试
                thread = threading.Thread(target=run_test_cases)
                thread.daemon = True
                thread.start()

                log_operation('run', 'scheduled_task', task.id, task.name, request.user)

                return Response({
                    'message': '测试用例开始执行',
                    'task_id': task.id,
                    'task_name': task.name,
                    'test_case_count': test_case_count,
                    'engine': task.engine,
                    'browser': task.browser,
                    'headless': task.headless
                }, status=status.HTTP_200_OK)

            else:
                return Response({
                    'error': '不支持的任务类型'
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f'执行定时任务失败: {str(e)}')
            return Response({
                'error': f'执行失败: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _send_task_notification(self, task, success):
        """发送任务执行通知"""
        try:
            logger.info(f"准备发送任务 {task.id} 的通知，执行结果: {'成功' if success else '失败'}")

            # 检查是否需要发送通知
            if success and not task.notify_on_success:
                logger.info("任务执行成功但未启用成功通知")
                return

            if not success and not task.notify_on_failure:
                logger.info("任务执行失败但未启用失败通知")
                return

            # 检查通知类型
            if not task.notification_type:
                logger.info("未设置通知类型")
                return

            logger.info(f"通知类型: {task.notification_type}")

            # 根据通知类型发送不同的通知
            if task.notification_type in ['webhook', 'both']:
                logger.info("发送Webhook通知")
                self._send_webhook_notification(task, success)

            if task.notification_type in ['email', 'both']:
                logger.info("发送邮件通知")
                self._send_email_notification(task, success)

        except Exception as e:
            logger.error(f"发送通知失败: {str(e)}", exc_info=True)

    def _send_webhook_notification(self, task, success):
        """发送Webhook通知"""
        try:
            import requests
            import json

            logger.info("=== 开始发送Webhook通知 ===")

            # 使用统一的通知配置
            try:
                from apps.core.models import UnifiedNotificationConfig
                all_webhook_configs = UnifiedNotificationConfig.objects.filter(
                    config_type__in=['webhook_wechat', 'webhook_feishu', 'webhook_dingtalk'],
                    is_active=True
                )
                logger.info("使用统一通知配置 (UnifiedNotificationConfig)")
            except ImportError as e:
                # 如果 core 模块不可用，记录错误并返回
                logger.error(f"无法导入统一通知配置: {e}")
                logger.warning("通知发送失败：无法找到通知配置模块")
                return
            except Exception as e:
                logger.error(f"获取通知配置时出错: {e}")
                return

            all_webhook_bots = []
            for config in all_webhook_configs:
                bots = config.get_webhook_bots()
                if bots:
                    for bot in bots:
                        # 只添加启用了"UI自动化测试"的机器人
                        if bot.get('enabled', True) and bot.get('enable_ui_automation', True):
                            all_webhook_bots.append(bot)
                            logger.info(f"添加机器人: {bot.get('name')} (UI自动化测试已启用)")
                        elif bot.get('enabled', True):
                            logger.info(f"配置中心机器人 {bot.get('name')} 未启用UI自动化测试，跳过")

            if not all_webhook_bots:
                logger.warning("没有找到任何启用的webhook机器人配置")
                return

            logger.info(f"找到 {len(all_webhook_bots)} 个启用的webhook机器人配置")

            # 准备通知内容
            status_text = '成功' if success else '失败'
            task_type_text = '测试套件执行' if task.task_type == 'TEST_SUITE' else '测试用例执行'

            # 获取最后执行结果的详细信息
            last_result = task.last_result or {}
            result_message = last_result.get('message', '')
            success_count = last_result.get('success_count', 0)
            failed_count = last_result.get('failed_count', 0)

            # 为不同的机器人平台准备消息格式
            for bot in all_webhook_bots:
                if not bot.get('enabled', True) or not bot.get('webhook_url'):
                    logger.info(f"跳过未启用或无URL的机器人: {bot.get('name', 'Unknown')}")
                    continue

                bot_type = bot.get('type', 'unknown')
                webhook_url = bot['webhook_url']
                logger.info(f"发送通知到 {bot_type} 机器人: {bot.get('name', 'Unknown')}")

                # 构造详细内容
                # 转换执行时间到本地时区
                local_run_time = timezone.localtime(task.last_run_time).strftime(
                    '%Y-%m-%d %H:%M:%S') if task.last_run_time else '未知'
                detail_content = f"""任务名称: {task.name}

执行状态: {status_text}

执行时间: {local_run_time}

任务类型: {task_type_text}

执行引擎: {task.engine.upper()}

浏览器: {task.browser.capitalize()}"""

                if result_message:
                    detail_content += f"\n\n执行结果: {result_message}"

                if success_count > 0 or failed_count > 0:
                    detail_content += f"\n\n成功: {success_count} 个，失败: {failed_count} 个"

                # 根据机器人类型构造消息格式
                if bot_type == 'wechat':  # 企业微信
                    message_data = {
                        "msgtype": "markdown",
                        "markdown": {
                            "content": f"""**UI自动化定时任务执行{status_text}**

{detail_content}"""
                        }
                    }
                elif bot_type == 'feishu':  # 飞书
                    message_data = {
                        "msg_type": "interactive",
                        "card": {
                            "elements": [{
                                "tag": "div",
                                "text": {
                                    "content": f"**UI自动化定时任务执行{status_text}**\n\n{detail_content}",
                                    "tag": "lark_md"
                                }
                            }],
                            "header": {
                                "title": {
                                    "content": f"UI自动化定时任务执行{status_text}",
                                    "tag": "plain_text"
                                },
                                "template": "green" if success else "red"
                            }
                        }
                    }
                elif bot_type == 'dingtalk':  # 钉钉
                    message_data = {
                        "msgtype": "markdown",
                        "markdown": {
                            "title": f"UI自动化定时任务执行{status_text}",
                            "text": f"""**UI自动化定时任务执行{status_text}**

{detail_content}"""
                        }
                    }

                    # 钉钉机器人签名验证
                    secret = bot.get('secret')
                    if secret:
                        import time
                        import hmac
                        import hashlib
                        import base64
                        import urllib.parse

                        timestamp = str(round(time.time() * 1000))
                        string_to_sign = f'{timestamp}\n{secret}'
                        string_to_sign_enc = string_to_sign.encode('utf-8')
                        secret_enc = secret.encode('utf-8')
                        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
                        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))

                        # 在URL中添加签名参数
                        if '?' in webhook_url:
                            webhook_url += f'&timestamp={timestamp}&sign={sign}'
                        else:
                            webhook_url += f'?timestamp={timestamp}&sign={sign}'
                else:
                    logger.warning(f"未知的机器人类型: {bot_type}")
                    continue

                # 发送webhook请求
                try:
                    logger.info(f"发送请求到: {webhook_url}")
                    logger.info(f"消息数据: {json.dumps(message_data, ensure_ascii=False, indent=2)}")

                    response = requests.post(
                        webhook_url,
                        json=message_data,
                        headers={'Content-Type': 'application/json'},
                        timeout=10
                    )

                    logger.info(f"响应状态码: {response.status_code}")
                    logger.info(f"响应内容: {response.text}")

                    if response.status_code == 200:
                        logger.info(f"成功发送通知到 {bot.get('name', 'Unknown')}")

                        # 记录通知日志
                        UiNotificationLog.objects.create(
                            task=task,
                            task_name=task.name,
                            task_type=task.task_type,
                            notification_type='task_execution',
                            sender_name='系统Webhook通知',
                            sender_email='system@notification.com',
                            recipient_info=[{'name': bot.get('name', 'Unknown'), 'webhook_url': webhook_url}],
                            webhook_bot_info=bot,
                            notification_content=json.dumps(message_data, ensure_ascii=False),
                            status='success',
                            response_info={'status_code': response.status_code, 'response': response.text},
                            sent_at=timezone.now()
                        )
                    else:
                        logger.error(f"发送通知失败，状态码: {response.status_code}, 响应: {response.text}")

                        # 记录失败日志
                        UiNotificationLog.objects.create(
                            task=task,
                            task_name=task.name,
                            task_type=task.task_type,
                            notification_type='task_execution',
                            sender_name='系统Webhook通知',
                            sender_email='system@notification.com',
                            recipient_info=[{'name': bot.get('name', 'Unknown'), 'webhook_url': webhook_url}],
                            webhook_bot_info=bot,
                            notification_content=json.dumps(message_data, ensure_ascii=False),
                            status='failed',
                            error_message=f'HTTP {response.status_code}: {response.text}',
                            response_info={'status_code': response.status_code, 'response': response.text}
                        )

                except requests.exceptions.RequestException as e:
                    logger.error(f"发送webhook请求失败: {str(e)}")

                    # 记录失败日志
                    UiNotificationLog.objects.create(
                        task=task,
                        task_name=task.name,
                        task_type=task.task_type,
                        notification_type='task_execution',
                        sender_name='系统Webhook通知',
                        sender_email='system@notification.com',
                        recipient_info=[{'name': bot.get('name', 'Unknown'), 'webhook_url': webhook_url}],
                        webhook_bot_info=bot,
                        notification_content=json.dumps(message_data, ensure_ascii=False),
                        status='failed',
                        error_message=str(e)
                    )

        except Exception as e:
            logger.error(f"发送Webhook通知失败: {str(e)}", exc_info=True)

    def _send_email_notification(self, task, success):
        """发送邮件通知"""
        try:
            from django.core.mail import send_mail
            from django.conf import settings

            logger.info("=== 开始发送邮件通知 ===")

            # 获取收件人列表
            recipients = []
            if task.notify_emails:
                if isinstance(task.notify_emails, list):
                    recipients = task.notify_emails
                else:
                    recipients = [task.notify_emails]

            if not recipients:
                logger.warning("没有找到任何邮件收件人")
                return

            # 准备邮件内容
            status_text = '成功' if success else '失败'
            task_type_text = '测试套件执行' if task.task_type == 'TEST_SUITE' else '测试用例执行'

            subject = f"UI自动化定时任务执行{status_text}: {task.name}"

            last_result = task.last_result or {}
            result_message = last_result.get('message', '')

            # 转换执行时间到本地时区
            local_run_time = timezone.localtime(task.last_run_time).strftime(
                '%Y-%m-%d %H:%M:%S') if task.last_run_time else '未知'

            message = f"""
任务名称: {task.name}
执行状态: {status_text}
执行时间: {local_run_time}
任务类型: {task_type_text}
执行引擎: {task.engine.upper()}
浏览器: {task.browser.capitalize()}

执行结果:
{result_message if result_message else '无详细信息'}

错误信息:
{task.error_message if task.error_message else '无错误信息'}
            """

            # 发送邮件
            from_email = settings.DEFAULT_FROM_EMAIL
            logger.info(f"准备发送邮件，发件人: {from_email}, 收件人: {recipients}")

            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=recipients,
                fail_silently=False,
            )
            logger.info("邮件发送成功")

            # 记录通知日志
            UiNotificationLog.objects.create(
                task=task,
                task_name=task.name,
                task_type=task.task_type,
                notification_type='task_execution',
                sender_name='系统邮件通知',
                sender_email=from_email,
                recipient_info=[{'email': email} for email in recipients],
                notification_content=message,
                status='success',
                sent_at=timezone.now()
            )

        except Exception as e:
            logger.error(f"发送邮件通知失败: {str(e)}", exc_info=True)

            # 记录失败日志
            try:
                UiNotificationLog.objects.create(
                    task=task,
                    task_name=task.name,
                    task_type=task.task_type,
                    notification_type='task_execution',
                    sender_name='系统邮件通知',
                    sender_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_info=[{'email': email} for email in recipients] if recipients else [],
                    notification_content=f"发送邮件通知失败: {str(e)}",
                    status='failed',
                    error_message=str(e)
                )
            except:
                pass


class UiNotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """UI通知日志视图集（只读）"""
    queryset = UiNotificationLog.objects.all()
    serializer_class = UiNotificationLogSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'notification_type']
    search_fields = ['task_name', 'notification_content']
    ordering_fields = ['created_at', 'sent_at']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'])
    def retry(self, request, pk=None):
        """重试发送通知"""
        log = self.get_object()
        if log.status == 'failed':
            # 这里应该触发实际的重试逻辑
            log.retry_count += 1
            log.is_retried = True
            log.save()
            return Response({'message': '通知已加入重试队列'})
        return Response({'error': '只能重试失败的通知'}, status=status.HTTP_400_BAD_REQUEST)


class UiTaskNotificationSettingViewSet(viewsets.ModelViewSet):
    """UI任务通知设置视图集"""
    queryset = UiTaskNotificationSetting.objects.all()
    serializer_class = UiTaskNotificationSettingSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['task', 'is_enabled', 'notification_type']


class AICaseViewSet(viewsets.ModelViewSet):
    queryset = AICase.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = AICaseSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project']
    search_fields = ['name', 'description', 'task_description']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        # 返回用户有权限的项目下的AI用例，以及没有关联项目的AI用例
        return AICase.objects.filter(
            models.Q(project__in=accessible_projects) | models.Q(project__isnull=True)
        ).distinct()

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        instance = serializer.save()

    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """执行 AI 用例"""
        ai_case = self.get_object()

        # 创建执行记录
        execution_record = AIExecutionRecord.objects.create(
            project=ai_case.project,
            ai_case=ai_case,
            case_name=ai_case.name,
            task_description=ai_case.task_description,
            status='running',
            executed_by=request.user,
            logs="正在分析任务...\n"
        )

        # 异步执行
        import threading
        import os
        from asgiref.sync import sync_to_async
        from django.db import connection, DatabaseError
        from .ai_agent import run_full_process_sync

        def run_task():
            # 注册停止信号
            STOP_SIGNALS[execution_record.id] = False

            # 关键修复：关闭旧连接，避免子线程共享主线程的连接
            try:
                connection.close()
            except:
                pass

            # 设置环境变量，允许在后台线程中使用同步 ORM
            os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

            def safe_save(record, update_fields=None, max_retries=3):
                """安全的保存方法，带有重试机制"""
                for attempt in range(max_retries):
                    try:
                        record.save(update_fields=update_fields)
                        return True
                    except (DatabaseError, Exception) as e:
                        error_str = str(e)
                        # 检查是否是MySQL连接错误
                        if '2006' in error_str or 'MySQL server has gone away' in error_str or '0' == error_str:
                            if attempt < max_retries - 1:
                                logger.warning(f"数据库连接失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                                # 关闭旧连接并重试
                                try:
                                    connection.close()
                                except:
                                    pass
                                import time
                                time.sleep(0.5)  # 等待一下再重试
                                continue
                            else:
                                logger.error(f"数据库保存失败，已达最大重试次数: {e}")
                                raise
                        else:
                            # 其他错误直接抛出
                            logger.error(f"数据库保存失败: {e}")
                            raise
                return False

            try:
                def should_stop():
                    return STOP_SIGNALS.get(execution_record.id, False)

                async def on_analysis_complete(planned_tasks):
                    execution_record.planned_tasks = planned_tasks
                    execution_record.logs += "任务分析完成，开始执行...\n"
                    await sync_to_async(safe_save)(execution_record, update_fields=['planned_tasks', 'logs'])

                async def on_step_update(step_info):
                    try:
                        # 处理日志
                        if step_info.get('type') == 'log':
                            content = step_info.get('content')
                            if content:
                                execution_record.logs += content
                                await sync_to_async(safe_save)(execution_record, update_fields=['logs'])
                            return

                        # 处理任务状态
                        task_id = step_info.get('task_id')
                        status = step_info.get('status')
                        if task_id and status:
                            if str(status).strip().lower() == 'completed':
                                backfilled_ids = backfill_prior_pending_tasks(
                                    execution_record.planned_tasks,
                                    task_id
                                )
                                if backfilled_ids:
                                    execution_record.logs += (
                                        f"\n[System] 已补齐遗漏标记的前序子任务: "
                                        f"{', '.join(map(str, backfilled_ids))}"
                                    )
                            updated = update_planned_task_status(
                                execution_record.planned_tasks,
                                task_id,
                                status
                            )
                            if updated:
                                update_fields = ['planned_tasks']
                                if str(status).strip().lower() == 'completed' and 'backfilled_ids' in locals() and backfilled_ids:
                                    update_fields.append('logs')
                                await sync_to_async(safe_save)(execution_record, update_fields=update_fields)
                    except Exception as e:
                        logger.error(f"更新步骤状态失败: {e}")

                history = run_full_process_sync(
                    ai_case.task_description,
                    analysis_callback=on_analysis_complete,
                    step_callback=on_step_update,
                    should_stop=should_stop
                )

                # 检查是否是手动停止
                if should_stop():
                    execution_record.status = 'stopped'
                    execution_record.logs += "\n[System] 任务已由用户停止。"
                else:
                    # 补齐 AI 漏标的前序步骤（如合并输入账号+密码只 mark 了一次）
                    reconciled = reconcile_skipped_pending_tasks(execution_record.planned_tasks)
                    if reconciled:
                        execution_record.logs += (
                            f"\n[System] 结束前补齐漏标子任务: {', '.join(map(str, reconciled))}"
                        )
                    execution_record.status, task_summary = resolve_execution_status(execution_record.planned_tasks)
                    if execution_record.status == 'passed':
                        execution_record.logs += "\n执行完成。"
                    else:
                        execution_record.logs += "\n执行结束，但存在未完成或失败的子任务。"
                    logger.info(
                        "🏁 Task completion summary: "
                        f"{task_summary['completed']}/{task_summary['total']} completed, "
                        f"{task_summary['failed']} failed, "
                        f"{task_summary['pending'] + task_summary['in_progress']} pending"
                    )

                execution_record.end_time = timezone.now()
                execution_record.duration = (execution_record.end_time - execution_record.start_time).total_seconds()

                # 格式化 history 为日志 (如果不是停止状态)
                steps = []
                if history:
                    if hasattr(history, 'steps'):
                        steps = [extract_step_info(s, i) for i, s in enumerate(history.steps)]

                execution_record.steps_completed = steps

                # 任务状态完全由 AI 智能体显式标记，测试完成后不再调用统一标记，避免幻觉改写结果
                if execution_record.planned_tasks:
                    execution_record.logs = append_execution_summary(
                        execution_record.logs,
                        summarize_planned_tasks(execution_record.planned_tasks)
                    )

                # 处理GIF录制文件
                self._process_gif_recording(execution_record, history)

                safe_save(execution_record)

            except Exception as e:
                error_message = str(e)
                failed_task_id = None if is_infrastructure_failure(error_message) else mark_first_active_task(execution_record.planned_tasks, 'failed')
                execution_record.status = 'failed'
                execution_record.end_time = timezone.now()
                execution_record.duration = (execution_record.end_time - execution_record.start_time).total_seconds()
                if '执行预检失败' in error_message:
                    execution_record.logs += f"\n执行出错: {error_message}"
                elif 'Execution LLM unavailable' in error_message:
                    execution_record.logs += f"\n执行出错: AI 执行模型连接失败。{error_message}"
                else:
                    execution_record.logs += f"\n执行出错: {error_message}"
                if failed_task_id is not None:
                    execution_record.logs += f"\n[System] 子任务 {failed_task_id} 已自动标记为失败。"
                execution_record.logs = append_execution_summary(
                    execution_record.logs,
                    summarize_planned_tasks(execution_record.planned_tasks)
                )
                try:
                    safe_save(execution_record)
                except:
                    # 如果保存失败，至少尝试保存基本信息
                    logger.error(f"保存失败状态时出错: {e}")
                    pass
            finally:
                # 清理停止信号
                if execution_record.id in STOP_SIGNALS:
                    del STOP_SIGNALS[execution_record.id]

        thread = threading.Thread(target=run_task)
        thread.daemon = True
        thread.start()

        return Response({
            'message': 'AI 用例开始执行',
            'execution_id': execution_record.id
        })

    def _process_gif_recording(self, execution_record, history):
        """
        处理GIF录制文件
        在执行完成后查找生成的GIF文件并保存路径到数据库
        """
        try:
            import os
            from django.conf import settings
            from datetime import datetime

            # browser-use 默认生成的GIF文件名（固定为agent_history.gif）
            default_gif_path = os.path.join(os.getcwd(), 'agent_history.gif')

            # 如果找到GIF文件，移动到media/ai_recording目录并重命名
            if os.path.exists(default_gif_path):
                import shutil

                # 创建录制文件目录
                gif_dir = os.path.join(settings.MEDIA_ROOT, 'ai_recording')
                os.makedirs(gif_dir, exist_ok=True)

                # 生成新的文件名：用例名称+年月日时分秒
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                # 清理用例名称中的非法字符
                safe_case_name = "".join(
                    [c if c.isalnum() or c in (' ', '_', '-') else '_' for c in execution_record.case_name])
                new_gif_filename = f"{safe_case_name}_{timestamp}.gif"
                new_gif_path = os.path.join(gif_dir, new_gif_filename)

                # 移动并重命名文件
                shutil.move(default_gif_path, new_gif_path)

                # 保存相对路径到数据库（使用正斜杠，确保跨平台兼容）
                relative_path = f'media/ai_recording/{new_gif_filename}'
                execution_record.gif_path = relative_path

                logger.info(f"✅ GIF recording saved to: {relative_path}")
            else:
                logger.warning(f"⚠️ GIF file not found at: {default_gif_path}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to process GIF recording: {e}")


# 全局停止信号字典 {execution_id: bool}
STOP_SIGNALS = {}

TERMINAL_TASK_STATUSES = {'completed', 'failed', 'skipped'}
ACTIVE_TASK_STATUSES = {'pending', 'in_progress'}


def build_planned_tasks_from_cases(cases):
    """从上传解析的用例步骤构建 planned_tasks，与前端用例明细 1:1 对齐。

    跳过 LLM 重新拆分/合并，避免右侧划线与日志/投屏进度错位。
    """
    tasks = []
    if not isinstance(cases, list):
        return tasks
    for case in cases:
        if not isinstance(case, dict):
            continue
        steps = case.get('steps') or []
        if not steps:
            expected = (case.get('expected') or '').strip()
            name = (case.get('name') or '').strip() or f'用例{len(tasks) + 1}'
            steps = [f'预期结果：{expected}' if expected else name]
        for step in steps:
            desc = str(step).strip() if step is not None else ''
            if not desc:
                continue
            tasks.append({
                'id': len(tasks) + 1,
                'description': desc,
                'status': 'pending',
            })
    return tasks


def echo_steps_to_hub_testcase(hub_testcase_id, planned_tasks):
    """将 AI 智能测试执行产生的步骤回显到「用例详情 - UI自动化」页面。

    以规划任务（planned_tasks）为数据源（含 AI 执行过程中的状态），把已完成/失败
    的步骤写入主项目测试用例的 step_details（TestCaseStep），供用例详情 UI 自动化 tab 回显。
    返回写入的步骤数量。
    """
    from apps.testcases.models import TestCase, TestCaseStep as HubTestCaseStep

    if not hub_testcase_id or not planned_tasks:
        return 0

    try:
        testcase = TestCase.objects.get(pk=hub_testcase_id)
    except TestCase.DoesNotExist:
        return 0

    completed = []
    for task in planned_tasks:
        desc = str(task.get('description', '')).strip()
        if not desc:
            continue
        status = str(task.get('status', '') or '').strip().lower()
        # 执行过的步骤才回显（跳过 pending/in_progress 的未执行步骤）
        if status in ('completed', 'failed', 'skipped'):
            completed.append(desc)

    if not completed:
        return 0

    # 采用全量覆盖策略：先用旧步骤删除，再重建，保证与执行结果一致
    HubTestCaseStep.objects.filter(testcase=testcase).delete()
    created = []
    for i, desc in enumerate(completed, start=1):
        created.append(HubTestCaseStep(
            testcase=testcase,
            step_number=i,
            action=desc,
            expected='',
        ))
    HubTestCaseStep.objects.bulk_create(created)
    return len(created)


# ============================== AI 生成步骤 → 用例录制并双端同步 ==============================

def _dom_element_to_locator(el):
    """把 browser-use 交互相元素映射为可被 _parse_playwright_locator 解析的定位表达式。

    兼容 UI自动化「录制步骤 → 用例」的解析器，使 AI 生成步骤能以同样的格式进入元素库。
    """
    if el is None:
        return ''
    attrs = getattr(el, 'attributes', None) or {}
    node = (getattr(el, 'node_name', '') or '').lower()
    ax_name = getattr(el, 'ax_name', None) or ''
    xpath = getattr(el, 'x_path', '') or ''

    testid = attrs.get('data-testid') or attrs.get('data-test') or attrs.get('data-cy')
    if testid:
        return f'page.get_by_test_id("{testid}")'
    if attrs.get('id'):
        return f'page.locator("#{attrs.get("id")}")'
    if attrs.get('placeholder'):
        return f'page.get_by_placeholder("{attrs.get("placeholder")}")'
    if attrs.get('name'):
        return f'page.locator("[name={attrs.get("name")}]")'
    if attrs.get('aria-label'):
        return f'page.get_by_label("{attrs.get("aria-label")}")'
    if ax_name:
        return f'page.get_by_label("{ax_name}")'
    if attrs.get('role'):
        return f'page.get_by_role("{attrs.get("role")}")'
    if xpath:
        return f'page.locator("xpath={xpath}")'
    return node or ''


def _extract_ai_history_actions(history):
    """从 AI 执行历史提取 (action, interacted_element) 列表，供录制用例。

    过滤掉纯状态标记动作（mark_task_* / done 等），仅保留真实浏览器操作。
    """
    actions = []
    if not history:
        return actions
    model_actions = getattr(history, 'model_actions', None)
    if not callable(model_actions):
        logger.warning('_extract_ai_history_actions: history 类型 %s 无 model_actions()，无法录制', type(history).__name__)
        return actions
    try:
        items = model_actions()
    except Exception as e:
        logger.warning('_extract_ai_history_actions: 调用 model_actions() 失败: %s', e)
        return actions

    for item in items or []:
        if not isinstance(item, dict):
            continue
        el = item.get('interacted_element')
        acted = {k: v for k, v in item.items() if k != 'interacted_element'}
        if not acted:
            continue
        # 仅保留真实操作；标记类动作（mark_task_* / update_task_status / done）单独出现时跳过
        MARKER_ACTIONS = ('mark_task_complete', 'mark_task_failed', 'mark_task_skipped',
                          'update_task_status', 'done', 'structured_output')
        if all(k in MARKER_ACTIONS for k in acted):
            continue
        # 混合动作（真实操作+标记动作）时，剔除标记部分，仅保留真实操作
        real = {k: v for k, v in acted.items() if k not in MARKER_ACTIONS}
        actions.append({
            'action': real or acted,
            'interacted_element': el,
        })
    return actions


def _ai_actions_to_case_steps(project, user, actions, default_page='main'):
    """把 AI 执行历史上的操作+定位器转换为用例步骤(DTO 结构)，并同步创建元素。

    与 codegen_pipeline_service.map_parse_to_case_steps 产出结构保持一致。
    返回 (steps, created_element_ids)。
    """
    from .codegen_pipeline_service import (
        _get_or_create_element_from_locator,
        _element_step_extras,
        _build_step_description,
        _page_name_from_url,
    )

    mapped = []
    element_cache = {}
    created_ids = []
    current_page = default_page or 'main'

    def _action_key(action_dict):
        # browser-use 动作序列化形如 {click_element: {...}} 或 {go_to_url: {...}}
        for k, v in action_dict.items():
            if isinstance(v, dict) and v:
                return k
        for k, v in action_dict.items():
            if v not in ('', None):
                return k
        return next((k for k in action_dict if k), None)

    for item in actions:
        action_dict = item.get('action') or {}
        el = item.get('interacted_element')
        key = _action_key(action_dict)
        if not key:
            continue
        params = action_dict.get(key) or {}
        action_l = key.lower()

        # 导航：定位器无目标，直接记录 URL
        if action_l in ('go_to_url', 'navigate'):
            url = params.get('url', '') if isinstance(params, dict) else str(params)
            if url:
                current_page = _page_name_from_url(url) or current_page
            mapped.append({
                'action_type': 'navigateUrl',
                'page_filter': current_page,
                'element_id': None,
                'input_value': url,
                'wait_time': 1000,
                'assert_type': '',
                'assert_value': '',
                'description': _build_step_description(action='navigate', url=url)[:500],
                'raw': '',
                **_element_step_extras(None),
            })
            continue

        # 映射为 UI 用例步骤操作类型（select 映射为 fill，与现有录制步骤转换保持一致）
        # 兼容 browser-use 新旧版本动作名：
        #   新版: navigate/input/click/scroll/select_dropdown_option/extract/switch_tab/close_tab
        #   旧版: go_to_url/input_text/click_element/scroll_down|scroll_up/select_option/extract_content
        if action_l in ('input_text', 'input', 'fill'):
            ui_action = 'fill'
        elif action_l in ('click_element', 'click'):
            ui_action = 'click'
        elif action_l in ('select_option', 'select', 'select_dropdown', 'select_dropdown_option'):
            ui_action = 'fill'
        elif action_l in ('hover_element', 'hover'):
            ui_action = 'hover'
        elif action_l in ('scroll_down', 'scroll_up', 'scroll_to_text', 'scroll'):
            ui_action = 'scroll'
        elif action_l in ('extract_content', 'get_text', 'get_text_list', 'assert', 'extract', 'read_content'):
            ui_action = 'assert'
        elif action_l in ('switch_tab', 'open_new_tab', 'close_tab', 'new_tab'):
            ui_action = 'switchTab'
        else:
            # 无法映射的动作跳过
            continue

        locator = _dom_element_to_locator(el)
        input_value = ''
        if ui_action == 'fill':
            # 新版 select_dropdown_option 用 text 字段；input 用 text 字段
            input_value = params.get('text', '') if isinstance(params, dict) else str(params)

        # 创建/复用元素（与录制步骤一致：按定位器入库）
        element = None
        if locator and ui_action in ('click', 'fill', 'hover', 'scroll'):
            element, created = _get_or_create_element_from_locator(
                project=project,
                user=user,
                locator=locator,
                action=ui_action,
                page_name=current_page,
                cache=element_cache,
                idx=len(mapped),
            )
            if created and element:
                created_ids.append(element.id)

        desc = _build_step_description(
            action=ui_action,
            locator=locator,
            value=input_value,
            element_name=element.name if element else '',
            element_type=element.element_type if element else '',
        )[:500]

        mapped.append({
            'action_type': ui_action,
            'page_filter': current_page,
            'element_id': element.id if element else None,
            'input_value': input_value,
            'wait_time': 1000,
            'assert_type': '',
            'assert_value': '',
            'description': desc,
            'raw': '',
            **_element_step_extras(element),
        })

    return mapped, created_ids


def sync_ai_execution_to_cases(hub_testcase_id, execution_record, history):
    """「AI生成步骤」执行完成后，将执行中用到的操作+定位器 录制成用例并同步到两个页面：

    1. UI自动化测试模块「用例管理」列表（ui_test_cases / ui_test_case_steps / ui_elements）；
    2. 主项目「用例库」的 UI自动化页面（testcases，case_type 含 'ui'，并回显 step_details）。

    返回 (ui_testcase_id, hub_testcase_id)；无可录制操作时返回 (None, None)。
    """
    if not hub_testcase_id:
        logger.info('sync_ai_execution_to_cases: 无 hub_testcase_id，跳过')
        return None, None

    from apps.testcases.models import TestCase as HubTestCase
    from apps.testcases.models import TestCaseStep as HubTestCaseStep
    from .models import TestCase as UiTestCase, TestCaseStep as UiTestCaseStep

    try:
        hub_case = HubTestCase.objects.select_related('project').get(pk=hub_testcase_id)
    except HubTestCase.DoesNotExist:
        logger.info('sync_ai_execution_to_cases: 用例 #%s 不存在，跳过', hub_testcase_id)
        return None, None

    hub_project = hub_case.project
    user = execution_record.executed_by

    # 确保关联的 UI自动化 项目
    if not hub_project:
        logger.info('sync_ai_execution_to_cases: 用例 %s 无关联项目，跳过同步', hub_case.id)
        return None, None
    result, err = ensure_ui_project_for_hub(user, hub_project.id)
    if err or not result:
        logger.info('sync_ai_execution_to_cases: 无法定位 UI自动化 项目: %s', err)
        return None, None
    ui_project, _created = result

    # 1) 从执行历史提取操作 + 定位器转成用例步骤
    actions = _extract_ai_history_actions(history)
    if not actions:
        logger.info(
            'sync_ai_execution_to_cases: 执行 #%s 历史无可录制操作（history=%s），跳过',
            execution_record.id, type(history).__name__ if history else None,
        )
        return None, None

    steps, _created_ids = _ai_actions_to_case_steps(ui_project, user, actions, default_page='main')
    if not steps:
        logger.info(
            'sync_ai_execution_to_cases: 执行 #%s 的 %s 个动作均无法映射为用例步骤，跳过',
            execution_record.id, len(actions),
        )
        return None, None

    # 2) 创建/更新 UI自动化 TestCase
    base_name = hub_case.title or 'AI生成步骤'
    ui_title = f'{base_name}-AI生成步骤'
    existing_ui = UiTestCase.objects.filter(project=ui_project, name=ui_title).first()
    if existing_ui:
        UiTestCaseStep.objects.filter(test_case=existing_ui).delete()
        ui_case = existing_ui
    else:
        ui_case = UiTestCase(
            project=ui_project,
            name=ui_title,
            description=f'由「AI生成步骤」自动录制（源用例：{hub_case.title}）',
            status='draft',
            priority='medium',
            created_by=user,
        )
        ui_case.save()

    ui_step_rows = []
    for i, s in enumerate(steps, start=1):
        ui_step_rows.append(UiTestCaseStep(
            test_case=ui_case,
            step_number=i,
            action_type=(s.get('action_type') or 'click')[:20],
            page_filter=(s.get('page_filter') or '')[:200],
            element_id=s.get('element_id') or None,
            input_value=(s.get('input_value') or ''),
            wait_time=int(s.get('wait_time') or 1000),
            assert_type=(s.get('assert_type') or '')[:20],
            assert_value=(s.get('assert_value') or ''),
            description=(s.get('description') or '')[:500],
        ))
    if ui_step_rows:
        UiTestCaseStep.objects.bulk_create(ui_step_rows)

    # 3) 同步到用例库（主项目 testcases，case_type 含 ui）
    case_type = list(hub_case.case_type or []) if hub_case.case_type else []
    if 'ui' not in case_type:
        case_type.append('ui')
    hub_case.case_type = case_type
    hub_case.save(update_fields=['case_type', 'updated_at'])

    # 回显 locator 化的步骤描述到用例库 step_details
    descs = [s.get('description') or '' for s in steps if s.get('description')]
    if descs:
        HubTestCaseStep.objects.filter(testcase=hub_case).delete()
        HubTestCaseStep.objects.bulk_create([
            HubTestCaseStep(testcase=hub_case, step_number=i, action=d, expected='')
            for i, d in enumerate(descs, start=1)
        ])

    logger.info('sync_ai_execution_to_cases: 已同步 UI用例=%s 步骤=%s, 用例库=%s',
                ui_case.id, len(ui_step_rows), hub_case.id)
    return ui_case.id, hub_case.id


def update_planned_task_status(planned_tasks, task_id, task_status):
    """更新子任务状态，返回是否命中任务。"""
    if not planned_tasks or task_id is None or not task_status:
        return False

    normalized_status = str(task_status).strip().lower()
    for task in planned_tasks:
        if str(task.get('id')) == str(task_id):
            task['status'] = normalized_status
            return True
    return False


def backfill_prior_pending_tasks(planned_tasks, current_task_id):
    """补齐当前任务之前被 AI 漏标的前序步骤。

    常见场景：同一 agent step 里连续输入账号+密码，却只 mark 了其中一个；
    随后又 mark 了「点击登录」，导致「输入密码」一直 pending → 用例明细不划线、整单失败。

    策略：当标记 task N 为 completed 时，把 id < N 且仍为 pending/in_progress 的
    连续前序任务一并标为 completed（验证/断言类步骤除外，须显式标记）。
    """
    if not planned_tasks or current_task_id is None:
        return []

    try:
        current_task_id_int = int(current_task_id)
    except (TypeError, ValueError):
        return []

    task_by_id = {}
    for task in planned_tasks:
        try:
            task_by_id[int(task.get('id'))] = task
        except (TypeError, ValueError):
            continue

    if current_task_id_int not in task_by_id:
        return []

    verification_keywords = ['校验', '确认', '检查', '验证', '断言']
    backfilled_ids = []

    # 从 N-1 向前连续补齐，遇到已终态则停下；验证类步骤跳过不强制改写
    for tid in range(current_task_id_int - 1, 0, -1):
        task = task_by_id.get(tid)
        if not task:
            continue
        status = task.get('status', 'pending')
        if status in TERMINAL_TASK_STATUSES:
            # 已终态：继续往前看是否还有空洞（如 1 done, 2 pending, 3 done, 现 mark 5）
            continue
        if status not in ACTIVE_TASK_STATUSES:
            continue
        desc = str(task.get('description', '')).strip()
        if any(keyword in desc for keyword in verification_keywords):
            continue
        task['status'] = 'completed'
        backfilled_ids.append(tid)

    backfilled_ids.reverse()
    return backfilled_ids


def reconcile_skipped_pending_tasks(planned_tasks):
    """执行结束时再扫一遍：最高已完成 id 之前的非验证 pending 一律补齐。

    防止 AI 漏 mark 导致整单被 resolve 成 failed。
    """
    if not planned_tasks:
        return []

    max_completed_id = 0
    for task in planned_tasks:
        try:
            tid = int(task.get('id'))
        except (TypeError, ValueError):
            continue
        if task.get('status') == 'completed' and tid > max_completed_id:
            max_completed_id = tid

    if max_completed_id <= 1:
        return []

    return backfill_prior_pending_tasks(planned_tasks, max_completed_id)


def mark_first_active_task(planned_tasks, task_status):
    """在执行异常时为第一个未终态任务补一个状态。"""
    if not planned_tasks:
        return None

    normalized_status = str(task_status).strip().lower()
    for task in planned_tasks:
        if task.get('status', 'pending') in ACTIVE_TASK_STATUSES:
            task['status'] = normalized_status
            return task.get('id')
    return None


def summarize_planned_tasks(planned_tasks):
    """汇总子任务状态。"""
    summary = {
        'total': 0,
        'completed': 0,
        'failed': 0,
        'skipped': 0,
        'pending': 0,
        'in_progress': 0,
    }
    if not planned_tasks:
        return summary

    summary['total'] = len(planned_tasks)
    for task in planned_tasks:
        task_status = task.get('status', 'pending')
        if task_status in summary:
            summary[task_status] += 1
        else:
            summary['pending'] += 1
    return summary


def resolve_execution_status(planned_tasks):
    """根据子任务实际状态推导整单状态。"""
    summary = summarize_planned_tasks(planned_tasks)

    if summary['total'] == 0:
        return 'passed', summary
    if summary['failed'] > 0:
        return 'failed', summary
    if summary['pending'] > 0 or summary['in_progress'] > 0:
        return 'failed', summary
    return 'passed', summary


def append_execution_summary(logs, summary):
    """把任务统计附加到日志中。"""
    if summary['total'] == 0:
        return logs
    return (
        f"{logs}\n[System] 子任务统计: 总数 {summary['total']}，"
        f"已完成 {summary['completed']}，失败 {summary['failed']}，"
        f"跳过 {summary['skipped']}，待处理 {summary['pending'] + summary['in_progress']}。"
    )


def is_infrastructure_failure(error_message: str) -> bool:
    """判断是否为模型/网络/初始化类故障，这类问题不应直接把首个子任务标失败。"""
    message = (error_message or '').lower()
    infra_markers = [
        '执行预检失败',
        'execution llm unavailable',
        'connection error',
        'timed out',
        'timeout',
        'api key',
        'authentication',
        'unauthorized',
        'forbidden',
        'rate limit',
        'service unavailable',
        '未找到 chrome',
        '未配置 ai 模型',
    ]
    return any(marker in message for marker in infra_markers)


class AIExecutionRecordViewSet(viewsets.ModelViewSet):
    """AI执行记录视图集"""
    queryset = AIExecutionRecord.objects.all()
    serializer_class = AIExecutionRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['project', 'ai_case', 'status']
    ordering = ['-start_time']
    pagination_class = StandardPagination

    def get_queryset(self):
        user = self.request.user
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        # 返回用户有权限的项目下的执行记录，以及没有关联项目的执行记录
        return AIExecutionRecord.objects.filter(
            models.Q(project__in=accessible_projects) | models.Q(project__isnull=True)
        ).distinct()

    def perform_destroy(self, instance):
        instance.delete()

    @action(detail=False, methods=['post'])
    def batch_delete(self, request):
        """批量删除AI执行记录"""
        try:
            ids = request.data.get('ids', [])

            # 验证ids参数
            if not ids:
                return Response({'error': '请选择要删除的记录'}, status=status.HTTP_400_BAD_REQUEST)

            # 确保ids是列表
            if not isinstance(ids, list):
                return Response({'error': 'ids参数格式错误，应为数组'}, status=status.HTTP_400_BAD_REQUEST)

            # 只能删除自己有权限的项目下的记录
            queryset = self.get_queryset()
            records_to_delete = queryset.filter(id__in=ids)

            # 检查是否有权限删除这些记录
            if not records_to_delete.exists():
                return Response({'error': '未找到可删除的记录或没有权限删除'}, status=status.HTTP_404_NOT_FOUND)

            # 获取可删除记录的ID列表，避免对distinct()后的queryset调用delete()
            deletable_ids = list(records_to_delete.values_list('id', flat=True))

            # 使用ID列表直接删除，避免distinct()的问题
            deleted_count = AIExecutionRecord.objects.filter(id__in=deletable_ids).delete()[0]

            return Response({'message': f'成功删除 {deleted_count} 条记录', 'deleted_count': deleted_count})
        except Exception as e:
            logger.error(f"批量删除AI执行记录失败: {str(e)}", exc_info=True)
            return Response({'error': f'批量删除失败: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='run_adhoc')
    def run_adhoc(self, request):
        """执行临时 AI 任务"""
        project_id = request.data.get('project_id')
        task_name = request.data.get('task_name', '')
        task_source = request.data.get('task_source', 'text')  # 任务来源：text/file
        task_description = request.data.get('task_description')
        execution_mode = request.data.get('execution_mode', 'text')  # 默认文本模式
        enable_gif = request.data.get('enable_gif', True)  # GIF录制开关，默认开启
        # 「用例详情 - AI生成步骤」：关联的主平台测试用例 id，执行完成后把步骤回显到该用例的 UI 自动化页
        hub_testcase_id = request.data.get('hub_testcase_id')
        # 「用例转换」：由「用例详情 - AI生成步骤」发起的临时执行，任务来源固定标记为用例转换
        if hub_testcase_id:
            task_source = 'case_conversion'
        # 文件模式：前端上传解析出的用例结构，用于构建与右侧明细 1:1 的 planned_tasks
        parsed_cases = request.data.get('parsed_cases')
        # multipart 模式下 parsed_cases 会以字符串形式到达，需解析为 JSON
        if isinstance(parsed_cases, str):
            try:
                parsed_cases = json.loads(parsed_cases)
            except (ValueError, TypeError):
                parsed_cases = None
        # 文件模式：原始上传的 Excel 文档，用于后续下载
        source_file = request.FILES.get('source_file')

        if not task_description:
            return Response({'error': '缺少任务描述参数'}, status=status.HTTP_400_BAD_REQUEST)

        # 获取项目对象（如果提供了project_id）
        project = None
        if project_id:
            try:
                project = UiProject.objects.get(id=project_id)
            except UiProject.DoesNotExist:
                return Response({'error': '项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        # 文件模式：用解析步骤直接生成 planned_tasks，跳过 LLM 重新拆分
        preset_planned_tasks = build_planned_tasks_from_cases(parsed_cases) if parsed_cases else None

        # 创建执行记录
        execution_record = AIExecutionRecord.objects.create(
            project=project,
            case_name="Adhoc Task",
            task_name=task_name,
            task_source=task_source,
            task_description=task_description,
            execution_mode=execution_mode,
            status='running',
            executed_by=request.user,
            logs="正在分析任务...\n" if not preset_planned_tasks else "已按用例文件步骤开始执行...\n",
            planned_tasks=preset_planned_tasks or [],
            parsed_cases=parsed_cases or [],
            source_file=source_file,
        )

        # 异步执行
        import threading
        import os
        from asgiref.sync import sync_to_async
        from django.db import connection, DatabaseError
        from .ai_agent import run_full_process_sync

        def run_task():
            # 注册停止信号
            STOP_SIGNALS[execution_record.id] = False

            # 关键修复：关闭旧连接，避免子线程共享主线程的连接
            try:
                connection.close()
            except:
                pass

            # 设置环境变量，允许在后台线程中使用同步 ORM
            os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'

            def safe_save(record, update_fields=None, max_retries=3):
                """安全的保存方法，带有重试机制"""
                for attempt in range(max_retries):
                    try:
                        record.save(update_fields=update_fields)
                        return True
                    except (DatabaseError, Exception) as e:
                        error_str = str(e)
                        # 检查是否是MySQL连接错误
                        if '2006' in error_str or 'MySQL server has gone away' in error_str or '0' == error_str:
                            if attempt < max_retries - 1:
                                logger.warning(f"数据库连接失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                                # 关闭旧连接并重试
                                try:
                                    connection.close()
                                except:
                                    pass
                                import time
                                time.sleep(0.5)  # 等待一下再重试
                                continue
                            else:
                                logger.error(f"数据库保存失败，已达最大重试次数: {e}")
                                raise
                        else:
                            # 其他错误直接抛出
                            logger.error(f"数据库保存失败: {e}")
                            raise
                return False

            try:
                # 定义异步安全的 should_stop
                async def should_stop_async():
                    # 优先检查内存信号
                    if STOP_SIGNALS.get(execution_record.id, False):
                        return True
                    # 兜底检查数据库状态 (使用 sync_to_async 避免异步上下文错误)
                    await sync_to_async(execution_record.refresh_from_db)()
                    return execution_record.status == 'stopped'

                # 定义同步版本的 should_stop 用于最后检查
                def should_stop_sync():
                    if STOP_SIGNALS.get(execution_record.id, False):
                        return True
                    execution_record.refresh_from_db()
                    return execution_record.status == 'stopped'

                async def on_analysis_complete(planned_tasks):
                    execution_record.planned_tasks = planned_tasks
                    execution_record.logs += "任务分析完成，开始执行...\n"
                    await sync_to_async(safe_save)(execution_record, update_fields=['planned_tasks', 'logs'])

                async def on_step_update(step_info):
                    try:
                        # 处理日志
                        if step_info.get('type') == 'log':
                            content = step_info.get('content')
                            if content:
                                execution_record.logs += content
                                # 立即保存到数据库，确保前端轮询能看到最新日志
                                await sync_to_async(safe_save)(execution_record, update_fields=['logs'])
                            return

                        # 处理任务状态
                        task_id = step_info.get('task_id')
                        status = step_info.get('status')
                        logger.info(f"DEBUG: on_step_update received: task_id={task_id}, status={status}")

                        if task_id and status:
                            updated = False
                            if execution_record.planned_tasks:
                                old_status = None
                                for task in execution_record.planned_tasks:
                                    if str(task.get('id')) == str(task_id):
                                        old_status = task.get('status', 'pending')
                                        break
                                backfilled_ids = []
                                if str(status).strip().lower() == 'completed':
                                    backfilled_ids = backfill_prior_pending_tasks(
                                        execution_record.planned_tasks,
                                        task_id
                                    )
                                    if backfilled_ids:
                                        execution_record.logs += (
                                            f"\n[System] 已补齐遗漏标记的前序子任务: "
                                            f"{', '.join(map(str, backfilled_ids))}"
                                        )
                                updated = update_planned_task_status(
                                    execution_record.planned_tasks,
                                    task_id,
                                    status
                                )
                                if updated:
                                    logger.info(f"DEBUG: Updated task {task_id} from {old_status} to {status}")
                            if updated:
                                # 立即保存到数据库，确保前端轮询能看到最新状态
                                update_fields = ['planned_tasks']
                                if 'backfilled_ids' in locals() and backfilled_ids:
                                    update_fields.append('logs')
                                await sync_to_async(safe_save)(execution_record, update_fields=update_fields)
                            else:
                                logger.warning(
                                    f"DEBUG: Task ID {task_id} not found in planned_tasks: {execution_record.planned_tasks}")
                    except Exception as e:
                        logger.error(f"更新步骤状态失败: {e}", exc_info=True)

                history = run_full_process_sync(
                    task_description,
                    analysis_callback=on_analysis_complete,
                    step_callback=on_step_update,
                    should_stop=should_stop_async,  # 传递异步版本
                    execution_mode=execution_mode,
                    enable_gif=enable_gif,  # 传递GIF录制开关
                    case_name=task_description[:50] if task_description else "Adhoc Task",  # 传递用例名称用于GIF文件命名
                    screencast_group=f"ui_ai_{execution_record.id}",  # 实时投屏：与 AI 探索测试同一套推送模式
                    planned_tasks=preset_planned_tasks,  # 文件模式：与右侧用例明细 1:1，跳过 LLM 拆分
                )

                # 检查是否是手动停止 (使用同步版本)
                if should_stop_sync():
                    execution_record.status = 'stopped'
                    execution_record.logs += "\n[System] 任务已由用户停止。"
                else:
                    # 补齐 AI 漏标的前序步骤（如合并输入账号+密码只 mark 了一次）
                    reconciled = reconcile_skipped_pending_tasks(execution_record.planned_tasks)
                    if reconciled:
                        execution_record.logs += (
                            f"\n[System] 结束前补齐漏标子任务: {', '.join(map(str, reconciled))}"
                        )
                    execution_record.status, task_summary = resolve_execution_status(execution_record.planned_tasks)
                    if execution_record.status == 'passed':
                        execution_record.logs += "\n执行完成。"
                    else:
                        execution_record.logs += "\n执行结束，但存在未完成或失败的子任务。"
                    logger.info(
                        "🏁 Task completion summary: "
                        f"{task_summary['completed']}/{task_summary['total']} completed, "
                        f"{task_summary['failed']} failed, "
                        f"{task_summary['pending'] + task_summary['in_progress']} pending"
                    )

                execution_record.end_time = timezone.now()
                execution_record.duration = (execution_record.end_time - execution_record.start_time).total_seconds()

                # 格式化 history 为日志 (如果不是停止状态)
                steps = []
                if history:
                    if hasattr(history, 'steps'):
                        steps = [extract_step_info(s, i) for i, s in enumerate(history.steps)]

                execution_record.steps_completed = steps

                # 任务状态完全由 AI 智能体显式标记，测试完成后不再调用统一标记，避免幻觉改写结果
                if execution_record.planned_tasks:
                    execution_record.logs = append_execution_summary(
                        execution_record.logs,
                        summarize_planned_tasks(execution_record.planned_tasks)
                    )

                # 处理GIF录制文件
                self._process_gif_recording(execution_record, history)

                safe_save(execution_record)
            except Exception as e:
                error_message = str(e)
                failed_task_id = None if is_infrastructure_failure(error_message) else mark_first_active_task(execution_record.planned_tasks, 'failed')
                execution_record.status = 'failed'
                execution_record.end_time = timezone.now()
                execution_record.duration = (execution_record.end_time - execution_record.start_time).total_seconds()
                if '执行预检失败' in error_message:
                    execution_record.logs += f"\n执行出错: {error_message}"
                elif 'Execution LLM unavailable' in error_message:
                    execution_record.logs += f"\n执行出错: AI 执行模型连接失败。{error_message}"
                else:
                    execution_record.logs += f"\n执行出错: {error_message}"
                if failed_task_id is not None:
                    execution_record.logs += f"\n[System] 子任务 {failed_task_id} 已自动标记为失败。"
                execution_record.logs = append_execution_summary(
                    execution_record.logs,
                    summarize_planned_tasks(execution_record.planned_tasks)
                )
                try:
                    safe_save(execution_record)
                except:
                    # 如果保存失败，至少尝试保存基本信息
                    logger.error(f"保存失败状态时出错: {e}")
                    pass
            finally:
                # 「用例详情 - AI生成步骤」：无论成功/失败/停止，都尽量把已生成的步骤回显到用例 UI 自动化页
                if hub_testcase_id:
                    try:
                        echoed = echo_steps_to_hub_testcase(hub_testcase_id, execution_record.planned_tasks)
                        if echoed:
                            logger.info(f"已回显 {echoed} 个AI生成步骤到用例 #{hub_testcase_id}")
                    except Exception as echo_err:
                        logger.error(f"回显AI生成步骤到用例 #{hub_testcase_id} 失败: {echo_err}")
                    # 「用例详情 - AI生成步骤」：把执行历史里的操作+定位器录制成用例，同步到
                    # UI自动化「用例管理」列表与「用例库」UI自动化页面
                    try:
                        _history = locals().get('history') or None
                        ui_case_id, hub_id = sync_ai_execution_to_cases(
                            hub_testcase_id, execution_record, _history
                        )
                        if ui_case_id:
                            logger.info(f"已录制AI生成步骤到UI用例 #{ui_case_id}（用例库 #{hub_id}）")
                    except Exception as sync_err:
                        logger.error(f"录制AI生成步骤到用例失败: {sync_err}", exc_info=True)
                # 清理停止信号
                if execution_record.id in STOP_SIGNALS:
                    del STOP_SIGNALS[execution_record.id]

        thread = threading.Thread(target=run_task)
        thread.daemon = True
        thread.start()

        return Response({
            'message': 'AI 任务开始执行',
            'execution_id': execution_record.id,
            'hub_testcase_id': hub_testcase_id,
        })

    @action(detail=True, methods=['get'], url_path='download_source_file')
    def download_source_file(self, request, pk=None):
        """下载文件模式上传的原始用例文档（Excel）"""
        record = self.get_object()
        if not record.source_file:
            return Response({'error': '该记录没有原始用例文档'}, status=status.HTTP_404_NOT_FOUND)

        file_path = record.source_file.path
        if not os.path.exists(file_path):
            return Response({'error': '原始用例文档不存在'}, status=status.HTTP_404_NOT_FOUND)

        filename = os.path.basename(record.source_file.name)
        response = FileResponse(
            open(file_path, 'rb'),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
        return response

    @action(detail=True, methods=['post'], url_path='stop')
    def stop_task(self, request, pk=None):
        """停止正在执行的任务"""
        try:
            execution_id = int(pk)
            if execution_id in STOP_SIGNALS:
                STOP_SIGNALS[execution_id] = True
                return Response({'message': '已发送停止信号'})
            else:
                # 如果不在内存中，可能已经结束，或者重启过服务
                # 尝试直接更新数据库状态
                record = self.get_object()
                if record.status == 'running':
                    record.status = 'stopped'
                    record.end_time = timezone.now()
                    record.logs += "\n[System] 任务被强制标记为停止（未在运行队列中找到）。"
                    record.save()
                    return Response({'message': '任务已标记为停止'})
                return Response({'message': '任务不在运行中'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _process_gif_recording(self, execution_record, history):
        """
        处理GIF录制文件
        在执行完成后查找生成的GIF文件并保存路径到数据库
        """
        try:
            import os
            from django.conf import settings
            from datetime import datetime

            # browser-use 默认生成的GIF文件名（固定为agent_history.gif）
            default_gif_path = os.path.join(os.getcwd(), 'agent_history.gif')

            # 如果找到GIF文件，移动到media/ai_recording目录并重命名
            if os.path.exists(default_gif_path):
                import shutil

                # 创建录制文件目录
                gif_dir = os.path.join(settings.MEDIA_ROOT, 'ai_recording')
                os.makedirs(gif_dir, exist_ok=True)

                # 生成新的文件名：用例名称+年月日时分秒
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
                # 清理用例名称中的非法字符
                safe_case_name = "".join(
                    [c if c.isalnum() or c in (' ', '_', '-') else '_' for c in execution_record.case_name])
                new_gif_filename = f"{safe_case_name}_{timestamp}.gif"
                new_gif_path = os.path.join(gif_dir, new_gif_filename)

                # 移动并重命名文件
                shutil.move(default_gif_path, new_gif_path)

                # 保存相对路径到数据库（使用正斜杠，确保跨平台兼容）
                relative_path = f'media/ai_recording/{new_gif_filename}'
                execution_record.gif_path = relative_path

                logger.info(f"✅ GIF recording saved to: {relative_path}")
            else:
                logger.warning(f"⚠️ GIF file not found at: {default_gif_path}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to process GIF recording: {e}")

    @action(detail=True, methods=['get'], url_path='report')
    def generate_report(self, request, pk=None):
        """
        生成AI执行报告

        Query Parameters:
            report_type: 报告类型 (summary/detailed/performance)，默认为 summary

        Returns:
            执行报告数据
        """
        try:
            record = self.get_object()
            report_type = request.query_params.get('report_type', 'summary')

            # 导入报告生成器
            from .reports import AIExecutionReportGenerator

            # 生成报告
            generator = AIExecutionReportGenerator(record)

            if report_type == 'detailed':
                report = generator.generate_detailed_report()
            elif report_type == 'performance':
                report = generator.generate_performance_report()
            else:  # summary
                report = generator.generate_summary_report()

            return Response({
                'success': True,
                'data': report,
                'report_type': report_type
            })

        except Exception as e:
            logger.error(f"生成AI执行报告失败: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='export-pdf')
    def export_pdf(self, request, pk=None):
        """
        导出AI执行报告为PDF

        Query Parameters:
            report_type: 报告类型 (summary/detailed/performance)，默认为 summary

        Returns:
            PDF文件下载
        """
        try:
            record = self.get_object()
            report_type = request.query_params.get('report_type', 'summary')

            # 导入报告生成器
            from .reports import AIExecutionReportGenerator
            from .pdf_generator import AIReportPDFGenerator

            # 生成报告数据
            generator = AIExecutionReportGenerator(record)

            if report_type == 'detailed':
                report_data = generator.generate_detailed_report()
            elif report_type == 'performance':
                report_data = generator.generate_performance_report()
            else:  # summary
                report_data = generator.generate_summary_report()

            # 生成PDF
            pdf_generator = AIReportPDFGenerator(report_data, report_type)
            pdf_buffer = pdf_generator.generate()

            # 生成文件名
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            safe_case_name = "".join([c if c.isalnum() or c in (' ', '_', '-') else '_' for c in record.case_name])
            filename = f"AI_Report_{safe_case_name}_{timestamp}.pdf"

            # 返回PDF文件
            response = HttpResponse(
                pdf_buffer.getvalue(),
                content_type='application/pdf'
            )
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            response['Content-Length'] = len(pdf_buffer.getvalue())

            return response

        except ImportError as e:
            logger.error(f"PDF生成库未安装: {e}")
            return Response({
                'success': False,
                'error': 'PDF生成功能需要安装 reportlab 库，请运行: pip install reportlab'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.error(f"导出PDF失败: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class UiDashboardViewSet(viewsets.ViewSet):
    """UI自动化仪表盘视图集"""
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """获取仪表盘统计数据"""
        user = request.user

        # 获取用户可访问的项目ID列表
        accessible_projects = UiProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        project_ids = accessible_projects.values_list('id', flat=True)

        # 统计数据
        project_count = accessible_projects.count()

        # 测试用例数量
        test_case_count = TestCase.objects.filter(project_id__in=project_ids).count()

        # 测试套件数量（包含用例总数）
        suite_count = TestSuite.objects.filter(project_id__in=project_ids).count()

        from .models import TestSuiteTestCase
        suite_test_case_count = TestSuiteTestCase.objects.filter(
            test_suite__project_id__in=project_ids
        ).count()

        # 测试执行数量（传统+新版）
        execution_count = TestExecution.objects.filter(project_id__in=project_ids).count()
        test_case_execution_count = TestCaseExecution.objects.filter(project_id__in=project_ids).count()
        total_execution_count = execution_count + test_case_execution_count

        return Response({
            'project_count': project_count,
            'test_case_count': test_case_count,
            'suite_count': suite_test_case_count,
            'execution_count': total_execution_count
        })
