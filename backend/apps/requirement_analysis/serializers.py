from rest_framework import serializers
from .models import (
    RequirementDocument, RequirementAnalysis, BusinessRequirement,
    GeneratedTestCase, AnalysisTask, AIModelConfig, PromptConfig, TestCaseGenerationTask,
    GenerationConfig, KnowledgeBase, KnowledgeDocument, KnowledgeBaseLLMConfig
)


class RequirementDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = RequirementDocument
        fields = ['id', 'title', 'file', 'file_url', 'document_type', 'document_type_display', 
                 'status', 'status_display', 'uploaded_by', 'uploaded_by_name', 'project', 
                 'project_name', 'created_at', 'updated_at', 'file_size', 'extracted_text']
        read_only_fields = ['uploaded_by', 'file_size', 'extracted_text']
    
    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None


class BusinessRequirementSerializer(serializers.ModelSerializer):
    requirement_type_display = serializers.CharField(source='get_requirement_type_display', read_only=True)
    requirement_level_display = serializers.CharField(source='get_requirement_level_display', read_only=True)
    parent_requirement_name = serializers.CharField(source='parent_requirement.requirement_name', read_only=True)
    
    class Meta:
        model = BusinessRequirement
        fields = ['id', 'requirement_id', 'requirement_name', 'requirement_type', 
                 'requirement_type_display', 'parent_requirement', 'parent_requirement_name',
                 'module', 'requirement_level', 'requirement_level_display', 'reviewer', 
                 'estimated_hours', 'description', 'acceptance_criteria', 'created_at', 'updated_at']


class RequirementAnalysisSerializer(serializers.ModelSerializer):
    document_title = serializers.CharField(source='document.title', read_only=True)
    document_id = serializers.IntegerField(source='document.id', read_only=True)
    requirements = BusinessRequirementSerializer(many=True, read_only=True)
    
    class Meta:
        model = RequirementAnalysis
        fields = ['id', 'document_id', 'document_title', 'analysis_report', 
                 'requirements_count', 'analysis_time', 'created_at', 'updated_at', 'requirements']


class GeneratedTestCaseSerializer(serializers.ModelSerializer):
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    requirement_name = serializers.CharField(source='requirement.requirement_name', read_only=True)
    requirement_id_display = serializers.CharField(source='requirement.requirement_id', read_only=True)
    
    class Meta:
        model = GeneratedTestCase
        fields = ['id', 'case_id', 'title', 'priority', 'priority_display', 'precondition',
                 'test_steps', 'expected_result', 'status', 'status_display', 'generated_by_ai',
                 'reviewed_by_ai', 'review_comments', 'requirement', 'requirement_name', 
                 'requirement_id_display', 'created_at', 'updated_at']


class AnalysisTaskSerializer(serializers.ModelSerializer):
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    document_title = serializers.CharField(source='document.title', read_only=True)
    duration = serializers.SerializerMethodField()
    
    class Meta:
        model = AnalysisTask
        fields = ['id', 'task_id', 'task_type', 'task_type_display', 'document', 'document_title',
                 'status', 'status_display', 'progress', 'result', 'error_message', 
                 'started_at', 'completed_at', 'created_at', 'duration']
        read_only_fields = ['task_id', 'result', 'error_message', 'started_at', 'completed_at']
    
    def get_duration(self, obj):
        if obj.started_at and obj.completed_at:
            return (obj.completed_at - obj.started_at).total_seconds()
        return None


class DocumentUploadSerializer(serializers.ModelSerializer):
    """文档上传专用序列化器"""
    class Meta:
        model = RequirementDocument
        fields = ['id', 'title', 'file', 'project']
    
    def create(self, validated_data):
        # 自动设置上传者（如果用户已登录）
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['uploaded_by'] = user
        else:
            # 如果是匿名用户，使用第一个超级用户作为默认用户
            from apps.users.models import User
            default_user = User.objects.filter(is_superuser=True).first()
            if not default_user:
                default_user = User.objects.first()
            validated_data['uploaded_by'] = default_user
        
        # 根据文件扩展名设置文档类型
        file = validated_data['file']
        if file.name.lower().endswith('.pdf'):
            validated_data['document_type'] = 'pdf'
        elif file.name.lower().endswith(('.doc', '.docx')):
            validated_data['document_type'] = 'docx'
        elif file.name.lower().endswith('.txt'):
            validated_data['document_type'] = 'txt'
        elif file.name.lower().endswith('.md'):
            validated_data['document_type'] = 'md'
        
        # 设置文件大小
        validated_data['file_size'] = file.size
        
        return super().create(validated_data)


