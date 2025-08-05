import uuid
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Conversation(models.Model):
    """對話會話模型"""

    CONVERSATION_STATUS = [
        ('active', _('Active')),
        ('closed', _('Closed')),
        ('pending', _('Pending')),
    ]

    CONVERSATION_TYPE = [
        ('customer_service', _('Customer Service')),
        ('knowledge_query', _('Knowledge Query')),
        ('general', _('General')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    session_id = models.CharField(max_length=255, unique=True)
    conversation_type = models.CharField(max_length=20, choices=CONVERSATION_TYPE, default='general')
    status = models.CharField(max_length=10, choices=CONVERSATION_STATUS, default='active')
    title = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = 'maya_sawa_v2_conversations'
        ordering = ['-created_at']

    def __str__(self):
        return f"Conversation {self.session_id} - {self.user.username}"


class Message(models.Model):
    """對話訊息模型"""

    MESSAGE_TYPE = [
        ('user', _('User Message')),
        ('ai', _('AI Response')),
        ('system', _('System Message')),
    ]

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE)
    content = models.TextField()
    metadata = models.JSONField(default=dict, blank=True)  # 儲存 AI 模型資訊、處理時間等
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = 'maya_sawa_v2_conversations'
        ordering = ['created_at']

    def __str__(self):
        return f"{self.message_type} message in {self.conversation.session_id}"
