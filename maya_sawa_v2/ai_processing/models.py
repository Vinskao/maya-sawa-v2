from django.db import models
from django.utils.translation import gettext_lazy as _


class AIModel(models.Model):
    """AI 模型配置"""

    name = models.CharField(max_length=100, unique=True)
    provider = models.CharField(max_length=50)  # OpenAI, Anthropic, etc.
    model_id = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    config = models.JSONField(default=dict)  # 模型特定配置
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'maya_sawa_v2_ai_processing'

    def __str__(self):
        return f"{self.provider} - {self.name}"


class ProcessingTask(models.Model):
    """AI 處理任務"""

    TASK_STATUS = [
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ]

    conversation = models.ForeignKey('maya_sawa_v2_conversations.Conversation', on_delete=models.CASCADE)
    message = models.ForeignKey('maya_sawa_v2_conversations.Message', on_delete=models.CASCADE)
    ai_model = models.ForeignKey(AIModel, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=TASK_STATUS, default='pending')
    result = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    processing_time = models.FloatField(null=True, blank=True)  # 秒
    knowledge_context = models.TextField(blank=True)  # 知識庫上下文
    knowledge_citations = models.JSONField(default=list)  # 知識庫引用
    knowledge_used = models.BooleanField(default=False)  # 是否使用了知識庫
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        app_label = 'maya_sawa_v2_ai_processing'
        ordering = ['-created_at']

    def __str__(self):
        return f"Task {self.id} - {self.status}"