class LegacyTestCaseGenerationRequestSerializer(serializers.Serializer):
    """旧版：基于 BusinessRequirement 列表生成测试用例的请求序列化器"""
    requirement_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="需求ID列表"
    )
    test_level = serializers.ChoiceField(
        choices=[('unit', '单元测试'), ('integration', '集成测试'), ('system', '系统测试'), ('acceptance', '验收测试')],
        default='system',
        help_text="测试级别"
    )
    test_priority = serializers.ChoiceField(
        choices=[('P0', '最高优先级'), ('P1', '高优先级'), ('P2', '中优先级'), ('P3', '低优先级')],
        default='P1',
        help_text="测试优先级"
    )
    test_case_count = serializers.IntegerField(
        min_value=1,
        max_value=200,
        default=50,
        help_text="生成测试用例数量"
    )


class TestCaseReviewRequestSerializer(serializers.Serializer):
    """测试用例评审请求序列化器"""
    test_case_ids = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="测试用例ID列表"
    )
    review_criteria = serializers.CharField(
        max_length=500,
        default="检查测试用例的完整性、准确性和可执行性",
        help_text="评审标准"
    )


class AIModelConfigSerializer(serializers.ModelSerializer):
    """AI模型配置序列化器"""
    model_type_display = serializers.CharField(source='get_model_type_display', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    api_key_masked = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = AIModelConfig
        fields = ['id', 'name', 'model_type', 'model_type_display', 'role', 'role_display',
                 'api_key', 'api_key_masked', 'base_url', 'model_name', 'max_tokens', 'temperature', 'top_p', 
                 'is_active', 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_by_name']
        extra_kwargs = {
            'api_key': {'write_only': True}  # API Key只用于写入，不在响应中返回
        }
    
    def get_api_key_masked(self, obj):
        """返回掩码版本的API Key"""
        if obj.api_key:
            # 显示前3个字符和后4个字符，中间用*替代
            if len(obj.api_key) > 7:
                return f"{obj.api_key[:3]}{'*' * (len(obj.api_key) - 7)}{obj.api_key[-4:]}"
            else:
                return '*' * len(obj.api_key)
        return ''
    
    def create(self, validated_data):
        # 自动设置创建者
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['created_by'] = user
        else:
            # 如果是匿名用户，使用第一个超级用户作为默认用户
            from apps.users.models import User
            default_user = User.objects.filter(is_superuser=True).first()
            if not default_user:
                default_user = User.objects.first()
            validated_data['created_by'] = default_user
        
        return super().create(validated_data)


class PromptConfigSerializer(serializers.ModelSerializer):
    """提示词配置序列化器"""
    prompt_type_display = serializers.CharField(source='get_prompt_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = PromptConfig
        fields = ['id', 'name', 'prompt_type', 'prompt_type_display', 'content', 'is_active',
                 'created_by', 'created_by_name', 'created_at', 'updated_at']
        read_only_fields = ['created_by', 'created_by_name']
    
    def create(self, validated_data):
        # 自动设置创建者
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['created_by'] = user
        else:
            # 如果是匿名用户，使用第一个超级用户作为默认用户
            from apps.users.models import User
            default_user = User.objects.filter(is_superuser=True).first()
            if not default_user:
                default_user = User.objects.first()
            validated_data['created_by'] = default_user
        
        return super().create(validated_data)


class TestCaseGenerationTaskSerializer(serializers.ModelSerializer):
    """测试用例生成任务序列化器"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    writer_model_name = serializers.CharField(source='writer_model_config.name', read_only=True)
    reviewer_model_name = serializers.CharField(source='reviewer_model_config.name', read_only=True)
    writer_prompt_name = serializers.CharField(source='writer_prompt_config.name', read_only=True)
    reviewer_prompt_name = serializers.CharField(source='reviewer_prompt_config.name', read_only=True)
    
    class Meta:
        model = TestCaseGenerationTask
        fields = ['id', 'task_id', 'title', 'requirement_text', 'status', 'status_display',
                 'progress', 'source_type', 'source_type_display', 'source_url',
                 'project', 'project_name', 'writer_model_config', 'writer_model_name', 
                 'reviewer_model_config', 'reviewer_model_name', 'writer_prompt_config', 'writer_prompt_name',
                 'reviewer_prompt_config', 'reviewer_prompt_name', 'generated_test_cases',
                 'review_feedback', 'final_test_cases', 'generation_log', 'error_message',
                 'created_by', 'created_by_name', 'created_at', 'updated_at', 'completed_at']
        read_only_fields = ['task_id', 'status', 'progress', 'generated_test_cases', 
                          'review_feedback', 'final_test_cases', 'generation_log', 
                          'error_message', 'created_by', 'completed_at']
    
    def create(self, validated_data):
        # 自动设置创建者和任务ID
        import uuid
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['created_by'] = user
        else:
            from apps.users.models import User
            default_user = User.objects.filter(is_superuser=True).first()
            if not default_user:
                default_user = User.objects.first()
            validated_data['created_by'] = default_user
        
        validated_data['task_id'] = f"TASK_{uuid.uuid4().hex[:8].upper()}"
        
        return super().create(validated_data)


class TestCaseGenerationRequestSerializer(serializers.Serializer):
    """新的测试用例生成请求序列化器"""
    title = serializers.CharField(max_length=200, help_text="任务标题")
    requirement_text = serializers.CharField(help_text="需求描述")
    use_writer_model = serializers.BooleanField(default=True, help_text="是否使用编写模型")
    use_reviewer_model = serializers.BooleanField(default=True, help_text="是否使用评审模型")
    project = serializers.IntegerField(required=False, allow_null=True, help_text="关联项目ID")
    source_type = serializers.ChoiceField(
        choices=['manual', 'upload', 'feishu', 'figma'],
        required=False,
        default='manual',
        help_text="需求来源类型",
    )
    source_url = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=1000,
        help_text="需求来源链接",
    )


class FeishuFetchRequestSerializer(serializers.Serializer):
    """飞书文档拉取请求"""
    url = serializers.CharField(max_length=1000, help_text="飞书文档或 Wiki 链接")


class FigmaFetchRequestSerializer(serializers.Serializer):
    """Figma 设计稿拉取请求"""
    url = serializers.CharField(max_length=1000, help_text="Figma 设计稿链接")


class GenerationConfigSerializer(serializers.ModelSerializer):
    """生成行为配置序列化器"""
    default_output_mode_display = serializers.CharField(source='get_default_output_mode_display', read_only=True)

    class Meta:
        model = GenerationConfig
        fields = [
            'id', 'name', 'default_output_mode', 'default_output_mode_display',
            'enable_auto_review', 'review_timeout',
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class KnowledgeBaseLLMConfigSerializer(serializers.ModelSerializer):
    """知识库大模型配置序列化器"""
    embedding_api_key_masked = serializers.SerializerMethodField(read_only=True)
    refiner_api_key_masked = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = KnowledgeBaseLLMConfig
        fields = [
            'id',
            'embedding_api_key', 'embedding_api_key_masked',
            'embedding_base_url', 'embedding_model_name',
            'refiner_api_key', 'refiner_api_key_masked',
            'refiner_base_url', 'refiner_model_name',
            'refiner_max_tokens', 'refiner_temperature',
            'tika_server_url',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']
        extra_kwargs = {
            # 配置中心需回显完整 Key，供「显示密码」查看；空值在 update 时保留原值
            'embedding_api_key': {'required': False, 'allow_blank': True},
            'refiner_api_key': {'required': False, 'allow_blank': True},
            'tika_server_url': {'required': False},
        }

    def get_embedding_api_key_masked(self, obj):
        return KnowledgeBaseLLMConfig.mask_api_key(obj.embedding_api_key)

    def get_refiner_api_key_masked(self, obj):
        return KnowledgeBaseLLMConfig.mask_api_key(obj.refiner_api_key)

    def _normalize_api_keys(self, validated_data, instance=None):
        """忽略空值/掩码值，更新时保留原 Key"""
        for field in ('embedding_api_key', 'refiner_api_key'):
            if field not in validated_data:
                continue
            value = validated_data.get(field)
            if value is None:
                validated_data.pop(field, None)
                continue
            if isinstance(value, str):
                value = value.strip()
                # 前端可能回传掩码（含 *），视为未修改
                if (not value) or ('*' in value):
                    if instance is not None:
                        validated_data.pop(field, None)
                    else:
                        validated_data[field] = ''
                else:
                    validated_data[field] = value
        return validated_data

    def create(self, validated_data):
        validated_data = self._normalize_api_keys(validated_data)
        if not validated_data.get('tika_server_url'):
            validated_data['tika_server_url'] = KnowledgeBaseLLMConfig.DEFAULT_TIKA_SERVER_URL
        request = self.context.get('request')
        if request and getattr(request, 'user', None) and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self._normalize_api_keys(validated_data, instance=instance)
        tika_url = validated_data.get('tika_server_url')
        if isinstance(tika_url, str):
            tika_url = tika_url.strip()
            if tika_url:
                validated_data['tika_server_url'] = tika_url.rstrip('/')
            else:
                validated_data.pop('tika_server_url', None)
        return super().update(instance, validated_data)


class KnowledgeDocumentSerializer(serializers.ModelSerializer):
    """知识库文档序列化器"""
    uploaded_by_name = serializers.CharField(source='uploaded_by.username', read_only=True)
    document_type_display = serializers.CharField(source='get_document_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    file_url = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeDocument
        fields = [
            'id', 'knowledge_base', 'title', 'file', 'file_url', 'file_name',
            'document_type', 'document_type_display', 'status', 'status_display',
            'uploaded_by', 'uploaded_by_name', 'file_size', 'extracted_text',
            'chunk_count', 'is_vectorized', 'error_message', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'uploaded_by', 'document_type', 'file_size', 'extracted_text',
            'chunk_count', 'is_vectorized', 'error_message', 'status',
            'created_at', 'updated_at'
        ]

    def get_file_url(self, obj):
        if obj.file:
            return obj.file.url
        return None

    def get_file_name(self, obj):
        if obj.file:
            return obj.file.name.split('/')[-1]
        return ''


class KnowledgeDocumentUploadSerializer(serializers.ModelSerializer):
    """知识库文档上传序列化器"""
    ALLOWED_EXTENSIONS = ('.pdf', '.doc', '.docx', '.txt', '.md')

    class Meta:
        model = KnowledgeDocument
        fields = ['id', 'knowledge_base', 'title', 'file']

    def validate_file(self, value):
        name = (value.name or '').lower()
        if not name.endswith(self.ALLOWED_EXTENSIONS):
            raise serializers.ValidationError(
                '仅支持上传 PDF、Word（.doc/.docx）、Markdown（.md）、TXT 格式文件'
            )
        max_size = 50 * 1024 * 1024  # 50MB
        if value.size and value.size > max_size:
            raise serializers.ValidationError('文件大小不能超过 50MB')
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['uploaded_by'] = user
        else:
            from apps.users.models import User
            default_user = User.objects.filter(is_superuser=True).first() or User.objects.first()
            validated_data['uploaded_by'] = default_user

        file = validated_data['file']
        name = file.name.lower()
        if name.endswith('.pdf'):
            validated_data['document_type'] = 'pdf'
        elif name.endswith(('.doc', '.docx')):
            validated_data['document_type'] = 'docx'
        elif name.endswith('.txt'):
            validated_data['document_type'] = 'txt'
        elif name.endswith('.md'):
            validated_data['document_type'] = 'md'

        if not validated_data.get('title'):
            validated_data['title'] = file.name.rsplit('.', 1)[0]

        validated_data['file_size'] = file.size
        validated_data['status'] = 'uploaded'
        return super().create(validated_data)


class KnowledgeBaseSerializer(serializers.ModelSerializer):
    """知识库序列化器"""
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)
    document_count = serializers.SerializerMethodField()
    total_size = serializers.SerializerMethodField()

    class Meta:
        model = KnowledgeBase
        fields = [
            'id', 'name', 'description', 'is_active',
            'chunk_size', 'chunk_overlap', 'enable_vectorization',
            'created_by', 'created_by_name',
            'project', 'project_name', 'document_count', 'total_size',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_by', 'created_at', 'updated_at']

    def get_document_count(self, obj):
        return obj.documents.count()

    def get_total_size(self, obj):
        from django.db.models import Sum
        result = obj.documents.aggregate(total=Sum('file_size'))
        return result['total'] or 0

    def create(self, validated_data):
        user = self.context['request'].user
        if user.is_authenticated:
            validated_data['created_by'] = user
        return super().create(validated_data)
