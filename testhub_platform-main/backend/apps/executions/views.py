from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from .models import TestPlan, TestRun, TestRunCase, TestRunCaseHistory
from apps.testcases.models import TestCase
from apps.projects.models import Project
from .serializers import (TestPlanSerializer, TestRunSerializer, TestRunCaseSerializer, 
                         TestPlanDetailSerializer, TestRunCaseDetailSerializer, 
                         TestRunCaseHistorySerializer)

class TestPlanViewSet(viewsets.ModelViewSet):
    """
    测试计划视图集
    """
    queryset = TestPlan.objects.all().order_by('-created_at')
    serializer_class = TestPlanSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TestPlanDetailSerializer
        return TestPlanSerializer

    def get_queryset(self):
        queryset = TestPlan.objects.all().order_by('-created_at')
        project_id = self.request.query_params.get('project')
        is_active = self.request.query_params.get('is_active')

        if project_id not in (None, ''):
            try:
                queryset = queryset.filter(projects__id=int(project_id)).distinct()
            except (TypeError, ValueError):
                pass

        if is_active not in (None, ''):
            value = str(is_active).lower()
            if value in ('true', '1'):
                queryset = queryset.filter(is_active=True)
            elif value in ('false', '0'):
                queryset = queryset.filter(is_active=False)

        return queryset

    def perform_create(self, serializer):
        # 在创建TestPlan时，设置creator并自动为每个项目创建TestRun和TestRunCase
        # 获取版本信息
        version_id = self.request.data.get('version')
        version = None
        if version_id:
            from apps.versions.models import Version
            try:
                version = Version.objects.get(id=version_id)
            except Version.DoesNotExist:
                pass
        
        test_plan = serializer.save(creator=self.request.user, version=version)
        
        # 获取选中的项目和测试用例
        project_ids = self.request.data.get('projects', [])
        testcase_ids = self.request.data.get('testcases', [])
        
        if project_ids:
            # 设置测试计划的项目关联
            test_plan.projects.set(project_ids)
            
            # 为每个项目创建TestRun
            for project_id in project_ids:
                try:
                    project = Project.objects.get(id=project_id)
                    test_run = TestRun.objects.create(
                        name=f"{test_plan.name} - {project.name} Execution",
                        test_plan=test_plan,
                        project=project,
                        version=test_plan.version,
                        creator=test_plan.creator,
                        assignee=test_plan.creator  # 默认指派给自己
                    )
                    
                    # 为TestRun关联测试用例
                    if testcase_ids:
                        test_run_cases = []
                        for case_id in testcase_ids:
                            try:
                                testcase = TestCase.objects.get(id=case_id)
                                test_run_cases.append(
                                    TestRunCase(test_run=test_run, testcase=testcase)
                                )
                            except TestCase.DoesNotExist:
                                continue
                        TestRunCase.objects.bulk_create(test_run_cases)
                        test_run.testcases.set(testcase_ids)
                        
                except Project.DoesNotExist:
                    continue

    @action(detail=False, methods=['get'])
    def testcases_by_projects(self, request):
        """
        根据项目获取测试用例
        """
        project_ids = request.query_params.getlist('project_ids')
        if not project_ids:
            return Response({
                'error': '请先选择项目',
                'detail': '请先选择项目后再选择测试用例'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # 过滤数字字符串和空值
            project_ids = [int(pid) for pid in project_ids if pid and pid.isdigit()]
            
            if not project_ids:
                return Response({
                    'error': '无效的项目 ID',
                    'detail': '请选择有效的项目'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # 获取指定项目的测试用例
            testcases = TestCase.objects.filter(
                project_id__in=project_ids,
                status__in=['draft', 'active']  # 包含草稿和激活状态的测试用例
            ).values('id', 'title', 'priority', 'test_type', 'project__name')
            
            return Response({
                'results': list(testcases)
            })
            
        except ValueError:
            return Response({
                'error': '项目 ID 格式错误',
                'detail': '请提供有效的项目 ID'
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'error': '获取测试用例失败',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_update(self, serializer):
        # 在更新TestPlan时，处理版本信息
        version_id = self.request.data.get('version')
        version = None
        if version_id:
            from apps.versions.models import Version
            try:
                version = Version.objects.get(id=version_id)
            except Version.DoesNotExist:
                pass
        
        # 更新测试计划
        test_plan = serializer.save(version=version)
        
        # 更新项目关联
        project_ids = self.request.data.get('projects', [])
        if project_ids:
            test_plan.projects.set(project_ids)
        
        # 更新指派人员
        assignee_ids = self.request.data.get('assignees', [])
        if assignee_ids:
            test_plan.assignees.set(assignee_ids)

    @action(detail=True, methods=['get'])
    def assigned_testcases(self, request, pk=None):
        """获取测试计划已分配的用例 ID 及关联项目 ID"""
        test_plan = self.get_object()
        project_ids = list(test_plan.projects.values_list('id', flat=True))
        testcase_ids = list(
            TestRunCase.objects.filter(test_run__test_plan=test_plan)
            .values_list('testcase_id', flat=True)
            .distinct()
        )
        return Response({
            'project_ids': project_ids,
            'testcase_ids': testcase_ids,
        })

    @action(detail=True, methods=['post'])
    def assign_testcases(self, request, pk=None):
        """为测试计划分配用例（按项目写入对应 TestRun，仅新增不覆盖）"""
        test_plan = self.get_object()
        testcase_ids = request.data.get('testcases', [])

        if not isinstance(testcase_ids, list) or not testcase_ids:
            return Response({
                'error': '请选择测试用例',
                'detail': '请至少选择一个测试用例'
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            testcase_ids = [int(tid) for tid in testcase_ids]
        except (TypeError, ValueError):
            return Response({
                'error': '用例 ID 格式错误',
                'detail': '请提供有效的用例 ID'
            }, status=status.HTTP_400_BAD_REQUEST)

        plan_projects = list(test_plan.projects.all())
        if not plan_projects:
            return Response({
                'error': '计划未关联项目',
                'detail': '请先为测试计划关联项目后再分配用例'
            }, status=status.HTTP_400_BAD_REQUEST)

        project_ids = [p.id for p in plan_projects]
        testcases = list(
            TestCase.objects.filter(
                id__in=testcase_ids,
                project_id__in=project_ids,
                status__in=['draft', 'active']
            )
        )
        if not testcases:
            return Response({
                'error': '无有效用例',
                'detail': '所选用例不属于该计划关联项目，或状态不可用'
            }, status=status.HTTP_400_BAD_REQUEST)

        added_count = 0
        for project in plan_projects:
            test_run = test_plan.test_runs.filter(project=project).first()
            if not test_run:
                test_run = TestRun.objects.create(
                    name=f"{test_plan.name} - {project.name} Execution",
                    test_plan=test_plan,
                    project=project,
                    version=test_plan.version,
                    creator=test_plan.creator,
                    assignee=test_plan.creator
                )

            existing_ids = set(
                test_run.run_cases.values_list('testcase_id', flat=True)
            )
            new_run_cases = []
            for testcase in testcases:
                if testcase.project_id != project.id or testcase.id in existing_ids:
                    continue
                new_run_cases.append(
                    TestRunCase(test_run=test_run, testcase=testcase)
                )
            if new_run_cases:
                TestRunCase.objects.bulk_create(new_run_cases)
                added_count += len(new_run_cases)

        return Response({
            'detail': '分配成功',
            'added_count': added_count,
            'selected_count': len(testcases),
        })


class TestRunViewSet(viewsets.ModelViewSet):
    """
    测试执行视图集
    """
    queryset = TestRun.objects.all().order_by('-created_at')
    serializer_class = TestRunSerializer

class TestRunCaseViewSet(viewsets.ModelViewSet):
    """
    测试执行用例视图集
    """
    queryset = TestRunCase.objects.all()
    serializer_class = TestRunCaseSerializer

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TestRunCaseDetailSerializer
        return TestRunCaseSerializer

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """
        更新单个用例的执行状态，并自动创建历史记录
        """
        run_case = self.get_object()
        new_status = request.data.get('status')
        actual_result = request.data.get('actual_result', '')
        comments = request.data.get('comments', '')
        
        if not new_status:
            return Response({'error': 'Status is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建历史记录
        TestRunCaseHistory.objects.create(
            run_case=run_case,
            status=new_status,
            actual_result=actual_result,
            comments=comments,
            executed_by=request.user,
            executed_at=timezone.now()
        )
        
        # 更新执行用例状态
        run_case.status = new_status
        run_case.actual_result = actual_result
        run_case.comments = comments
        run_case.executed_by = request.user
        run_case.executed_at = timezone.now()
        run_case.save()
        
        return Response(TestRunCaseDetailSerializer(run_case).data)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        获取用例执行历史记录
        """
        run_case = self.get_object()
        history = run_case.history.all().order_by('-executed_at')
        serializer = TestRunCaseHistorySerializer(history, many=True)
        return Response(serializer.data)

class TestRunCaseHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    测试执行历史视图集（只读）
    """
    queryset = TestRunCaseHistory.objects.all().order_by('-executed_at')
    serializer_class = TestRunCaseHistorySerializer
