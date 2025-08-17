"""
pytest 配置文件
設置測試環境和共享 fixtures
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from django.conf import settings


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """設置測試數據庫"""
    with django_db_blocker.unblock():
        # 這裡可以添加測試數據庫的初始化邏輯
        pass


@pytest.fixture
def mock_settings():
    """模擬 Django 設置"""
    with patch('django.conf.settings') as mock_settings:
        # 設置默認的測試配置
        mock_settings.API_REQUIRE_AUTHENTICATION = False
        mock_settings.API_REQUIRE_CSRF = False
        mock_settings.API_RATE_LIMIT_ENABLED = False
        mock_settings.DEBUG = True
        yield mock_settings


@pytest.fixture
def temp_env_file():
    """創建臨時 .env 文件"""
    temp_dir = tempfile.mkdtemp()
    env_file_path = os.path.join(temp_dir, '.env')

    # 創建測試用的 .env 文件
    env_content = """
# Django Settings
DJANGO_DEBUG=True
MAYA_V2_SECRET_KEY=test-secret-key

# Database
DATABASE_URL=sqlite:///test.db

# Redis & Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# AI APIs
OPENAI_API_KEY=test-openai-key
OPENAI_ORGANIZATION=test-org
OPENAI_API_BASE=https://api.openai.com/v1

