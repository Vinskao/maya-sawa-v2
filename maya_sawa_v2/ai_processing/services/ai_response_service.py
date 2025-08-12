from __future__ import annotations

import time
import logging
from typing import Dict, Any, Optional, List

from django.utils import timezone

from maya_sawa_v2.conversations.models import Conversation, Message
from maya_sawa_v2.ai_processing.models import ProcessingTask, AIModel
from maya_sawa_v2.ai_processing.ai_providers import get_ai_provider


logger = logging.getLogger(__name__)


class AIResponseService:
    """Coordinates AI response generation independent from Celery/serializers."""

    def build_conversation_history(self, conversation: Conversation, limit: int = 10) -> List[Dict[str, str]]:
        history: List[Dict[str, str]] = []
        messages = conversation.messages.filter(message_type__in=["user", "ai"]).order_by("created_at")
        for msg in list(messages)[-limit:]:
            role = "user" if msg.message_type == "user" else "assistant"
            history.append({"role": role, "content": msg.content})
        return history

    def build_context(
        self,
        conversation: Conversation,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        context: Dict[str, Any] = {
            "conversation_history": self.build_conversation_history(conversation),
            "conversation_type": conversation.conversation_type,
        }
        if extra:
            context.update(extra)
        return context

    def select_ai_model(self, ai_model_id: Optional[int]) -> Optional[AIModel]:
        if ai_model_id:
            try:
                return AIModel.objects.get(id=ai_model_id, is_active=True)
            except AIModel.DoesNotExist:
                return None
        return AIModel.objects.filter(is_active=True).first()

    def enqueue_task(self, conversation: Conversation, user_message: Message, ai_model: AIModel) -> ProcessingTask:
        task = ProcessingTask.objects.create(conversation=conversation, message=user_message, ai_model=ai_model)
        return task

    def process_task(self, task: ProcessingTask, extra_context: Optional[Dict[str, Any]] = None) -> str:
        start_time = time.time()
        conversation = task.conversation
        context = self.build_context(conversation, extra_context)

        provider = get_ai_provider(task.ai_model.provider, task.ai_model.config)
        response = provider.generate_response(task.message.content, context)

        processing_time = time.time() - start_time

        Message.objects.create(
            conversation=conversation,
            message_type="ai",
            content=response,
            metadata={
                "ai_model": task.ai_model.name,
                "provider": task.ai_model.provider,
                "processing_time": processing_time,
                "task_id": str(task.id),
            },
        )

        task.status = "completed"
        task.result = response
        task.processing_time = processing_time
        task.completed_at = timezone.now()
        task.save(update_fields=["status", "result", "processing_time", "completed_at"])

        return response


