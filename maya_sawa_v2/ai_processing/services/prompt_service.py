from __future__ import annotations

class PromptService:
    """Provides system prompts based on conversation type."""

    DEFAULT_PROMPT = "你是一個有用的 AI 助手，請用中文回答用戶的問題。"

    PROMPTS_BY_TYPE = {
        'customer_service': "你是一個專業的客戶服務代表，請用友善、專業的態度回答客戶問題。",
        'knowledge_query': "你是一個知識庫助手，請根據您的知識為用戶提供準確、有用的資訊。",
        'general': DEFAULT_PROMPT,
    }

    def get_system_prompt(self, conversation_type: str) -> str:
        return self.PROMPTS_BY_TYPE.get(conversation_type, self.DEFAULT_PROMPT)


