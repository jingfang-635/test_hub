from rest_framework import generics, permissions, status, pagination
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models, transaction
import re
from .models import TestCase, TestCaseStep, TestCaseAttachment, TestCaseComment
from .serializers import (
    TestCaseSerializer, TestCaseListSerializer, TestCaseCreateSerializer, TestCaseUpdateSerializer
)
from apps.projects.models import Project
from apps.versions.models import Version

class TestCasePagination(pagination.PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class TestCaseListCreateView(generics.ListCreateAPIView):
    queryset = TestCase.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = TestCasePagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['priority', 'test_type', 'project', 'id']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TestCaseCreateSerializer
        return TestCaseListSerializer
    
    def get_queryset(self):
        user = self.request.user
        accessible_projects = Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        qs = TestCase.objects.filter(
            project__in=accessible_projects
        ).select_related(
            'author', 'assignee', 'project'
        ).prefetch_related(
            'versions', 'step_details'
        ).distinct()

        # 用例类型多选存储为 JSON 数组，按“包含某类型”筛选
        case_type = self.request.query_params.get('case_type')
        if case_type:
            qs = qs.filter(case_type__contains=[case_type])

        # 用例编号筛选：支持精确或部分匹配（编号即主键 id）
        case_number = self.request.query_params.get('id', '').strip()
        if case_number:
            qs = qs.filter(id__icontains=case_number)

        return qs
    def get_user_accessible_projects(self, user):
        """获取用户有权限访问的项目"""
        return Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
    
    def perform_create(self, serializer):
        user = self.request.user
        project_id = self.request.data.get('project_id')
        
        # 获取用户有权限的项目
        accessible_projects = self.get_user_accessible_projects(user)
        
        if project_id:
            # 检查指定的项目是否存在且用户有权限
            try:
                project = accessible_projects.get(id=project_id)
            except Project.DoesNotExist:
                # 如果指定项目不存在或无权限，使用第一个可访问的项目
                project = accessible_projects.first()
                if not project:
                    # 如果用户没有任何项目，创建默认项目
                    project = Project.objects.create(
                        name="默认项目",
                        owner=user,
                        description='系统自动创建的默认项目'
                    )
        else:
            # 没有指定项目，使用第一个可访问的项目
            project = accessible_projects.first()
            if not project:
                # 如果用户没有任何项目，创建默认项目
                project = Project.objects.create(
                    name="默认项目",
                    owner=user,
                    description='系统自动创建的默认项目'
                )
        
        serializer.save(author=user, project=project)

class TestCaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TestCase.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return TestCaseUpdateSerializer
        return TestCaseSerializer
    
    def get_queryset(self):
        user = self.request.user
        accessible_projects = Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return TestCase.objects.filter(
            project__in=accessible_projects
        ).select_related(
            'author', 'assignee', 'project'
        ).prefetch_related(
            'versions', 'step_details', 'attachments', 'comments'
        )
    
    def get_user_accessible_projects(self, user):
        """获取用户有权限访问的项目"""
        return Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
    
    def perform_update(self, serializer):
        user = self.request.user
        project_id = self.request.data.get('project_id')
        
        if project_id:
            # 检查指定的项目是否存在且用户有权限
            accessible_projects = self.get_user_accessible_projects(user)
            try:
                project = accessible_projects.get(id=project_id)
                serializer.save(project=project)
            except Project.DoesNotExist:
                # 如果指定项目不存在或无权限，保持原项目不变
                serializer.save()
        else:
            # 没有指定项目，保持原项目不变
            serializer.save()


# ========== 用例详情 - UI自动化 tab 只读步骤详情（含元素/选择器/输入值） ==========

class TestCaseUiStepDetailView(generics.RetrieveAPIView):
    """返回用例对应的 UI自动化用例的结构化只读步骤。

    优先通过 ui_test_cases.hub_testcase 一对一关联定位；兼容历史命名
    「{标题}-AI生成步骤」。供用例详情「UI自动化」tab 只读展示，不做业务写入
    （仅在命中历史命名时补绑 FK）。
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        user = request.user

        # 权限校验：仅允许访问用户可访问项目下的用例
        accessible_projects = Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        try:
            testcase = TestCase.objects.select_related('project').get(pk=pk, project__in=accessible_projects)
        except TestCase.DoesNotExist:
            return Response({'error': '用例不存在或无权访问'}, status=status.HTTP_404_NOT_FOUND)

        from apps.ui_automation.models import (
            UiProject as UiProjectModel, TestCase as UiTestCase, TestCaseStep as UiTestCaseStep,
        )

        # 定位关联的 UI自动化用例：优先 hub_testcase 一对一 FK，兼容旧命名规则
        ui_case = UiTestCase.objects.filter(hub_testcase_id=testcase.id).first()
        if not ui_case:
            ui_project = UiProjectModel.objects.filter(hub_project=testcase.project).first()
            if not ui_project:
                return Response({'ui_case_id': None, 'steps': []})
            expected_name = f'{testcase.title or ""}-AI生成步骤'
            ui_case = UiTestCase.objects.filter(
                project=ui_project, name=expected_name
            ).order_by('id').first()
            if not ui_case and testcase.title:
                ui_case = (
                    UiTestCase.objects.filter(
                        project=ui_project,
                        hub_testcase__isnull=True,
                        name__endswith='-AI生成步骤',
                        name__startswith=testcase.title,
                    )
                    .order_by('id')
                    .first()
                )
            # 历史数据补绑 FK，后续重复生成走更新而非新建
            if ui_case and not ui_case.hub_testcase_id:
                ui_case.hub_testcase = testcase
                ui_case.save(update_fields=['hub_testcase', 'updated_at'])
        if not ui_case:
            return Response({'ui_case_id': None, 'steps': []})

        steps = UiTestCaseStep.objects.filter(test_case=ui_case).select_related(
            'element', 'element__locator_strategy'
        ).order_by('step_number')

        def element_data(el):
            if not el:
                return None
            return {
                'id': el.id,
                'name': el.name,
                'locator_strategy': el.locator_strategy.name if el.locator_strategy_id else '',
                'locator_value': el.locator_value,
                'backup_locators': el.backup_locators or [],
                'screenshot': el.screenshot.url if el.screenshot else '',
                'page': el.page,
                'wait_timeout': el.wait_timeout,
            }

        data = []
        for s in steps:
            data.append({
                'id': s.id,
                'step_number': s.step_number,
                'action_type': s.action_type,
                'description': s.description,
                'page_filter': s.page_filter,
                'element': element_data(s.element),
                'input_value': s.input_value,
                'wait_time': s.wait_time,
                'assert_type': s.assert_type,
                'assert_value': s.assert_value,
            })
        return Response({'ui_case_id': ui_case.id, 'ui_case_name': ui_case.name, 'steps': data})


# ========== Excel 批量导入 ==========

# 优先级/测试类型 中文 -> 代码 映射，兼容直接传代码
# 优先级已迁移为 P0/P1/P2/P3，同时兼容旧值 low/medium/high/critical 和中文
PRIORITY_MAP = {
    'P0': 'P0', 'P1': 'P1', 'P2': 'P2', 'P3': 'P3',
    '紧急': 'P0', '高': 'P1', '中': 'P2', '低': 'P3',
    'critical': 'P0', 'high': 'P1', 'medium': 'P2', 'low': 'P3',
}

TYPE_MAP = {
    '功能测试': 'functional', 'functional': 'functional',
    '集成测试': 'integration', 'integration': 'integration',
    'API测试': 'api', 'api': 'api',
    'UI测试': 'ui', 'ui': 'ui',
    '性能测试': 'performance', 'performance': 'performance',
    '安全测试': 'security', 'security': 'security',
}

CASE_TYPE_MAP = {
    '手工': 'manual', 'manual': 'manual',
    'UI': 'ui', 'ui': 'ui',
    '接口': 'api', 'api': 'api',
}


def parse_case_types(raw_value):
    """解析导入的用例类型（支持多选，分隔符：,，、;；）"""
    text = str(raw_value or '').strip()
    if not text:
        return None
    parts = [p.strip() for p in re.split(r'[,，、;；]', text) if p.strip()]
    result = []
    seen = set()
    for part in parts:
        mapped = CASE_TYPE_MAP.get(part)
        if mapped and mapped not in seen:
            seen.add(mapped)
            result.append(mapped)
    return result or None


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def import_testcases_view(request):
    """批量导入测试用例（全有或全无）：
    - 用例编号为空 -> 新增用例
    - 用例编号已存在 -> 更新用例(只更新导入的字段)
    - 除前置条件和备注外,其余字段必填
    - 任一行校验/写入失败则整批不导入，并返回全部报错信息
    """
    cases = request.data.get('cases')
    if not isinstance(cases, list):
        return Response({'detail': '请求体需包含 cases 列表'}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user
    accessible_projects = Project.objects.filter(
        models.Q(owner=user) | models.Q(members=user)
    ).distinct()

    # 解析用户项目名 -> 项目对象(按名匹配,取第一个匹配项)
    project_name_map = {}
    for p in accessible_projects:
        project_name_map.setdefault(p.name, p)

    def resolve_project(project_name, project_id):
        if project_id:
            try:
                return accessible_projects.get(id=project_id)
            except Project.DoesNotExist:
                pass
        if project_name:
            name = str(project_name).strip()
            if name in project_name_map:
                return project_name_map[name]
        return None

    # 必填字段(除前置条件和备注外)
    REQUIRED_FIELDS = [
        ('title', '用例标题'),
        ('steps', '操作步骤'),
        ('expected_result', '预期结果'),
        ('project_name', '关联项目'),
        ('versions', '关联版本'),
        ('priority', '优先级'),
        ('test_type', '测试类型'),
        ('l1', 'L1'),
        ('l2', 'L2'),
        ('l3', 'L3'),
    ]

    errors = []
    prepared = []  # 通过校验、待写入的数据

    for idx, case in enumerate(cases, start=1):
        title = str(case.get('title', '')).strip()

        # 先解析用例编号:空 -> 新增; 非空 -> 查找,找到则更新,找不到则报错
        case_number = str(case.get('case_number', '')).strip()
        existing_instance = None
        if case_number:
            try:
                existing_instance = TestCase.objects.get(pk=case_number)
            except (TestCase.DoesNotExist, ValueError):
                existing_instance = None
            if not existing_instance:
                errors.append({
                    'row': idx,
                    'title': title,
                    'message': f'用例编号 {case_number} 不存在,无法更新'
                })
                continue

        # 仅新增时做必填校验;更新时不校验,只更新导入的字段
        if not existing_instance:
            missing = []
            for field, label in REQUIRED_FIELDS:
                val = str(case.get(field, '')).strip()
                if not val:
                    missing.append(label)
            if missing:
                errors.append({
                    'row': idx,
                    'title': title,
                    'message': '以下字段必填: ' + '、'.join(missing)
                })
                continue

        # 解析项目:更新时若 Excel 项目名为空则保持原项目,不更新
        project_name_val = str(case.get('project_name', '')).strip()
        project = None
        create_project_name = None
        if project_name_val or case.get('project_id'):
            project = resolve_project(project_name_val, case.get('project_id'))
        # 新增时必须解析到项目;解析不到则后续在事务中新建同名项目
        if not existing_instance and not project:
            create_project_name = project_name_val or '默认项目'

        # 解析版本(按顿号/逗号分隔,优先匹配当前项目下的版本)
        # 更新时若 Excel 版本为空则不更新关联,保持原关联
        version_str = str(case.get('versions', '')).strip()
        versions = None  # None 表示 Excel 未提供版本(更新时跳过);新增时为空列表
        if version_str:
            version_names = [v.strip() for v in re.split(r'[、,，;；]', version_str) if v.strip()]
            # 清理版本名中的"(基线)"/"(baseline)"等括号后缀(导出时基线版本会附加此标记)
            version_names = [re.sub(r'\s*[\(（].*?[\)）]\s*$', '', v).strip() for v in version_names]
            version_names = [v for v in version_names if v]
            proj_for_versions = project or (existing_instance.project if existing_instance else None)
            project_versions = (
                Version.objects.filter(projects=proj_for_versions)
                if proj_for_versions else Version.objects.none()
            )
            versions = []
            for vname in version_names:
                v = project_versions.filter(name=vname).first()
                if not v:
                    # 回退到全局按名匹配
                    v = Version.objects.filter(name=vname).first()
                if v:
                    versions.append(v)

        # 优先级/测试类型:空时不更新
        priority_val = str(case.get('priority', '')).strip()
        priority = PRIORITY_MAP.get(priority_val, 'P2') if priority_val else None
        test_type_val = str(case.get('test_type', '')).strip()
        test_type = TYPE_MAP.get(test_type_val, 'functional') if test_type_val else None
        case_type_val = str(case.get('case_type', '')).strip()
        case_type = parse_case_types(case_type_val)

        prepared.append({
            'row': idx,
            'title': title,
            'case': case,
            'existing_instance': existing_instance,
            'project': project,
            'create_project_name': create_project_name,
            'versions': versions,
            'priority': priority,
            'test_type': test_type,
            'case_type': case_type,
        })

    # 任一报错：整批不导入
    if errors:
        return Response({
            'success_count': 0,
            'created_count': 0,
            'updated_count': 0,
            'fail_count': len(errors),
            'errors': errors,
        }, status=status.HTTP_400_BAD_REQUEST)

    created_count = 0
    updated_count = 0

    try:
        with transaction.atomic():
            for item in prepared:
                case = item['case']
                title = item['title']
                existing_instance = item['existing_instance']
                project = item['project']
                versions = item['versions']
                priority = item['priority']
                test_type = item['test_type']
                case_type = item['case_type']

                # 事务内按需创建项目（同名复用）
                if not project and item['create_project_name']:
                    name = item['create_project_name']
                    if name in project_name_map:
                        project = project_name_map[name]
                    else:
                        project = Project.objects.create(
                            name=name,
                            owner=user,
                            description='Excel 导入自动创建'
                        )
                        project_name_map[project.name] = project

                if existing_instance:
                    # 更新:只更新 Excel 中非空的字段,空字段保持原值
                    instance = existing_instance
                    if title:
                        instance.title = title
                    steps_val = str(case.get('steps', '')).strip()
                    if steps_val:
                        instance.steps = steps_val[:1000]
                    expected_val = str(case.get('expected_result', '')).strip()
                    if expected_val:
                        instance.expected_result = expected_val
                    if priority:
                        instance.priority = priority
                    if test_type:
                        instance.test_type = test_type
                    if case_type:
                        instance.case_type = case_type
                    l1_val = str(case.get('l1', '')).strip()
                    if l1_val:
                        instance.l1 = l1_val[:500]
                    l2_val = str(case.get('l2', '')).strip()
                    if l2_val:
                        instance.l2 = l2_val[:500]
                    l3_val = str(case.get('l3', '')).strip()
                    if l3_val:
                        instance.l3 = l3_val[:500]
                    if project:
                        instance.project = project
                    desc_val = str(case.get('description', '')).strip()
                    if desc_val:
                        instance.description = desc_val
                    pre_val = str(case.get('preconditions', '')).strip()
                    if pre_val:
                        instance.preconditions = pre_val
                    instance.save()
                    # 版本关联:仅在 Excel 提供了版本字段时才更新
                    if versions is not None and versions:
                        instance.versions.set(versions)
                    updated_count += 1
                else:
                    # 新增(必填校验已通过,字段一定有值)
                    instance = TestCase.objects.create(
                        title=title,
                        description=str(case.get('description', '')).strip(),
                        preconditions=str(case.get('preconditions', '')).strip(),
                        steps=str(case.get('steps', '')).strip()[:1000],
                        expected_result=str(case.get('expected_result', '')).strip(),
                        priority=priority or 'P2',
                        case_type=case_type or ['manual'],
                        test_type=test_type or 'functional',
                        l1=str(case.get('l1', '')).strip()[:500],
                        l2=str(case.get('l2', '')).strip()[:500],
                        l3=str(case.get('l3', '')).strip()[:500],
                        tags=[],
                        author=user,
                        project=project,
                    )
                    if versions:
                        instance.versions.set(versions)
                    created_count += 1
    except Exception as e:
        return Response({
            'success_count': 0,
            'created_count': 0,
            'updated_count': 0,
            'fail_count': 1,
            'errors': [{'row': 0, 'title': '', 'message': f'导入写入失败，已全部回滚: {e}'}],
        }, status=status.HTTP_400_BAD_REQUEST)

    success_count = created_count + updated_count
    return Response({
        'success_count': success_count,
        'created_count': created_count,
        'updated_count': updated_count,
        'fail_count': 0,
        'errors': [],
    }, status=status.HTTP_200_OK)
