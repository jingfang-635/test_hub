# -*- coding: utf-8 -*-
"""APP自动化项目管理视图"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
import logging

from .test_case_views import AppPagination
from ..models import AppProject
from ..serializers import (
    AppProjectSerializer,
    AppProjectCreateSerializer,
    AppProjectUpdateSerializer,
)

logger = logging.getLogger(__name__)


class AppProjectViewSet(viewsets.ModelViewSet):
    """APP自动化项目 ViewSet"""
    queryset = AppProject.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = AppPagination
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'owner']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return AppProjectCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AppProjectUpdateSerializer
        return AppProjectSerializer

    def get_queryset(self):
        user = self.request.user
        return AppProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    @action(detail=False, methods=['post'], url_path='ensure')
    def ensure_for_hub_project(self, request):
        """按「项目与版本」主项目 get-or-create 对应的 AppProject。"""
        from apps.projects.models import Project

        hub_project_id = request.data.get('hub_project_id')
        if not hub_project_id:
            return Response({'error': '请提供 hub_project_id'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            hub_project = Project.objects.get(id=hub_project_id)
        except Project.DoesNotExist:
            return Response({'error': '主项目不存在'}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        if hub_project.owner_id != user.id and not hub_project.members.filter(id=user.id).exists():
            return Response({'error': '无权限访问该项目'}, status=status.HTTP_403_FORBIDDEN)

        if 'app_automation' not in (hub_project.project_types or []):
            return Response(
                {'error': '该项目未关联 APP自动化 模块'},
                status=status.HTTP_400_BAD_REQUEST
            )

        app_project = AppProject.objects.filter(hub_project=hub_project).first()
        created = False
        if not app_project:
            # 兼容历史数据：同名未关联的 AppProject 优先绑定
            app_project = AppProject.objects.filter(
                hub_project__isnull=True,
                name=hub_project.name,
            ).filter(
                models.Q(owner=user) | models.Q(members=user)
            ).first()
            if app_project:
                app_project.hub_project = hub_project
                app_project.description = app_project.description or (hub_project.description or '')
                app_project.save(update_fields=['hub_project', 'description', 'updated_at'])
            else:
                status_map = {
                    'active': 'IN_PROGRESS',
                    'paused': 'NOT_STARTED',
                    'completed': 'COMPLETED',
                    'archived': 'COMPLETED',
                }
                app_project = AppProject.objects.create(
                    name=hub_project.name,
                    description=hub_project.description or '',
                    status=status_map.get(hub_project.status, 'IN_PROGRESS'),
                    owner=hub_project.owner,
                    hub_project=hub_project,
                )
                member_ids = list(hub_project.members.values_list('id', flat=True))
                if member_ids:
                    app_project.members.set(member_ids)
                created = True

        serializer = AppProjectSerializer(app_project)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