# API Security
API_REQUIRE_AUTHENTICATION=False
API_REQUIRE_CSRF=False
API_RATE_LIMIT_ENABLED=False
    """.strip()

    with open(env_file_path, 'w') as f:
        f.write(env_content)

    yield env_file_path

    # 清理
    import shutil
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_openai_client():
    """模擬 OpenAI 客戶端"""
    with patch('maya_sawa_v2.ai_processing.ai_providers.OpenAI') as mock_openai:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "模擬 AI 回應"
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_gemini_client():
    """模擬 Gemini 客戶端"""
    with patch('maya_sawa_v2.ai_processing.ai_providers.genai') as mock_genai:
        mock_genai.configure = MagicMock()
        mock_model = MagicMock()
        mock_chat = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "模擬 Gemini 回應"

        mock_model.start_chat.return_value = mock_chat
        mock_chat.send_message.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model
        yield mock_genai


@pytest.fixture
def mock_qwen_client():
    """模擬 Qwen 客戶端"""
    with patch('maya_sawa_v2.ai_processing.ai_providers.dashscope') as mock_dashscope:
        mock_dashscope.api_key = None
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.output.choices = [MagicMock()]
        mock_response.output.choices[0].message.content = "模擬 Qwen 回應"

        mock_dashscope.MultiModalConversation.call.return_value = mock_response
        yield mock_dashscope


@pytest.fixture
def mock_celery_task():
    """模擬 Celery 任務"""
    with patch('maya_sawa_v2.ai_processing.tasks.process_ai_response.delay') as mock_task:
        mock_task.return_value = MagicMock()
        yield mock_task


@pytest.fixture
def sample_conversation_data():
    """樣本對話數據"""
    return {
        'session_id': 'test-session-123',
        'type': 'chat',
        'status': 'active',
        'title': '測試對話'
    }


@pytest.fixture
def sample_message_data():
    """樣本消息數據"""
    return {
        'type': 'user',
        'content': '你好，這是一個測試消息',
        'metadata': {
            'source': 'test',
            'timestamp': '2024-01-01T00:00:00Z'
        }
    }


@pytest.fixture
def sample_ai_model_data():
    """樣本 AI 模型數據"""
    return {
        'name': 'GPT-4o-mini',
        'provider': 'openai',
        'model_id': 'gpt-4o-mini',
        'is_active': True,
        'config': {
            'api_key': 'test-key',
            'organization': 'test-org',
            'api_base': 'https://api.openai.com/v1'
        }
    }


@pytest.fixture
def mock_user():
    """模擬用戶"""
    user = MagicMock()
    user.id = 1
    user.username = 'testuser'
    user.email = 'test@example.com'
    user.is_authenticated = True
    user.is_active = True
    return user


@pytest.fixture
def mock_anonymous_user():
    """模擬匿名用戶"""
    from django.contrib.auth.models import AnonymousUser
    return AnonymousUser()


@pytest.fixture
def mock_request():
    """模擬請求對象"""
    from django.test import RequestFactory

    factory = RequestFactory()
    request = factory.get('/')
    request.user = MagicMock()
    request.user.is_authenticated = True
    return request


@pytest.fixture
def mock_view():
    """模擬視圖對象"""
    view = MagicMock()
    view.action = 'list'
    view.request = MagicMock()
    view.request.user = MagicMock()
    view.request.user.is_authenticated = True
    return view


@pytest.fixture
def api_client():
    """API 測試客戶端"""
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_api_client(mock_user):
    """已認證的 API 測試客戶端"""
    from rest_framework.test import APIClient

    client = APIClient()
    client.force_authenticate(user=mock_user)
    return client


@pytest.fixture
def mock_logger():
    """模擬日誌記錄器"""
    with patch('logging.getLogger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        yield mock_logger


@pytest.fixture
def mock_redis():
    """模擬 Redis 連接"""
    with patch('redis.Redis') as mock_redis_class:
        mock_redis_instance = MagicMock()
        mock_redis_class.return_value = mock_redis_instance
        yield mock_redis_instance


@pytest.fixture
def mock_celery_app():
    """模擬 Celery 應用"""
    with patch('celery.Celery') as mock_celery_class:
        mock_celery_instance = MagicMock()
        mock_celery_class.return_value = mock_celery_instance
        yield mock_celery_instance


@pytest.fixture
def test_settings():
    """測試設置"""
    return {
        'API_REQUIRE_AUTHENTICATION': False,
        'API_REQUIRE_CSRF': False,
        'API_RATE_LIMIT_ENABLED': False,
        'DEBUG': True,
        'SECRET_KEY': 'test-secret-key',
        'DATABASES': {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': ':memory:',
            }
        },
        'REDIS_URL': 'redis://localhost:6379/0',
        'CELERY_BROKER_URL': 'redis://localhost:6379/0',
        'CELERY_RESULT_BACKEND': 'redis://localhost:6379/0',
    }


# 注意：不要在此自動啟用 DB，避免不需要資料庫的單元測試被迫初始化資料庫


@pytest.fixture
def mock_environment_variables():
    """模擬環境變數"""
    env_vars = {
        'OPENAI_API_KEY': 'test-openai-key',
        'OPENAI_ORGANIZATION': 'test-org',
        'OPENAI_API_BASE': 'https://api.openai.com/v1',
        'GOOGLE_API_KEY': 'test-google-key',
        'QWEN_API_KEY': 'test-qwen-key',
        'DATABASE_URL': 'sqlite:///test.db',
        'REDIS_URL': 'redis://localhost:6379/0',
        'CELERY_BROKER_URL': 'redis://localhost:6379/0',
        'CELERY_RESULT_BACKEND': 'redis://localhost:6379/0',
    }

    with patch.dict('os.environ', env_vars):
        yield env_vars


@pytest.fixture
def mock_file_operations():
    """模擬文件操作"""
    with patch('builtins.open', mock_open()) as mock_file:
        with patch('os.path.exists', return_value=True):
            with patch('os.makedirs'):
                yield mock_file


@pytest.fixture
def sample_api_response():
    """樣本 API 回應"""
    return {
        'id': 1,
        'message': '操作成功',
        'data': {
            'conversation_id': 123,
            'message_id': 456,
            'status': 'success'
        },
        'timestamp': '2024-01-01T00:00:00Z'
    }


@pytest.fixture
def sample_error_response():
    """樣本錯誤回應"""
    return {
        'error': '操作失敗',
        'message': '詳細錯誤信息',
        'code': 'ERROR_CODE',
        'timestamp': '2024-01-01T00:00:00Z'
    }
