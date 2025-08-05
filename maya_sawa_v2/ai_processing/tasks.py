import time
import logging
from celery import shared_task
from django.utils import timezone
from .models import ProcessingTask
from maya_sawa_v2.conversations.models import Message
from .ai_providers import get_ai_provider

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

        # 構建對話歷史（僅保留最近的 10 條訊息）
        conversation_history = []
        for msg in messages[-10:]:
            role = "user" if msg.message_type == "user" else "assistant"
            conversation_history.append({"role": role, "content": msg.content})

        # 構建上下文
        context = {
            'conversation_history': conversation_history,
            'conversation_type': conversation.conversation_type,
            'system_prompt': get_system_prompt(conversation.conversation_type)
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
                'task_id': str(self.request.id)
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


def get_system_prompt(conversation_type):
    """根據對話類型獲取系統提示"""
    prompts = {
        'customer_service': "你是一個專業的客戶服務代表，請用友善、專業的態度回答客戶問題。",
        'knowledge_query': "你是一個知識庫助手，請根據您的知識為用戶提供準確、有用的資訊。",
        'general': "你是一個有用的 AI 助手，請用中文回答用戶的問題。"
    }
    return prompts.get(conversation_type, "你是一個有用的 AI 助手，請用中文回答用戶的問題。")
