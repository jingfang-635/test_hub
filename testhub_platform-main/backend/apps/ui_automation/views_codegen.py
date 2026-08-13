"""
Playwright Codegen 录制 API + Phase 2–4 流水线。
"""
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .codegen_service import codegen_recorder
from .codegen_pipeline_service import (
    confirm_plan,
    conversion_to_dict,
    create_from_parse,
    generate_plan,
    generate_scripts,
    map_parse_to_case_steps,
    update_plan_md,
)
from .models import CodegenConversion, TestScript, UiProject


class PlaywrightCodegenViewSet(viewsets.ViewSet):
    """Playwright 录制脚本接口"""

    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'], url_path='check-env')
    def check_env(self, request):
        return Response(codegen_recorder.check_environment())

    @action(detail=False, methods=['post'], url_path='start')
    def start(self, request):
        data = request.data or {}
        url = data.get('url', '')
        browser = data.get('browser', 'chromium')
        language = data.get('language', 'python')
        project_id = data.get('project_id') or data.get('project')
        script_name = data.get('script_name') or data.get('name') or ''

        try:
            project_id_int = int(project_id) if project_id not in (None, '', 'all') else None
        except (TypeError, ValueError):
            project_id_int = None

        try:
            session = codegen_recorder.start(
                user_id=request.user.id,
                url=url,
                browser=browser,
                language=language,
                project_id=project_id_int,
                script_name=script_name,
            )
            return Response({
                'message': '录制已启动，请在打开的浏览器中完成操作，结束后在 Inspector 点击停止',
                'session': session.to_dict(include_content=False),
            })
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            return Response({'error': f'启动失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='status')
    def status_view(self, request):
        session = codegen_recorder.get_session(request.user.id)
        if not session:
            return Response({
                'session': None,
                'message': '当前没有录制任务',
            })
        include_content = request.query_params.get('include_content', '1') != '0'
        return Response({
            'session': session.to_dict(include_content=include_content),
        })

    @action(detail=False, methods=['post'], url_path='stop')
    def stop(self, request):
        session = codegen_recorder.stop(request.user.id)
        if not session:
            return Response({'error': '当前没有录制任务'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'message': '已结束录制',
            'session': session.to_dict(include_content=True),
        })

    @action(detail=False, methods=['get'], url_path='recorded')
    def recorded_list(self, request):
        return Response({
            'results': codegen_recorder.list_recorded(),
        })

    @action(detail=False, methods=['get'], url_path='recorded-content')
    def recorded_content(self, request):
        name = request.query_params.get('name', '')
        if not name:
            return Response({'error': '缺少 name 参数'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            content = codegen_recorder.read_recorded(name)
            return Response({'name': name, 'content': content})
        except FileNotFoundError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    # ========== Phase 2–4 流水线 ==========

    def _get_project(self, project_id):
        try:
            return UiProject.objects.get(pk=int(project_id))
        except (TypeError, ValueError, UiProject.DoesNotExist):
            return None

    def _get_conversion(self, pk, user):
        try:
            return CodegenConversion.objects.select_related('project', 'user').get(pk=pk)
        except (CodegenConversion.DoesNotExist, ValueError, TypeError):
            return None

    @action(detail=False, methods=['post'], url_path='pipeline/parse')
    def pipeline_parse(self, request):
        data = request.data or {}
        content = data.get('content') or data.get('recorded_content') or ''
        if not str(content).strip():
            return Response({'error': '录制脚本内容为空'}, status=status.HTTP_400_BAD_REQUEST)

        project = self._get_project(data.get('project_id') or data.get('project'))
        if not project:
            return Response({'error': '请选择有效项目'}, status=status.HTTP_400_BAD_REQUEST)

        source_script = None
        source_script_id = data.get('source_script_id')
        if source_script_id:
            source_script = TestScript.objects.filter(pk=source_script_id, project=project).first()

        try:
            conversion = create_from_parse(
                project=project,
                user=request.user,
                content=content,
                language=data.get('language') or 'python',
                scenario=data.get('scenario') or data.get('script_name') or '',
                target_url=data.get('target_url') or data.get('url') or '',
                recorded_name=data.get('recorded_name') or data.get('script_name') or '',
                source_script=source_script,
            )
            return Response({
                'message': '录制脚本已解析',
                'conversion': conversion_to_dict(conversion),
            })
        except Exception as exc:  # noqa: BLE001
            return Response({'error': f'解析失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='pipeline/to-case-steps')
    def pipeline_to_case_steps(self, request):
        """录制脚本 → 用例步骤（供用例管理「录制步骤」导入）。"""
        data = request.data or {}
        content = data.get('content') or data.get('recorded_content') or ''
        if not str(content).strip():
            return Response({'error': '录制脚本内容为空'}, status=status.HTTP_400_BAD_REQUEST)

        project = self._get_project(data.get('project_id') or data.get('project'))
        if not project:
            return Response({'error': '请选择有效项目'}, status=status.HTTP_400_BAD_REQUEST)

        create_elements_raw = data.get('create_elements', True)
        create_elements = str(create_elements_raw).strip().lower() not in {'0', 'false', 'no', 'off'}

        try:
            result = map_parse_to_case_steps(
                project=project,
                user=request.user,
                content=content,
                language=data.get('language') or 'python',
                create_elements=create_elements,
            )
            return Response({
                'message': f'已解析出 {result.get("step_count", 0)} 个用例步骤',
                **result,
            })
        except Exception as exc:  # noqa: BLE001
            return Response({'error': f'解析为用例步骤失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path=r'pipeline/detail/(?P<pk>[^/.]+)')
    def pipeline_detail(self, request, pk=None):
        conversion = self._get_conversion(pk, request.user)
        if not conversion:
            return Response({'error': '流水线任务不存在'}, status=status.HTTP_404_NOT_FOUND)
        return Response({'conversion': conversion_to_dict(conversion)})

    @action(detail=False, methods=['post'], url_path=r'pipeline/(?P<pk>[^/.]+)/generate-plan')
    def pipeline_generate_plan(self, request, pk=None):
        conversion = self._get_conversion(pk, request.user)
        if not conversion:
            return Response({'error': '流水线任务不存在'}, status=status.HTTP_404_NOT_FOUND)
        data = request.data or {}
        user_cases = data.get('user_cases_md')
        if user_cases is None:
            user_cases = conversion.user_cases_md
        use_ai_raw = data.get('use_ai', False)
        use_ai = str(use_ai_raw).strip().lower() in {'1', 'true', 'yes', 'on'}
        try:
            conversion = generate_plan(conversion, user_cases_md=user_cases, use_ai=use_ai)
            mode = 'AI 增强' if use_ai and not conversion.error else '模板'
            return Response({
                'message': f'用例计划已生成（{mode}），请审阅确认后再生成脚本',
                'conversion': conversion_to_dict(conversion),
                'use_ai': use_ai,
            })
        except RuntimeError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            return Response({'error': f'生成计划失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['patch', 'put'], url_path=r'pipeline/(?P<pk>[^/.]+)/plan')
    def pipeline_update_plan(self, request, pk=None):
        conversion = self._get_conversion(pk, request.user)
        if not conversion:
            return Response({'error': '流水线任务不存在'}, status=status.HTTP_404_NOT_FOUND)
        plan_md = (request.data or {}).get('plan_md', '')
        conversion = update_plan_md(conversion, plan_md)
        return Response({
            'message': '计划已保存',
            'conversion': conversion_to_dict(conversion),
        })

    @action(detail=False, methods=['post'], url_path=r'pipeline/(?P<pk>[^/.]+)/confirm-plan')
    def pipeline_confirm_plan(self, request, pk=None):
        conversion = self._get_conversion(pk, request.user)
        if not conversion:
            return Response({'error': '流水线任务不存在'}, status=status.HTTP_404_NOT_FOUND)
        plan_md = (request.data or {}).get('plan_md')
        try:
            conversion = confirm_plan(conversion, plan_md=plan_md)
            return Response({
                'message': '计划已确认，可以生成工程化脚本',
                'conversion': conversion_to_dict(conversion),
            })
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'], url_path=r'pipeline/(?P<pk>[^/.]+)/generate-scripts')
    def pipeline_generate_scripts(self, request, pk=None):
        conversion = self._get_conversion(pk, request.user)
        if not conversion:
            return Response({'error': '流水线任务不存在'}, status=status.HTTP_404_NOT_FOUND)
        data = request.data or {}
        use_ai_raw = data.get('use_ai', False)
        use_ai = str(use_ai_raw).strip().lower() in {'1', 'true', 'yes', 'on'}
        try:
            conversion = generate_scripts(conversion, use_ai=use_ai)
            mode = 'AI 增强' if use_ai and not conversion.error else '模板'
            return Response({
                'message': f'脚本与脚手架已生成完毕（{mode}）。跑测/打开报告/根据报错修复需另行触发。',
                'conversion': conversion_to_dict(conversion),
                'use_ai': use_ai,
            })
        except ValueError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # noqa: BLE001
            return Response({'error': f'生成脚本失败: {exc}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
