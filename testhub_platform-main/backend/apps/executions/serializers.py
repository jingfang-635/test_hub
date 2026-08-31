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
    class Meta:
        model = TestRunCase
        fields = ('id', 'testcase', 'status')

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
