from rest_framework import serializers
from .models import TestCase, TestCaseStep, TestCaseAttachment, TestCaseComment
from apps.users.serializers import UserSerializer
from apps.versions.serializers import VersionSimpleSerializer
from apps.projects.models import Project

class TestCaseStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCaseStep
        fields = '__all__'

class TestCaseAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by = UserSerializer(read_only=True)
    
    class Meta:
        model = TestCaseAttachment
        fields = '__all__'

class TestCaseCommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    
    class Meta:
        model = TestCaseComment
        fields = '__all__'

class ProjectSimpleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()

class TestCaseSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    assignee = UserSerializer(read_only=True)
    project = ProjectSimpleSerializer(read_only=True)
    versions = VersionSimpleSerializer(many=True, read_only=True)
    step_details = TestCaseStepSerializer(many=True, read_only=True)
    attachments = TestCaseAttachmentSerializer(many=True, read_only=True)
    comments = TestCaseCommentSerializer(many=True, read_only=True)
    
    class Meta:
        model = TestCase
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']

class TestCaseListSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    assignee = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()
    versions = serializers.SerializerMethodField()

    class Meta:
        model = TestCase
        fields = [
            'id', 'title', 'description', 'preconditions', 'steps', 'expected_result',
            'priority', 'test_type', 'l1', 'l2', 'l3',
            'author', 'assignee', 'project', 'versions', 'tags', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_author(self, obj):
        return {'id': obj.author.id, 'username': obj.author.username} if obj.author else None
    
    def get_assignee(self, obj):
        return {'id': obj.assignee.id, 'username': obj.assignee.username} if obj.assignee else None
    
    def get_project(self, obj):
        return {'id': obj.project.id, 'name': obj.project.name} if obj.project else None
    
    def get_versions(self, obj):
        return [{'id': v.id, 'name': v.name, 'is_baseline': v.is_baseline} for v in obj.versions.all()]

class TestCaseCreateSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(required=False, allow_null=True, help_text="项目ID，可选")
    version_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        help_text="关联版本ID列表"
    )

    class Meta:
        model = TestCase
        fields = [
            'title', 'description', 'preconditions', 'steps', 'expected_result',
            'priority', 'test_type', 'l1', 'l2', 'l3', 'tags', 'project_id', 'version_ids'
        ]

    def validate_title(self, value):
        """用例标题不可重复"""
        if not value or not value.strip():
            return value
        if TestCase.objects.filter(title=value.strip()).exists():
            raise serializers.ValidationError('用例标题已存在，请勿重复创建')
        return value

    def validate(self, attrs):
        """L1 必须与归属项目名一致"""
        project_id = attrs.get('project_id')
        l1 = attrs.get('l1')
        if project_id and l1:
            try:
                project = Project.objects.get(pk=project_id)
            except Project.DoesNotExist:
                raise serializers.ValidationError({'project_id': '归属项目不存在'})
            if l1.strip() != project.name:
                raise serializers.ValidationError({
                    'l1': f'L1 的值必须与归属项目名一致（应为：{project.name}）'
                })
        return attrs

    def create(self, validated_data):
        version_ids = validated_data.pop('version_ids', [])
        # project_id会在视图的perform_create中处理
        validated_data.pop('project_id', None)
        
        testcase = super().create(validated_data)
        
        # 设置版本关联
        if version_ids:
            testcase.versions.set(version_ids)
        
        return testcase

class TestCaseUpdateSerializer(serializers.ModelSerializer):
    project_id = serializers.IntegerField(required=False, allow_null=True, help_text="项目ID，可选")
    version_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True,
        help_text="关联版本ID列表"
    )

    class Meta:
        model = TestCase
        fields = [
            'title', 'description', 'preconditions', 'steps', 'expected_result',
            'priority', 'test_type', 'l1', 'l2', 'l3', 'tags', 'project_id', 'version_ids'
        ]

    def validate_title(self, value):
        """用例标题不可重复（编辑时排除自身）"""
        if not value or not value.strip():
            return value
        qs = TestCase.objects.filter(title=value.strip())
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError('用例标题已存在，请勿重复')
        return value

    def validate(self, attrs):
        """L1 必须与归属项目名一致"""
        # 编辑时若未传 project_id / l1，从 instance 取当前值
        project_id = attrs.get('project_id')
        if project_id is None and self.instance:
            project_id = self.instance.project_id
        l1 = attrs.get('l1')
        if l1 is None and self.instance:
            l1 = self.instance.l1
        if project_id and l1:
            try:
                project = Project.objects.get(pk=project_id)
            except Project.DoesNotExist:
                raise serializers.ValidationError({'project_id': '归属项目不存在'})
            if l1.strip() != project.name:
                raise serializers.ValidationError({
                    'l1': f'L1 的值必须与归属项目名一致（应为：{project.name}）'
                })
        return attrs

    def update(self, instance, validated_data):
        version_ids = validated_data.pop('version_ids', None)
        # project_id会在视图中处理
        validated_data.pop('project_id', None)
        
        instance = super().update(instance, validated_data)
        
        # 更新版本关联
        if version_ids is not None:
            instance.versions.set(version_ids)

        return instance

