"""
AI探索测试 API ViewSet
"""
import os
import threading

from django.db import connection
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response

from .models import AIExplorationTask, AIExplorationCase, AIExplorationStep
from .ai_exploration import run_exploration_sync, EXPLORATION_STOP_SIGNALS
from .case_file_parser import parse_case_file, CaseFileParseError, SUPPORTED_EXTENSIONS


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
        'ai_model_id': task.ai_model_config_id,
        'ai_model_name': (f"{task.ai_model_config.name} ({task.ai_model_config.model_name})" if task.ai_model_config else ''),
        'status': task.status,
        'logs': task.logs,
        'generated_code': task.generated_code if hasattr(task, 'generated_code') else '',
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
        'locator_strategy': getattr(step, 'locator_strategy', ''),
        'locator_value': getattr(step, 'locator_value', ''),
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
        case_list = []
        for c in task.cases.all():
            cd = _serialize_case(c)
            cd['steps'] = [_serialize_step(s) for s in c.steps.all()]
            case_list.append(cd)
        data['cases'] = case_list
        return Response(data)

    def create(self, request):
        name = request.data.get('name') or '探索测试'
        start_url = request.data.get('start_url')
        environment = request.data.get('environment', '')
        data_source = request.data.get('data_source', 'autonomous')
        data_content = request.data.get('data_content', '')
        intent_content = request.data.get('intent_content', '')
        repo_content = request.data.get('repo_content', '')
        ai_model_id = request.data.get('ai_model_id')
        if not start_url:
            return Response({'error': '起始URL不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        # 校验 URL 格式：必须是 http/https 开头的合法网址，避免把账号密码等非 URL 内容误填导致静默失败
        from urllib.parse import urlparse
        parsed = urlparse(str(start_url).strip())
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            return Response(
                {'error': '起始URL格式不正确，请输入以 http:// 或 https:// 开头的完整网址（如 https://example.com）。'
                          '账号、密码等登录信息请填写在"自然语言意图"中'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 查找AI模型配置
        ai_model_config = None
        if ai_model_id:
            try:
                from apps.requirement_analysis.models import AIModelConfig
                ai_model_config = AIModelConfig.objects.get(id=ai_model_id)
            except AIModelConfig.DoesNotExist:
                pass

        task = AIExplorationTask.objects.create(
            name=name,
            start_url=start_url,
            environment=environment,
            data_source=data_source,
            data_content=data_content,
            intent_content=intent_content,
            repo_content=repo_content,
            ai_model_config=ai_model_config,
            status='pending',
            created_by=request.user,
        )
        return Response(_serialize_task(task), status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        """删除探索任务（运行中的任务不允许删除）"""
        task = self.get_object()
        if task.status == 'running':
            return Response({'error': '任务正在执行中，请先停止后再删除'}, status=status.HTTP_400_BAD_REQUEST)
        task.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_cases(self, request):
        """上传功能用例文件（Excel/XMind/Markdown），解析为用例文本供功能用例驱动模式使用。"""
        upload = request.FILES.get('file')
        if upload is None:
            return Response({'error': '未检测到上传文件，请选择用例文件'}, status=status.HTTP_400_BAD_REQUEST)

        ext = ''
        if upload.name and '.' in upload.name:
            ext = upload.name[upload.name.rfind('.'):].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            return Response(
                {'error': f'不支持的文件类型：{ext or "未知"}，仅支持 Excel(.xlsx/.xls)、XMind(.xmind)、Markdown(.md/.txt)'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            data = upload.read()
            result = parse_case_file(upload.name, data)
        except CaseFileParseError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            logger_msg = traceback.format_exc()
            return Response(
                {'error': f'文件解析失败：{e}', 'detail': logger_msg},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            'filename': upload.name,
            'format': result['format'],
            'case_count': result['case_count'],
            'cases': result['cases'],
            'text': result['text'],
        }, status=status.HTTP_200_OK)

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
