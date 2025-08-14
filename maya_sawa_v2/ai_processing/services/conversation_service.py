from __future__ import annotations

from typing import Dict, Any

from maya_sawa_v2.conversations.models import Conversation
from maya_sawa_v2.ai_processing.chain.service import conversation_type_service


class ConversationService:
    """Encapsulates conversation classification and updates."""

    def classify_and_update(self, conversation: Conversation, message_text: str) -> Dict[str, Any]:
        result = conversation_type_service.classify_conversation_type(
            message=message_text,
            user_id=conversation.user.id,
            conversation_id=str(conversation.id),
            current_type=conversation.conversation_type,
        )

        if result.get('should_update'):
            conversation.conversation_type = result['conversation_type']
            conversation.save(update_fields=['conversation_type'])

        return result




