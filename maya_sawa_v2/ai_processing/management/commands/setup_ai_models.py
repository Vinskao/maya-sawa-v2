from django.core.management.base import BaseCommand
from maya_sawa_v2.ai_processing.models import AIModel


class Command(BaseCommand):
    help = '設置預設的 AI 模型配置'

    def handle(self, *args, **options):
        # 創建 GPT-4o-mini 模型
        gpt4o_mini, created = AIModel.objects.get_or_create(
            name="GPT-4o-mini",
            defaults={
                'provider': 'openai',
                'model_id': 'gpt-4o-mini',
                'is_active': True,
                'config': {
                    'model': 'gpt-4o-mini',
                    'max_tokens': 1000,
                    'temperature': 0.7
                }
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'成功創建 AI 模型: {gpt4o_mini.name}')
            )
        else:
            self.stdout.write(
                self.style.WARNING(f'AI 模型已存在: {gpt4o_mini.name}')
            )

        # 創建 Mock 模型（用於測試）
        mock_model, created = AIModel.objects.get_or_create(
            name="Mock AI",
            defaults={
                'provider': 'mock',
                'model_id': 'mock',
                'is_active': False,  # 預設不啟用
                'config': {}
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'成功創建 AI 模型: {mock_model.name}')
            )

        # 顯示所有模型
        self.stdout.write('\n當前 AI 模型:')
        for model in AIModel.objects.all():
            status = "✅ 啟用" if model.is_active else "❌ 停用"
            self.stdout.write(f'  - {model.name} ({model.provider}) - {status}')

        self.stdout.write(
            self.style.SUCCESS('\nAI 模型設置完成！')
        )
