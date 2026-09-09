from rest_framework import serializers
from .models import TestPlan, TestRun, TestRunCase, TestRunCaseHistory
from apps.testcases.models import TestCase
from apps.users.serializers import UserSimpleSerializer

class TestRunCaseHistorySerializer(serializers.ModelSerializer):
    executed_by = UserSimpleSerializer(read_only=True)
    version = serializers.SerializerMethodField()

    class Meta:
        model = TestRunCaseHistory
        fields = ('id', 'status', 'actual_result', 'comments', 'version', 'executed_by', 'executed_at')

    def get_version(self, obj):
        # 历史记录显示测试计划关联的版本，兼容历史数据未存版本的情况
        plan = obj.run_case.test_run.test_plan if obj.run_case and obj.run_case.test_run else None
        if plan and plan.version:
            return plan.version.name
        return obj.version.name if obj.version else None

class TestRunCaseSimpleSerializer(serializers.ModelSerializer):
    testcase = serializers.StringRelatedField()
    testcase_id = serializers.ReadOnlyField(source='testcase.id')
    l1 = serializers.CharField(source='testcase.l1', read_only=True)
    l2 = serializers.CharField(source='testcase.l2', read_only=True)
    l3 = serializers.CharField(source='testcase.l3', read_only=True)
    case_priority = serializers.CharField(source='testcase.priority', read_only=True)
    test_type = serializers.CharField(source='testcase.test_type', read_only=True)
    preconditions = serializers.CharField(source='testcase.preconditions', read_only=True)
    steps = serializers.CharField(source='testcase.steps', read_only=True)
    expected_result = serializers.CharField(source='testcase.expected_result', read_only=True)
    description = serializers.CharField(source='testcase.description', read_only=True)
    project_name = serializers.CharField(source='testcase.project.name', read_only=True)
    versions = serializers.SerializerMethodField()

    class Meta:
        model = TestRunCase
        fields = ('id', 'testcase', 'testcase_id', 'status', 'comments', 'l1', 'l2', 'l3',
                  'case_priority', 'test_type', 'preconditions', 'steps',
                  'expected_result', 'description', 'project_name', 'versions')

    def get_versions(self, obj):
        versions = obj.testcase.versions.all()
        return [{'id': v.id, 'name': v.name, 'is_baseline': v.is_baseline} for v in versions]

class TestRunCaseDetailSerializer(serializers.ModelSerializer):
    testcase = serializers.StringRelatedField()
    executed_by = UserSimpleSerializer(read_only=True)
    history = TestRunCaseHistorySerializer(many=True, read_only=True)
    
    class Meta:
        model = TestRunCase
        fields = ('id', 'testcase', 'status', 'priority', 'actual_result', 'comments', 
                 'defects', 'elapsed_time', 'executed_by', 'executed_at', 'created_at', 
                 'updated_at', 'history')

class TestRunSerializer(serializers.ModelSerializer):
    run_cases = TestRunCaseSimpleSerializer(many=True, read_only=True)
    progress = serializers.SerializerMethodField()

    class Meta:
        model = TestRun
        fields = ('id', 'name', 'status', 'assignee', 'progress', 'run_cases')
    
    def get_progress(self, obj):
        return obj.progress_stats


class TestPlanSerializer(serializers.ModelSerializer):
    creator = UserSimpleSerializer(read_only=True)
    projects = serializers.StringRelatedField(many=True, read_only=True)
    version = serializers.StringRelatedField()

    class Meta:
        model = TestPlan
        fields = ('id', 'name', 'projects', 'version', 'creator', 'created_at', 'is_active')


class TestPlanDetailSerializer(serializers.ModelSerializer):
    test_runs = TestRunSerializer(many=True, read_only=True)
    creator = UserSimpleSerializer(read_only=True)
    projects = serializers.StringRelatedField(many=True, read_only=True)
    version = serializers.StringRelatedField()

    class Meta:
        model = TestPlan
        fields = '__all__'

class TestRunCaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestRunCase
        fields = '__all__'
