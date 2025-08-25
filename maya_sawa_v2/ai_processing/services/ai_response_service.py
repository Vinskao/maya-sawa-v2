from __future__ import annotations

import time
import logging
from typing import Dict, Any, Optional, List

from django.utils import timezone

from maya_sawa_v2.conversations.models import Conversation, Message
from maya_sawa_v2.ai_processing.models import ProcessingTask, AIModel
from maya_sawa_v2.ai_processing.ai_providers import get_ai_provider
from maya_sawa_v2.ai_processing.services.conversation_service import ConversationService
from maya_sawa_v2.ai_processing.services.prompt_service import PromptService


logger = logging.getLogger(__name__)


class AIResponseService:
    """Coordinates AI response generation independent from Celery/serializers."""

    def __init__(self, conversation_service: ConversationService | None = None, prompt_service: PromptService | None = None) -> None:
        self.conversation_service = conversation_service or ConversationService()
        self.prompt_service = prompt_service or PromptService()

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

        # Classify conversation type and update if needed
        classification_result = self.conversation_service.classify_and_update(
            conversation=conversation,
            message_text=task.message.content,
        )

        # Build context with system prompt and classification metadata
        context_extra: Dict[str, Any] = {
            "system_prompt": self.prompt_service.get_system_prompt(conversation.conversation_type),
            "classification_metadata": classification_result.get("metadata", {}),
        }
        if extra_context:
            context_extra.update(extra_context)

        context = self.build_context(conversation, context_extra)

        provider = get_ai_provider(task.ai_model.provider, task.ai_model.config)
        response = provider.generate_response(task.message.content, context)

        # 如果有知識庫上下文，將其添加到回應中
        if extra_context and extra_context.get('knowledge_context'):
            response = f"{response}\n\n{extra_context['knowledge_context']}"

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

    def process_sync(self, user_message: Message, ai_model: AIModel, knowledge_context: Optional[str] = None) -> str:
        start_time = time.time()
        conversation = user_message.conversation

        classification_result = self.conversation_service.classify_and_update(
            conversation=conversation,
            message_text=user_message.content,
        )

        context_extra: Dict[str, Any] = {
            "system_prompt": self.prompt_service.get_system_prompt(conversation.conversation_type),
            "classification_metadata": classification_result.get("metadata", {}),
        }
        if knowledge_context:
            context_extra["knowledge_context"] = knowledge_context

        context = self.build_context(conversation, context_extra)

        provider = get_ai_provider(ai_model.provider, ai_model.config)
        response = provider.generate_response(user_message.content, context)

        processing_time = time.time() - start_time

        Message.objects.create(
            conversation=conversation,
            message_type="ai",
            content=response,
            metadata={
                "ai_model": ai_model.name,
                "provider": ai_model.provider,
                "processing_time": processing_time,
                "classification_result": classification_result,
            },
        )

        return response


