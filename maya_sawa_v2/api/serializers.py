from rest_framework import serializers
from maya_sawa_v2.conversations.models import Conversation, Message
from maya_sawa_v2.ai_processing.models import ProcessingTask, AIModel
from maya_sawa_v2.ai_processing.utils import AIProviderConfig, ModelNameMapper


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'message_type', 'content', 'metadata', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'session_id', 'conversation_type', 'status', 'title', 'messages', 'created_at', 'updated_at']

    def create(self, validated_data):
        """创建对话 - 根据认证状态设置用户"""
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # 如果用户已认证，设置用户
            validated_data['user'] = request.user
        else:
            # 如果未认证，使用默认用户或None
            from django.contrib.auth import get_user_model
            User = get_user_model()
            default_user = User.objects.filter(is_superuser=True).first()
            if default_user:
                validated_data['user'] = default_user

        return super().create(validated_data)


class AIModelSerializer(serializers.ModelSerializer):
    """AI 模型序列化器"""

    status = serializers.SerializerMethodField()
    provider_display_name = serializers.SerializerMethodField()

    class Meta:
        model = AIModel
        fields = ['id', 'name', 'provider', 'provider_display_name', 'model_id', 'is_active', 'status']

    def get_status(self, obj):
        """獲取模型狀態"""
        if obj.is_active:
            return "Available"
        else:
            return "Not Available"

    def get_provider_display_name(self, obj):
        """獲取提供者顯示名稱"""
        return ModelNameMapper.get_provider_display_name(obj.provider)


class CreateMessageSerializer(serializers.ModelSerializer):
    ai_model_id = serializers.IntegerField(required=False, help_text="選擇的 AI 模型 ID")

    class Meta:
        model = Message
        fields = ['content', 'ai_model_id']

    def validate_ai_model_id(self, value):
        """驗證 AI 模型是否存在且啟用"""
        if value:
            try:
                ai_model = AIModel.objects.get(id=value, is_active=True)
                return value
            except AIModel.DoesNotExist:
                raise serializers.ValidationError("指定的 AI 模型不存在或未啟用")
        return value

    def create(self, validated_data):
        conversation = self.context['conversation']
        ai_model_id = validated_data.pop('ai_model_id', None)

        message = Message.objects.create(
            conversation=conversation,
            message_type='user',
            content=validated_data['content']
        )

        # 觸發 AI 處理任務
        from maya_sawa_v2.ai_processing.tasks import process_ai_response

        # 獲取 AI 模型（優先使用前端指定的，否則使用預設）
        if ai_model_id:
            ai_model = AIModel.objects.get(id=ai_model_id, is_active=True)
        else:
            ai_model = AIModel.objects.filter(is_active=True).first()

        if ai_model:
            task = ProcessingTask.objects.create(
                conversation=conversation,
                message=message,
                ai_model=ai_model
            )
            process_ai_response.delay(task.id)

        return message


class ProcessingTaskSerializer(serializers.ModelSerializer):
    ai_model = AIModelSerializer(read_only=True)

    class Meta:
        model = ProcessingTask
        fields = ['id', 'status', 'result', 'processing_time', 'created_at', 'completed_at', 'ai_model']


class AIProviderConfigSerializer(serializers.Serializer):
    """AI 提供者配置序列化器"""

    provider = serializers.CharField()
    display_name = serializers.CharField()
    models = serializers.ListField(child=serializers.CharField())
    available_models = serializers.ListField(child=serializers.CharField())
    default_model = serializers.CharField(allow_null=True)
    enabled = serializers.BooleanField()
