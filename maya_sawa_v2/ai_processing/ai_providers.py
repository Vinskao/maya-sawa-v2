import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """AI 提供者抽象基類"""

    @abstractmethod
    def generate_response(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """生成 AI 回應"""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI API 提供者"""

    def __init__(self, api_key: str = None, model: str = "gpt-4o-mini", organization: str = None, api_base: str = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.model = model
        self.organization = organization or os.getenv('OPENAI_ORGANIZATION')
        self.api_base = api_base or os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1')

    def generate_response(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """使用 OpenAI API 生成回應"""
        try:
            import openai

            if not self.api_key:
                raise ValueError("OpenAI API key not found")

            # 配置 OpenAI 客戶端
            openai.api_key = self.api_key
            if self.organization:
                openai.organization = self.organization
            if self.api_base:
                openai.api_base = self.api_base

            # 構建對話歷史
            messages = []
            if context and 'conversation_history' in context:
                messages.extend(context['conversation_history'])

            messages.append({"role": "user", "content": message})

            response = openai.ChatCompletion.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return f"抱歉，AI 服務暫時無法使用。錯誤：{str(e)}"


class AnthropicProvider(AIProvider):
    """Anthropic Claude API 提供者"""

    def __init__(self, api_key: str = None, model: str = "claude-3-sonnet-20240229"):
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        self.model = model

    def generate_response(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """使用 Anthropic API 生成回應"""
        try:
            import anthropic

            if not self.api_key:
                raise ValueError("Anthropic API key not found")

            client = anthropic.Anthropic(api_key=self.api_key)

            # 構建系統提示
            system_prompt = "你是一個有用的 AI 助手，請用中文回答用戶的問題。"
            if context and 'system_prompt' in context:
                system_prompt = context['system_prompt']

            response = client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": message}]
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            return f"抱歉，AI 服務暫時無法使用。錯誤：{str(e)}"


class MockProvider(AIProvider):
    """模擬 AI 提供者（用於測試）"""

    def generate_response(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """模擬 AI 回應"""
        import random
        import time

        # 模擬處理時間
        time.sleep(random.uniform(1, 3))

        responses = [
            "感謝您的詢問，我理解您的問題。根據我的分析，建議您...",
            "這是一個很好的問題。讓我為您詳細說明...",
            "根據您提供的資訊，我建議您可以考慮以下方案...",
            "我理解您的需求，以下是相關的解決方案...",
            f"您提到的是關於「{message[:20]}...」的問題，讓我為您分析一下...",
        ]

        return random.choice(responses)


def get_ai_provider(provider_name: str, config: Dict[str, Any] = None) -> AIProvider:
    """根據提供者名稱獲取 AI 提供者實例"""
    config = config or {}

    if provider_name.lower() == 'openai':
        return OpenAIProvider(
            api_key=config.get('api_key'),
            model=config.get('model', 'gpt-4o-mini'),
            organization=config.get('organization'),
            api_base=config.get('api_base')
        )
    elif provider_name.lower() == 'anthropic':
        return AnthropicProvider(
            api_key=config.get('api_key'),
            model=config.get('model', 'claude-3-sonnet-20240229')
        )
    elif provider_name.lower() == 'mock':
        return MockProvider()
    else:
        raise ValueError(f"Unsupported AI provider: {provider_name}")
