from __future__ import annotations

from typing import Optional

from maya_sawa_v2.conversations.models import Conversation, Message
from maya_sawa_v2.ai_processing.models import AIModel, ProcessingTask
from maya_sawa_v2.ai_processing.services.ai_response_service import AIResponseService


class MessageAppService:
    """Application service for creating user messages and enqueuing AI tasks."""

    def __init__(self, ai_response_service: Optional[AIResponseService] = None) -> None:
        self.ai_response_service = ai_response_service or AIResponseService()

    def create_user_message_and_enqueue(
        self,
        conversation: Conversation,
        content: str,
        ai_model_id: Optional[int] = None,
    ) -> Message:
        user_message = Message.objects.create(
            conversation=conversation,
            message_type="user",
            content=content,
        )

        ai_model = self.ai_response_service.select_ai_model(ai_model_id)
        if ai_model:
            task = self.ai_response_service.enqueue_task(conversation, user_message, ai_model)
            # Lazy import to avoid Celery coupling here
            from maya_sawa_v2.ai_processing.tasks import process_ai_response

            process_ai_response.delay(task.id)

        return user_message


