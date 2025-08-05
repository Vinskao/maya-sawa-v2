from rest_framework import serializers
from maya_sawa_v2.conversations.models import Conversation, Message
from maya_sawa_v2.ai_processing.models import ProcessingTask


class MessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['id', 'message_type', 'content', 'metadata', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    class Meta:
        model = Conversation
        fields = ['id', 'session_id', 'conversation_type', 'status', 'title', 'messages', 'created_at', 'updated_at']


class CreateMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ['content']

    def create(self, validated_data):
        conversation = self.context['conversation']
        message = Message.objects.create(
            conversation=conversation,
            message_type='user',
            content=validated_data['content']
        )

        # 觸發 AI 處理任務
        from maya_sawa_v2.ai_processing.tasks import process_ai_response
        from maya_sawa_v2.ai_processing.models import ProcessingTask, AIModel

        # 獲取預設 AI 模型
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
    class Meta:
        model = ProcessingTask
        fields = ['id', 'status', 'result', 'processing_time', 'created_at', 'completed_at']
