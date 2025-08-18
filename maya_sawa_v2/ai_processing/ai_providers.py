import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AIProvider(ABC):
    """AI 提供者抽象基類"""

    @abstractmethod
    def generate_response(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
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
            from openai import OpenAI

            if not self.api_key:
                raise ValueError("OpenAI API key not found")

            # 配置 OpenAI 客戶端 - 只傳遞支援的參數
            client_kwargs = {
                'api_key': self.api_key
            }

            # 只有在非預設 URL 時才添加 base_url
            if self.api_base and self.api_base != 'https://api.openai.com/v1':
                client_kwargs['base_url'] = self.api_base

            # 只有在有組織 ID 時才添加
            if self.organization:
                client_kwargs['organization'] = self.organization

            # 調試資訊
            logger.info(f"Creating OpenAI client with kwargs: {client_kwargs}")

            # 確保沒有傳遞不支援的參數，並明確排除 proxy 相關參數
            supported_params = {'api_key', 'base_url', 'organization', 'timeout', 'max_retries'}
            excluded_params = {'proxies', 'http_proxy', 'https_proxy', 'no_proxy'}
            filtered_kwargs = {k: v for k, v in client_kwargs.items()
                             if k in supported_params and k not in excluded_params}

            # 臨時清除環境變數中的 proxy 設定
            original_proxy_vars = {}
            for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY', 'http_proxy', 'https_proxy', 'no_proxy']:
                if var in os.environ:
                    original_proxy_vars[var] = os.environ[var]
                    del os.environ[var]

            try:
                # 使用最簡單的初始化方式，只傳遞必要的參數
                client = OpenAI(api_key=self.api_key)

                # 如果需要設置其他參數，在初始化後單獨設置
                if self.organization:
                    client.organization = self.organization

            except Exception as e:
                logger.error(f"OpenAI client initialization error: {str(e)}")
                # 如果還是有問題，嘗試不傳遞任何參數
                client = OpenAI()
                client.api_key = self.api_key
                if self.organization:
                    client.organization = self.organization
            finally:
                # 恢復原始環境變數
                for var, value in original_proxy_vars.items():
                    os.environ[var] = value

            # 構建對話歷史與知識庫上下文
            messages = []
            if context and 'conversation_history' in context:
                messages.extend(context['conversation_history'])

            system_content = None
            if context:
                parts = []
                if context.get('system_prompt'):
                    parts.append(str(context['system_prompt']))
                if context.get('knowledge_context'):
                    parts.append("以下是與用戶問題相關的知識庫內容，請作為主要依據回答：\n" + str(context['knowledge_context']))
                if parts:
                    system_content = "\n\n".join(parts)

            if system_content:
                messages.insert(0, {"role": "system", "content": system_content})

            messages.append({"role": "user", "content": message})

            response = client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )

            return response.choices[0].message.content

        except ImportError:
            logger.error("OpenAI library not installed")
            return "抱歉，OpenAI 函式庫未安裝，請先安裝 openai 套件。"
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            return f"抱歉，AI 服務暫時無法使用。錯誤：{str(e)}"


_UNSET = object()


class GeminiProvider(AIProvider):
    """Google Gemini API 提供者"""

    def __init__(self, api_key: str | object = _UNSET, model: str = "gemini-1.5-flash"):
        # 未提供參數時，回退到環境變數；明確傳入 None 則不回退（便於測試）
        if api_key is _UNSET:
            self.api_key = os.getenv('GOOGLE_API_KEY')
        else:
            self.api_key = api_key  # could be None
        self.model = model

    def generate_response(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """使用 Gemini API 生成回應"""
        # 明確在無 API key 時回覆固定錯誤字串，確保測試穩定
        if not self.api_key:
            return "Google API key not found"
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)

            # 構建對話歷史
            chat = model.start_chat(history=[])
            if context and 'conversation_history' in context:
                for msg in context['conversation_history']:
                    if msg['role'] == 'user':
                        chat.send_message(msg['content'])
                    elif msg['role'] == 'assistant':
                        # Gemini 會自動處理助手回應
                        pass

            response = chat.send_message(message)
            return response.text

        except ImportError:
            logger.error("Google Generative AI library not installed")
            return "抱歉，Google Generative AI 函式庫未安裝，請先安裝 google-generativeai 套件。"
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return f"抱歉，AI 服務暫時無法使用。錯誤：{str(e)}"


class QwenProvider(AIProvider):
    """Qwen API 提供者"""

    def __init__(self, api_key: str | object = _UNSET, model: str = "qwen-turbo"):
        # 未提供參數時，回退到環境變數；明確傳入 None 則不回退（便於測試）
        if api_key is _UNSET:
            self.api_key = os.getenv('QWEN_API_KEY')
        else:
            self.api_key = api_key  # could be None
        self.model = model

    def generate_response(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """使用 Qwen API 生成回應"""
        # 明確在無 API key 時回覆固定錯誤字串，確保測試穩定
        if not self.api_key:
            return "Qwen API key not found"
        try:
            import dashscope

            dashscope.api_key = self.api_key

            # 構建對話歷史
            messages = []
            if context and 'conversation_history' in context:
                messages.extend(context['conversation_history'])

            messages.append({"role": "user", "content": message})

            response = dashscope.MultiModalConversation.call(
                model=self.model,
                messages=messages,
                max_tokens=1000,
                temperature=0.7
            )

            if response.status_code == 200:
                return response.output.choices[0].message.content
            else:
                raise Exception(f"Qwen API error: {response.message}")

        except ImportError:
            logger.error("DashScope library not installed")
            return "抱歉，DashScope 函式庫未安裝，請先安裝 dashscope 套件。"
        except Exception as e:
            logger.error(f"Qwen API error: {str(e)}")
            return f"抱歉，AI 服務暫時無法使用。錯誤：{str(e)}"


class MockProvider(AIProvider):
    """模擬 AI 提供者 - 用於測試"""

    def generate_response(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """生成模擬回應"""
        return f"這是一個模擬回應。你問的是：{message}"


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
    elif provider_name.lower() == 'gemini':
        return GeminiProvider(
            api_key=config.get('api_key'),
            model=config.get('model', 'gemini-1.5-flash')
        )
    elif provider_name.lower() == 'qwen':
        return QwenProvider(
            api_key=config.get('api_key'),
            model=config.get('model', 'qwen-turbo')
        )
    elif provider_name.lower() == 'mock':
        return MockProvider()
    else:
        raise ValueError(f"Unsupported AI provider: {provider_name}")
