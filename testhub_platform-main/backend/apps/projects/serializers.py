from rest_framework import serializers
from .models import Project, ProjectMember, ProjectEnvironment
from apps.users.serializers import UserSerializer

class ProjectSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ('id', 'name')

class ProjectEnvironmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectEnvironment
        fields = '__all__'
        extra_kwargs = {
            'project': {'read_only': True}
        }

class ProjectMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ProjectMember
        fields = ['id', 'user', 'user_id', 'role', 'joined_at']

def _validate_project_types(value):
    if value is None:
        return []
    if not isinstance(value, list):
        raise serializers.ValidationError('项目类型必须为列表')
    invalid = [t for t in value if t not in Project.VALID_PROJECT_TYPES]
    if invalid:
        raise serializers.ValidationError(f'无效的项目类型: {", ".join(invalid)}')
    # 去重并保持顺序
    seen = set()
    result = []
    for t in value:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


class ProjectSerializer(serializers.ModelSerializer):
    owner = UserSerializer(read_only=True)
    members = ProjectMemberSerializer(source='projectmember_set', many=True, read_only=True)
    environments = ProjectEnvironmentSerializer(many=True, read_only=True)
    
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'status', 'project_types', 'owner', 'members',
                 'environments', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_project_types(self, value):
        return _validate_project_types(value)

class ProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'status', 'project_types']
        read_only_fields = ['id']
    
    def validate_project_types(self, value):
        return _validate_project_types(value)

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        validated_data.setdefault('project_types', [])
        return super().create(validated_data)