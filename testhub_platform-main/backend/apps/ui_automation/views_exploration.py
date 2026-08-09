"""
AI探索测试 API ViewSet
"""
import os
import threading

from django.db import connection
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import AIExplorationTask, AIExplorationCase, AIExplorationStep
from .ai_exploration import run_exploration_sync, EXPLORATION_STOP_SIGNALS


def _serialize_task(task):
    return {
        'id': task.id,
        'name': task.name,
        'start_url': task.start_url,
        'environment': task.environment,
        'data_source': task.data_source,
        'data_source_display': task.get_data_source_display(),
        'data_content': task.data_content,
        'intent_content': task.intent_content,
        'repo_content': task.repo_content,
        'status': task.status,
        'logs': task.logs,
        'start_time': task.start_time.isoformat() if task.start_time else None,
        'end_time': task.end_time.isoformat() if task.end_time else None,
        'duration': task.duration,
    }


def _serialize_case(case):
    return {
        'id': case.id,
        'name': case.name,
        'description': case.description,
        'order': case.order,
        'status': case.status,
        'created_at': case.created_at.isoformat() if case.created_at else None,
    }


def _serialize_step(step):
    return {
        'id': step.id,
        'order': step.order,
        'action_type': step.action_type,
        'action_description': step.action_description,
        'element_index': step.element_index,
        'element_text': step.element_text,
        'rect': step.rect or {},
        'click_point': step.click_point or {},
        'screenshot': step.screenshot,
        'page_url': step.page_url,
        'status': step.status,
    }


class AIExplorationTaskViewSet(viewsets.ModelViewSet):
    """AI探索测试任务"""
    queryset = AIExplorationTask.objects.all().order_by('-start_time')

    def list(self, request):
        tasks = self.get_queryset()[:50]
        return Response([_serialize_task(t) for t in tasks])

    def retrieve(self, request, pk=None):
        task = self.get_object()
        data = _serialize_task(task)
        data['cases'] = [_serialize_case(c) for c in task.cases.all()]
        return Response(data)

    def create(self, request):
        name = request.data.get('name') or '探索测试'
        start_url = request.data.get('start_url')
        environment = request.data.get('environment', '')
        data_source = request.data.get('data_source', 'autonomous')
        data_content = request.data.get('data_content', '')
        intent_content = request.data.get('intent_content', '')
        repo_content = request.data.get('repo_content', '')
        if not start_url:
            return Response({'error': '起始URL不能为空'}, status=status.HTTP_400_BAD_REQUEST)

        task = AIExplorationTask.objects.create(
            name=name,
            start_url=start_url,
            environment=environment,
            data_source=data_source,
            data_content=data_content,
            intent_content=intent_content,
            repo_content=repo_content,
            status='pending',
            created_by=request.user,
        )
        return Response(_serialize_task(task), status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """启动探索执行"""
        task = self.get_object()
        if task.status == 'running':
            return Response({'error': '任务正在执行中'}, status=status.HTTP_400_BAD_REQUEST)

        task.status = 'running'
        task.logs = (task.logs or '') + "开始探索...\n"
        task.save()
        EXPLORATION_STOP_SIGNALS[task.id] = False

        def run():
            try:
                connection.close()
            except Exception:
                pass
            os.environ['DJANGO_ALLOW_ASYNC_UNSAFE'] = 'true'
            try:
                run_exploration_sync(task.id)
            except Exception as e:
                # 兜底：防止异常逃逸导致线程静默退出
                import traceback
                tb = traceback.format_exc()
                try:
                    t = AIExplorationTask.objects.get(id=task.id)
                    t.status = 'failed'
                    t.logs = (t.logs or '') + f"\n[线程异常] {e}\n{tb}\n"
                    t.save()
                except Exception:
                    pass

        threading.Thread(target=run, daemon=True).start()
        return Response({'message': '探索任务已启动', 'task_id': task.id})

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止探索执行"""
        task = self.get_object()
        EXPLORATION_STOP_SIGNALS[task.id] = True
        if task.status == 'running':
            task.status = 'stopped'
            task.save()
        return Response({'message': '已发送停止信号'})

    @action(detail=True, methods=['get'])
    def progress(self, request, pk=None):
        """轮询：返回任务状态 + 用例步骤（动态加载，供前端实时展示）"""
        task = self.get_object()
        data = _serialize_task(task)
        case_list = []
        for c in task.cases.all():
            cd = _serialize_case(c)
            cd['steps'] = [_serialize_step(s) for s in c.steps.all()]
            case_list.append(cd)
        data['cases'] = case_list
        return Response(data)


class AIExplorationStepViewSet(viewsets.ModelViewSet):
    """探索步骤（可视化编排时更新坐标）"""
    queryset = AIExplorationStep.objects.all()

    def retrieve(self, request, pk=None):
        return Response(_serialize_step(self.get_object()))

    def partial_update(self, request, pk=None):
        """PATCH 更新 rect/click_point/element_text 等（可视化编排）"""
        step = self.get_object()
        for f in ('rect', 'click_point', 'element_text', 'action_description', 'action_type'):
            if f in request.data:
                setattr(step, f, request.data[f])
        step.save()
        return Response(_serialize_step(step))

    @action(detail=True, methods=['patch'])
    def update_coords(self, request, pk=None):
        """仅更新元素坐标（rect + click_point）"""
        step = self.get_object()
        if 'rect' in request.data:
            step.rect = request.data['rect']
        if 'click_point' in request.data:
            step.click_point = request.data['click_point']
        step.save()
        return Response(_serialize_step(step))
