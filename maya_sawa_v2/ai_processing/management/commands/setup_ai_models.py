import os
from django.core.management.base import BaseCommand
from django.conf import settings
from maya_sawa_v2.ai_processing.models import AIModel


class Command(BaseCommand):
    help = '從環境變數設置 AI 模型'

    def handle(self, *args, **options):
        # 獲取啟用的提供者
        enabled_providers = os.getenv('ENABLED_PROVIDERS', 'openai,mock').split(',')

        created_count = 0
        updated_count = 0

        for provider in enabled_providers:
            provider = provider.strip().upper()

            # 獲取該提供者的所有模型
            models_key = f'{provider}_MODELS'
            available_models_key = f'{provider}_AVAILABLE_MODELS'
            default_model_key = f'{provider}_DEFAULT_MODEL'

            all_models = os.getenv(models_key, '').split(',')
            available_models = os.getenv(available_models_key, '').split(',')
            default_model = os.getenv(default_model_key, '')

            if not all_models or all_models == ['']:
                self.stdout.write(
                    self.style.WARNING(f'跳過 {provider}：未找到模型配置')
                )
                continue

            # 為每個模型創建記錄
            for model_id in all_models:
                model_id = model_id.strip()
                if not model_id:
                    continue

                # 檢查是否為可用模型
                is_available = model_id in available_models

                # 生成模型名稱
                model_name = self._generate_model_name(provider, model_id)

                model_data = {
                    'name': model_name,
                    'provider': provider.lower(),
                    'model_id': model_id,
                    'is_active': is_available,
                    'config': {
                        'model': model_id,
                        'max_tokens': 1000,
                        'temperature': 0.7
                    }
                }

                model, created = AIModel.objects.get_or_create(
                    name=model_name,
                    defaults=model_data
                )

                if created:
                    created_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'創建 AI 模型: {model.name} ({model.provider})')
                    )
                else:
                    # 更新現有模型
                    for key, value in model_data.items():
                        if key != 'name':  # 不更新名稱
                            setattr(model, key, value)
                    model.save()
                    updated_count += 1
                    self.stdout.write(
                        self.style.WARNING(f'更新 AI 模型: {model.name} ({model.provider})')
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f'AI 模型設置完成！創建: {created_count}, 更新: {updated_count}'
            )
        )

        # 顯示當前配置
        self.stdout.write('\n當前 AI 模型配置:')
        for model in AIModel.objects.all().order_by('provider', 'name'):
            status = "✅ 可用" if model.is_active else "❌ 不可用"
            self.stdout.write(f'  - {model.name} ({model.provider}) - {status}')

    def _generate_model_name(self, provider, model_id):
        """生成模型顯示名稱"""
        name_mapping = {
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
            }
        }

        return name_mapping.get(provider, {}).get(model_id, f'{provider} {model_id}')
