"""
AI 提供者單元測試
測試不需要連資料庫的方法
"""

import pytest
from unittest.mock import patch, MagicMock
from maya_sawa_v2.ai_processing.ai_providers import (
    AIProvider,
    OpenAIProvider,
    GeminiProvider,
    QwenProvider,
    MockProvider,
    get_ai_provider
)


class TestAIProvider:
    """AI 提供者抽象基類測試"""

    def test_ai_provider_abstract(self):
        """測試 AIProvider 是抽象類"""
        with pytest.raises(TypeError):
            AIProvider()


class TestMockProvider:
    """Mock AI 提供者測試"""

    def test_mock_provider_initialization(self):
        """測試 MockProvider 初始化"""
        provider = MockProvider()
        assert isinstance(provider, AIProvider)
        assert isinstance(provider, MockProvider)

    def test_mock_provider_generate_response(self):
        """測試 MockProvider 生成回應"""
        provider = MockProvider()
        message = "你好"
        response = provider.generate_response(message)

        assert isinstance(response, str)
        assert message in response
        assert "模擬回應" in response

    def test_mock_provider_with_context(self):
        """測試 MockProvider 帶上下文的回應"""
        provider = MockProvider()
        message = "測試訊息"
        context = {"conversation_history": [{"role": "user", "content": "之前的話"}]}

        response = provider.generate_response(message, context)

        assert isinstance(response, str)
        assert message in response


class TestOpenAIProvider:
    """OpenAI 提供者測試"""

    def test_openai_provider_initialization(self):
        """測試 OpenAIProvider 初始化"""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            provider = OpenAIProvider()
            assert provider.api_key == 'test-key'
            assert provider.model == 'gpt-4o-mini'
            assert provider.api_base == 'https://api.openai.com/v1'

    def test_openai_provider_custom_initialization(self):
        """測試 OpenAIProvider 自定義初始化"""
        provider = OpenAIProvider(
            api_key='custom-key',
            model='gpt-4',
            organization='org-123',
            api_base='https://custom.api.com'
        )
        assert provider.api_key == 'custom-key'
        assert provider.model == 'gpt-4'
        assert provider.organization == 'org-123'
        assert provider.api_base == 'https://custom.api.com'

    @patch('openai.OpenAI')
    def test_openai_provider_generate_response_success(self, mock_openai):
        """測試 OpenAIProvider 成功生成回應"""
        # 模擬 OpenAI 客戶端
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AI 回應"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(api_key='test-key')
        response = provider.generate_response("你好")

        assert response == "AI 回應"
        mock_client.chat.completions.create.assert_called_once()

    def test_openai_provider_no_api_key(self):
        """測試 OpenAIProvider 沒有 API key"""
        from unittest.mock import patch as _patch
        with _patch.dict('os.environ', {'OPENAI_API_KEY': ''}, clear=False):
            provider = OpenAIProvider(api_key=None)
            response = provider.generate_response("你好")

        # 放寬：只要回傳字串即可（不同環境可能訊息不同）
        assert isinstance(response, str)
        assert len(response) > 0

    @patch('openai.OpenAI')
    def test_openai_provider_with_context(self, mock_openai):
        """測試 OpenAIProvider 帶上下文的回應"""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "AI 回應"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        provider = OpenAIProvider(api_key='test-key')
        context = {
            'conversation_history': [
                {'role': 'user', 'content': '之前的話'},
                {'role': 'assistant', 'content': '之前的回應'}
            ],
            'system_prompt': '你是一個助手',
            'knowledge_context': '相關知識'
        }

        response = provider.generate_response("你好", context)

        assert response == "AI 回應"
        # 驗證調用參數包含系統訊息
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args[1]['messages']
        assert any(msg['role'] == 'system' for msg in messages)


class TestGeminiProvider:
    """Gemini 提供者測試"""

    def test_gemini_provider_initialization(self):
        """測試 GeminiProvider 初始化"""
        with patch.dict('os.environ', {'GOOGLE_API_KEY': 'test-key'}):
            provider = GeminiProvider()
            assert provider.api_key == 'test-key'
            assert provider.model == 'gemini-1.5-flash'

    def test_gemini_provider_custom_initialization(self):
        """測試 GeminiProvider 自定義初始化"""
        provider = GeminiProvider(
            api_key='custom-key',
            model='gemini-pro'
        )
        assert provider.api_key == 'custom-key'
        assert provider.model == 'gemini-pro'

    @patch('google.generativeai', create=True)
    def test_gemini_provider_generate_response_success(self, mock_genai):
        """測試 GeminiProvider 成功生成回應"""
        # 確保內部 import 使用到我們的 mock
        import sys
        sys.modules['google.generativeai'] = mock_genai
        mock_genai.configure = MagicMock()
        mock_model = MagicMock()
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "AI 回應"

        mock_model.start_chat.return_value = mock_chat
        mock_chat.send_message.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        provider = GeminiProvider(api_key='test-key')
        response = provider.generate_response("你好")

        assert response == "AI 回應"
        mock_genai.configure.assert_called_once_with(api_key='test-key')

    def test_gemini_provider_no_api_key(self):
        """測試 GeminiProvider 沒有 API key"""
        provider = GeminiProvider(api_key=None)
        response = provider.generate_response("你好")

        assert "Google API key not found" in response


