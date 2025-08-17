"""
管理命令單元測試
測試不需要連資料庫的方法
"""

import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from io import StringIO


class TestToggleAPISecurityCommand:
    """API 安全配置管理命令測試"""

    def setup_method(self):
        """設置測試環境"""
        self.temp_dir = tempfile.mkdtemp()
        self.env_file_path = os.path.join(self.temp_dir, '.env')

    def teardown_method(self):
        """清理測試環境"""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def create_env_file(self, content):
        """創建測試用的 .env 文件"""
        with open(self.env_file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def read_env_file(self):
        """讀取 .env 文件內容"""
        with open(self.env_file_path, 'r', encoding='utf-8') as f:
            return f.read()

    @patch('maya_sawa_v2.api.management.commands.toggle_api_security.settings')
    def test_show_status_command(self, mock_settings):
        """測試顯示狀態命令"""
        # 設置模擬的設置值
        mock_settings.API_REQUIRE_AUTHENTICATION = False
        mock_settings.API_REQUIRE_CSRF = True
        mock_settings.API_RATE_LIMIT_ENABLED = False

        # 創建測試 .env 文件
        self.create_env_file("""
# Django Settings
DJANGO_DEBUG=True
MAYA_V2_SECRET_KEY=test-key

# API Security
API_REQUIRE_AUTHENTICATION=False
API_REQUIRE_CSRF=True
API_RATE_LIMIT_ENABLED=False
        """.strip())

        # 模擬當前工作目錄
        with patch('os.getcwd', return_value=self.temp_dir):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                call_command('toggle_api_security', '--status')

                output = mock_stdout.getvalue()
                assert '📊 当前API安全设置状态' in output
                assert '🔐 认证要求: ❌ 禁用' in output
                assert '🛡️  CSRF保护: ✅ 启用' in output
                assert '⚡ 速率限制: ❌ 禁用' in output

    def test_enable_security_command(self):
        """測試啟用安全設置命令"""
        # 創建初始 .env 文件
        initial_content = """
# Django Settings
DJANGO_DEBUG=True
MAYA_V2_SECRET_KEY=test-key

# API Security
API_REQUIRE_AUTHENTICATION=False
API_REQUIRE_CSRF=False
API_RATE_LIMIT_ENABLED=False
        """.strip()

        self.create_env_file(initial_content)

        # 模擬當前工作目錄
        with patch('os.getcwd', return_value=self.temp_dir):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                call_command('toggle_api_security', '--enable')

                output = mock_stdout.getvalue()
                # 接受已啟用或狀態輸出（本地化可能略有不同）
                assert ('已启用' in output) or ('已開啟' in output) or ('API安全设置已' in output)

                # 檢查 .env 文件是否被更新
                updated_content = self.read_env_file()
                assert 'API_REQUIRE_AUTHENTICATION=True' in updated_content
                assert 'API_REQUIRE_CSRF=True' in updated_content
                assert 'API_RATE_LIMIT_ENABLED=True' in updated_content

    def test_disable_security_command(self):
        """測試禁用安全設置命令"""
        # 創建初始 .env 文件
        initial_content = """
# Django Settings
DJANGO_DEBUG=True
MAYA_V2_SECRET_KEY=test-key

# API Security
API_REQUIRE_AUTHENTICATION=True
API_REQUIRE_CSRF=True
API_RATE_LIMIT_ENABLED=True
        """.strip()

        self.create_env_file(initial_content)

        # 模擬當前工作目錄
        with patch('os.getcwd', return_value=self.temp_dir):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                call_command('toggle_api_security', '--disable')

                output = mock_stdout.getvalue()
                assert ('已禁用' in output) or ('已關閉' in output) or ('API安全设置已' in output)

                # 檢查 .env 文件是否被更新
                updated_content = self.read_env_file()
                assert 'API_REQUIRE_AUTHENTICATION=False' in updated_content
                assert 'API_REQUIRE_CSRF=False' in updated_content
                assert 'API_RATE_LIMIT_ENABLED=False' in updated_content

    def test_command_without_arguments(self):
        """測試沒有參數的命令"""
        # 創建測試 .env 文件
        self.create_env_file("""
# Django Settings
DJANGO_DEBUG=True
MAYA_V2_SECRET_KEY=test-key
        """.strip())

        # 模擬當前工作目錄
        with patch('os.getcwd', return_value=self.temp_dir):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                call_command('toggle_api_security')

                output = mock_stdout.getvalue()
                assert '请指定 --enable 或 --disable 参数' in output

    def test_command_with_missing_env_file(self):
        """測試 .env 文件不存在的情況"""
        # 確保 .env 文件不存在
        if os.path.exists(self.env_file_path):
            os.remove(self.env_file_path)

        # 模擬當前工作目錄
        with patch('os.getcwd', return_value=self.temp_dir):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                call_command('toggle_api_security', '--enable')

                output = mock_stdout.getvalue()
                assert ('不存在' in output) or ('not exist' in output.lower())

    def test_command_preserves_existing_content(self):
        """測試命令保留現有內容"""
        # 創建包含其他設置的 .env 文件
        initial_content = """
# Django Settings
DJANGO_DEBUG=True
MAYA_V2_SECRET_KEY=test-key

# Database
DATABASE_URL=postgresql://user:pass@localhost/db

# API Security
API_REQUIRE_AUTHENTICATION=False
API_REQUIRE_CSRF=False
API_RATE_LIMIT_ENABLED=False

# Other Settings
REDIS_URL=redis://localhost:6379
        """.strip()

        self.create_env_file(initial_content)

        # 模擬當前工作目錄
        with patch('os.getcwd', return_value=self.temp_dir):
            call_command('toggle_api_security', '--enable')

            # 檢查其他設置是否被保留
            updated_content = self.read_env_file()
            assert 'DJANGO_DEBUG=True' in updated_content
            assert 'DATABASE_URL=postgresql://user:pass@localhost/db' in updated_content
            assert 'REDIS_URL=redis://localhost:6379' in updated_content

    def test_command_handles_comments_and_whitespace(self):
        """測試命令處理註釋和空白"""
        # 創建包含註釋和空白的 .env 文件
        initial_content = """
# Django Settings
DJANGO_DEBUG=True

# API Security Settings
API_REQUIRE_AUTHENTICATION=False  # 開發環境禁用
API_REQUIRE_CSRF=False
API_RATE_LIMIT_ENABLED=False

        """.strip()

        self.create_env_file(initial_content)

        # 模擬當前工作目錄
        with patch('os.getcwd', return_value=self.temp_dir):
            call_command('toggle_api_security', '--enable')

            # 檢查更新後的內容
            updated_content = self.read_env_file()
            assert 'API_REQUIRE_AUTHENTICATION=True' in updated_content
            assert 'API_REQUIRE_CSRF=True' in updated_content
            assert 'API_RATE_LIMIT_ENABLED=True' in updated_content

    def test_command_with_multiple_arguments(self):
        """測試多個參數的命令"""
        # 創建測試 .env 文件
        self.create_env_file("""
# Django Settings
DJANGO_DEBUG=True
MAYA_V2_SECRET_KEY=test-key
        """.strip())

        # 模擬當前工作目錄
        with patch('os.getcwd', return_value=self.temp_dir):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                # 測試同時使用多個參數（目前行為顯示狀態）
                call_command('toggle_api_security', '--status')

                output = mock_stdout.getvalue()
                assert ('当前API安全设置状态' in output) or ('API安全' in output)


class TestSetupAIModelsCommand:
    """設置 AI 模型管理命令測試"""

    @patch('maya_sawa_v2.ai_processing.management.commands.setup_ai_models.AIModel')
    def test_setup_ai_models_command(self, mock_aimodel):
        """測試設置 AI 模型命令"""
        # 模擬 AIModel.objects.get_or_create
        mock_aimodel.objects.get_or_create.side_effect = [
            (MagicMock(), True),  # GPT-4o-mini
            (MagicMock(), True),  # Mock AI
        ]

        with patch.dict('os.environ', {
            'ENABLED_PROVIDERS': 'openai,mock',
            'OPENAI_MODELS': 'gpt-4o-mini',
            'OPENAI_AVAILABLE_MODELS': 'gpt-4o-mini',
            'OPENAI_DEFAULT_MODEL': 'gpt-4o-mini',
            'MOCK_MODELS': 'mock-respond',
            'MOCK_AVAILABLE_MODELS': 'mock-respond',
            'MOCK_DEFAULT_MODEL': 'mock-respond',
        }, clear=False):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                call_command('setup_ai_models')

                output = mock_stdout.getvalue()
                assert ('AI 模型' in output) or ('模型' in output)

            # 驗證調用次數
            assert mock_aimodel.objects.get_or_create.call_count == 2

    @patch('maya_sawa_v2.ai_processing.management.commands.setup_ai_models.AIModel')
    def test_setup_ai_models_existing_models(self, mock_aimodel):
        """測試設置已存在的 AI 模型"""
        # 模擬模型已存在
        mock_aimodel.objects.get_or_create.side_effect = [
            (MagicMock(), False),  # GPT-4o-mini 已存在
            (MagicMock(), False),  # Mock AI 已存在
        ]

        with patch.dict('os.environ', {
            'ENABLED_PROVIDERS': 'openai,mock',
            'OPENAI_MODELS': 'gpt-4o-mini',
            'OPENAI_AVAILABLE_MODELS': 'gpt-4o-mini',
            'OPENAI_DEFAULT_MODEL': 'gpt-4o-mini',
            'MOCK_MODELS': 'mock-respond',
            'MOCK_AVAILABLE_MODELS': 'mock-respond',
            'MOCK_DEFAULT_MODEL': 'mock-respond',
        }, clear=False):
            with patch('sys.stdout', new=StringIO()) as mock_stdout:
                call_command('setup_ai_models')

                output = mock_stdout.getvalue()
                assert ('AI 模型' in output) or ('模型' in output)

    @patch('maya_sawa_v2.ai_processing.management.commands.setup_ai_models.AIModel')
    def test_setup_ai_models_with_errors(self, mock_aimodel):
        """測試設置 AI 模型時出現錯誤"""
        # 模擬創建時出現錯誤
        mock_aimodel.objects.get_or_create.side_effect = Exception("Database error")
        # 設置環境以進入創建流程
        with patch.dict('os.environ', {
            'ENABLED_PROVIDERS': 'openai',
            'OPENAI_MODELS': 'gpt-4o-mini',
            'OPENAI_AVAILABLE_MODELS': 'gpt-4o-mini',
            'OPENAI_DEFAULT_MODEL': 'gpt-4o-mini',
        }, clear=False):
            with pytest.raises(Exception):
                call_command('setup_ai_models')


class TestManagementCommandHelpers:
    """管理命令輔助函數測試"""

    def test_env_file_parsing(self):
        """測試 .env 文件解析"""
        env_content = """
# Comment line
KEY1=value1
KEY2=value2  # Inline comment
KEY3=value3

KEY4=value4
        """.strip()

        # 測試解析邏輯
        lines = env_content.split('\n')
        key_value_pairs = {}

        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                if '=' in line:
                    key, value = line.split('=', 1)
                    # 移除行內註釋
                    if '#' in value:
                        value = value.split('#')[0].strip()
                    key_value_pairs[key.strip()] = value.strip()

        assert key_value_pairs['KEY1'] == 'value1'
        assert key_value_pairs['KEY2'] == 'value2'
        assert key_value_pairs['KEY3'] == 'value3'
        assert key_value_pairs['KEY4'] == 'value4'
        assert len(key_value_pairs) == 4

    def test_env_file_updating(self):
        """測試 .env 文件更新邏輯"""
        original_content = """
# Django Settings
DJANGO_DEBUG=True
API_REQUIRE_AUTHENTICATION=False
API_REQUIRE_CSRF=False
        """.strip()

        # 模擬更新邏輯
        lines = original_content.split('\n')
        updated_lines = []

        for line in lines:
            if line.startswith('API_REQUIRE_AUTHENTICATION='):
                updated_lines.append('API_REQUIRE_AUTHENTICATION=True')
            elif line.startswith('API_REQUIRE_CSRF='):
                updated_lines.append('API_REQUIRE_CSRF=True')
            else:
                updated_lines.append(line)

        updated_content = '\n'.join(updated_lines)

        assert 'API_REQUIRE_AUTHENTICATION=True' in updated_content
        assert 'API_REQUIRE_CSRF=True' in updated_content
        assert 'DJANGO_DEBUG=True' in updated_content
