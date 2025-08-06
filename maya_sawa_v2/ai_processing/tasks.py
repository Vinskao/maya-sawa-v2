import time
import logging
from celery import shared_task
from django.utils import timezone
from .models import ProcessingTask
from maya_sawa_v2.conversations.models import Message, Conversation
from .ai_providers import get_ai_provider
from .chain.service import conversation_type_service

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def process_ai_response(self, task_id):
    """處理 AI 回應的非同步任務"""
    try:
        processing_task = ProcessingTask.objects.get(id=task_id)
        processing_task.status = 'processing'
        processing_task.save()

        start_time = time.time()

        # 獲取對話歷史作為上下文
        conversation = processing_task.conversation
        messages = conversation.messages.filter(message_type__in=['user', 'ai']).order_by('created_at')

        # 使用 chain 分類服務確定對話類型
        user_message = processing_task.message.content
        classification_result = conversation_type_service.classify_conversation_type(
            message=user_message,
            user_id=conversation.user.id,
            conversation_id=str(conversation.id),
            current_type=conversation.conversation_type
        )
        
        # 如果分類結果建議更新對話類型，則更新
        if classification_result['should_update']:
            conversation.conversation_type = classification_result['conversation_type']
            conversation.save()
            logger.info(f"Updated conversation type to: {classification_result['conversation_type']} "
                       f"(confidence: {classification_result['confidence']}, reason: {classification_result['reason']})")

        # 構建對話歷史（僅保留最近的 10 條訊息）
        conversation_history = []
        for msg in messages[-10:]:
            role = "user" if msg.message_type == "user" else "assistant"
            conversation_history.append({"role": role, "content": msg.content})

        # 構建上下文
        context = {
            'conversation_history': conversation_history,
            'conversation_type': conversation.conversation_type,
            'system_prompt': get_system_prompt(conversation.conversation_type),
            'classification_metadata': classification_result['metadata']
        }

        # 使用配置的 AI 提供者
        provider = get_ai_provider(
            processing_task.ai_model.provider,
            processing_task.ai_model.config
        )

        # 調用 AI API
        response = provider.generate_response(
            processing_task.message.content,
            context
        )

        processing_time = time.time() - start_time

        # 創建 AI 回應訊息
        ai_message = Message.objects.create(
            conversation=processing_task.conversation,
            message_type='ai',
            content=response,
            metadata={
                'ai_model': processing_task.ai_model.name,
                'provider': processing_task.ai_model.provider,
                'processing_time': processing_time,
                'task_id': str(self.request.id),
                'classification_result': classification_result
            }
        )

        # 更新任務狀態
        processing_task.status = 'completed'
        processing_task.result = response
        processing_task.processing_time = processing_time
        processing_task.completed_at = timezone.now()
        processing_task.save()

        logger.info(f"AI processing completed for task {task_id}")

    except Exception as e:
        logger.error(f"AI processing failed for task {task_id}: {str(e)}")
        processing_task.status = 'failed'
        processing_task.error_message = str(e)
        processing_task.save()


def process_ai_response_sync(user_message, ai_model):
    """同步处理AI回应"""
    try:
        start_time = time.time()

        # 获取对话历史作为上下文
        conversation = user_message.conversation
        messages = conversation.messages.filter(message_type__in=['user', 'ai']).order_by('created_at')

        # 使用 chain 分类服务确定对话类型
        classification_result = conversation_type_service.classify_conversation_type(
            message=user_message.content,
            user_id=conversation.user.id,
            conversation_id=str(conversation.id),
            current_type=conversation.conversation_type
        )
        
        # 如果分类结果建议更新对话类型，则更新
        if classification_result['should_update']:
            conversation.conversation_type = classification_result['conversation_type']
            conversation.save()
            logger.info(f"Updated conversation type to: {classification_result['conversation_type']} "
                       f"(confidence: {classification_result['confidence']}, reason: {classification_result['reason']})")

        # 构建对话历史（仅保留最近的 10 条訊息）
        conversation_history = []
        recent_messages = list(messages)[-10:]  # 转换为列表再切片
        for msg in recent_messages:
            role = "user" if msg.message_type == "user" else "assistant"
            conversation_history.append({"role": role, "content": msg.content})

        # 构建上下文
        context = {
            'conversation_history': conversation_history,
            'conversation_type': conversation.conversation_type,
            'system_prompt': get_system_prompt(conversation.conversation_type),
            'classification_metadata': classification_result['metadata']
        }

        # 使用配置的 AI 提供者
        provider = get_ai_provider(
            ai_model.provider,
            ai_model.config
        )

        # 调用 AI API
        response = provider.generate_response(
            user_message.content,
            context
        )

        processing_time = time.time() - start_time

        # 创建 AI 回应訊息
        ai_message = Message.objects.create(
            conversation=conversation,
            message_type='ai',
            content=response,
            metadata={
                'ai_model': ai_model.name,
                'provider': ai_model.provider,
                'processing_time': processing_time,
                'classification_result': classification_result
            }
        )

        logger.info(f"AI processing completed synchronously for message {user_message.id}")

        return response

    except Exception as e:
        logger.error(f"AI processing failed for message {user_message.id}: {str(e)}")
        raise e


def get_system_prompt(conversation_type):
    """根據對話類型獲取系統提示"""
    prompts = {
        'customer_service': "你是一個專業的客戶服務代表，請用友善、專業的態度回答客戶問題。",
        'knowledge_query': "你是一個知識庫助手，請根據您的知識為用戶提供準確、有用的資訊。",
        'general': "你是一個有用的 AI 助手，請用中文回答用戶的問題。"
    }
    return prompts.get(conversation_type, "你是一個有用的 AI 助手，請用中文回答用戶的問題。")