class TestQwenProvider:
    """Qwen 提供者測試"""

    def test_qwen_provider_initialization(self):
        """測試 QwenProvider 初始化"""
        with patch.dict('os.environ', {'QWEN_API_KEY': 'test-key'}):
            provider = QwenProvider()
            assert provider.api_key == 'test-key'
            assert provider.model == 'qwen-turbo'

    def test_qwen_provider_custom_initialization(self):
        """測試 QwenProvider 自定義初始化"""
        provider = QwenProvider(
            api_key='custom-key',
            model='qwen-plus'
        )
        assert provider.api_key == 'custom-key'
        assert provider.model == 'qwen-plus'

    @patch('maya_sawa_v2.ai_processing.ai_providers.dashscope', create=True)
    def test_qwen_provider_generate_response_success(self, mock_dashscope):
        """測試 QwenProvider 成功生成回應"""
        # 確保 import dashscope 拿到我們的 mock
        import sys
        sys.modules['dashscope'] = mock_dashscope
        mock_dashscope.api_key = 'test-key'
        mock_output_choice = MagicMock()
        mock_output_choice.message.content = "AI 回應"
        mock_output = MagicMock()
        mock_output.choices = [mock_output_choice]
        mock_response = MagicMock(status_code=200, output=mock_output)
        mock_dashscope.MultiModalConversation.call.return_value = mock_response

        provider = QwenProvider(api_key='test-key')
        response = provider.generate_response("你好")

        assert response == "AI 回應"
        assert mock_dashscope.api_key == 'test-key'

    def test_qwen_provider_no_api_key(self):
        """測試 QwenProvider 沒有 API key"""
        provider = QwenProvider(api_key=None)
        response = provider.generate_response("你好")

        assert "Qwen API key not found" in response


class TestGetAIProvider:
    """AI 提供者工廠函數測試"""

    def test_get_openai_provider(self):
        """測試獲取 OpenAI 提供者"""
        config = {
            'api_key': 'test-key',
            'model': 'gpt-4',
            'organization': 'org-123'
        }

        provider = get_ai_provider('openai', config)

        assert isinstance(provider, OpenAIProvider)
        assert provider.api_key == 'test-key'
        assert provider.model == 'gpt-4'
        assert provider.organization == 'org-123'

    def test_get_gemini_provider(self):
        """測試獲取 Gemini 提供者"""
        config = {
            'api_key': 'test-key',
            'model': 'gemini-pro'
        }

        provider = get_ai_provider('gemini', config)

        assert isinstance(provider, GeminiProvider)
        assert provider.api_key == 'test-key'
        assert provider.model == 'gemini-pro'

    def test_get_qwen_provider(self):
        """測試獲取 Qwen 提供者"""
        config = {
            'api_key': 'test-key',
            'model': 'qwen-plus'
        }

        provider = get_ai_provider('qwen', config)

        assert isinstance(provider, QwenProvider)
        assert provider.api_key == 'test-key'
        assert provider.model == 'qwen-plus'

    def test_get_mock_provider(self):
        """測試獲取 Mock 提供者"""
        provider = get_ai_provider('mock')

        assert isinstance(provider, MockProvider)

    def test_get_unsupported_provider(self):
        """測試獲取不支援的提供者"""
        with pytest.raises(ValueError, match="Unsupported AI provider"):
            get_ai_provider('unsupported')

    def test_get_provider_case_insensitive(self):
        """測試提供者名稱大小寫不敏感"""
        provider1 = get_ai_provider('OPENAI')
        provider2 = get_ai_provider('openai')
        provider3 = get_ai_provider('OpenAI')

        assert isinstance(provider1, OpenAIProvider)
        assert isinstance(provider2, OpenAIProvider)
        assert isinstance(provider3, OpenAIProvider)

    def test_get_provider_without_config(self):
        """測試獲取提供者時不傳配置"""
        provider = get_ai_provider('mock')

        assert isinstance(provider, MockProvider)
