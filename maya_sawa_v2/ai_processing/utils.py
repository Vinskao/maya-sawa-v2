import os
from typing import Dict, List, Optional
from django.conf import settings


class AIProviderConfig:
    """AI 提供者配置管理"""

    @staticmethod
    def get_enabled_providers() -> List[str]:
        """獲取啟用的提供者列表"""
        providers = os.getenv('ENABLED_PROVIDERS', 'openai,mock')
        return [p.strip() for p in providers.split(',') if p.strip()]

    @staticmethod
    def get_provider_models(provider: str) -> List[str]:
        """獲取指定提供者的所有模型"""
        models_key = f'{provider.upper()}_MODELS'
        models = os.getenv(models_key, '')
        return [m.strip() for m in models.split(',') if m.strip()]

    @staticmethod
    def get_available_models(provider: str) -> List[str]:
        """獲取指定提供者的可用模型"""
        available_key = f'{provider.upper()}_AVAILABLE_MODELS'
        models = os.getenv(available_key, '')
        return [m.strip() for m in models.split(',') if m.strip()]

    @staticmethod
    def get_default_model(provider: str) -> Optional[str]:
        """獲取指定提供者的預設模型"""
        default_key = f'{provider.upper()}_DEFAULT_MODEL'
        return os.getenv(default_key, '').strip() or None

    @staticmethod
    def is_model_available(provider: str, model_id: str) -> bool:
        """檢查模型是否可用"""
        available_models = AIProviderConfig.get_available_models(provider)
        return model_id in available_models

    @staticmethod
    def get_provider_config(provider: str) -> Dict[str, any]:
        """獲取提供者的完整配置"""
        return {
            'provider': provider,
            'models': AIProviderConfig.get_provider_models(provider),
            'available_models': AIProviderConfig.get_available_models(provider),
            'default_model': AIProviderConfig.get_default_model(provider),
            'enabled': provider in AIProviderConfig.get_enabled_providers()
        }

    @staticmethod
    def get_all_providers_config() -> Dict[str, Dict[str, any]]:
        """獲取所有提供者的配置"""
        configs = {}
        for provider in AIProviderConfig.get_enabled_providers():
            configs[provider] = AIProviderConfig.get_provider_config(provider)
        return configs


class ModelNameMapper:
    """模型名稱映射器"""

    NAME_MAPPING = {
        'OPENAI': {
            'gpt-4o-mini': 'GPT-4o Mini',
            'gpt-4o': 'GPT-4o',
            'gpt-4.1-nano': 'GPT-4.1 Nano',
            'gpt-3.5-turbo': 'GPT-3.5 Turbo'
        },
        'GEMINI': {
            'gemini-1.5-flash': 'Gemini 1.5 Flash',
            'gemini-1.5-pro': 'Gemini 1.5 Pro'
        },
        'QWEN': {
            'qwen-turbo': 'Qwen Turbo',
            'qwen-plus': 'Qwen Plus'
        },
        'MOCK': {
            'mock-ai': 'Mock AI (測試用)'
        }
    }

    @staticmethod
    def get_display_name(provider: str, model_id: str) -> str:
        """獲取模型的顯示名稱"""
        provider_upper = provider.upper()
        mapping = ModelNameMapper.NAME_MAPPING.get(provider_upper, {})
        return mapping.get(model_id, f'{provider} {model_id}')

    @staticmethod
    def get_provider_display_name(provider: str) -> str:
        """獲取提供者的顯示名稱"""
        provider_names = {
            'openai': 'OpenAI',
            'gemini': 'Google Gemini',
            'qwen': 'Qwen',
            'mock': 'Mock AI'
        }
        return provider_names.get(provider.lower(), provider.title())
