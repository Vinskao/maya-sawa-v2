#!/usr/bin/env python3
"""
測試 Celery 任務的腳本
"""

import os
import sys
import django
from pathlib import Path

# 設置 Django 環境
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

django.setup()

from maya_sawa_v2.ai_processing.tasks import process_ai_response
from maya_sawa_v2.ai_processing.models import ProcessingTask, AIModel
from maya_sawa_v2.conversations.models import Conversation, Message
from maya_sawa_v2.users.models import User

def test_celery_task():
    """測試 Celery 任務"""
    print("🔍 測試 Celery 任務...")

    try:
        # 獲取或創建測試用戶
        user, created = User.objects.get_or_create(
            username='test_user',
            defaults={'email': 'test@example.com'}
        )

        # 獲取 AI 模型
        ai_model = AIModel.objects.filter(is_active=True).first()
        if not ai_model:
            print("❌ 沒有可用的 AI 模型")
            return False

        # 創建測試對話
        conversation = Conversation.objects.create(
            user=user,
            session_id=f"test-{os.getpid()}",
            conversation_type='general',
            title="Test Conversation"
        )

        # 創建測試消息
        message = Message.objects.create(
            conversation=conversation,
            message_type='user',
            content="這是一個測試問題：請簡單介紹一下你自己。"
        )

        # 創建處理任務
        processing_task = ProcessingTask.objects.create(
            conversation=conversation,
            message=message,
            ai_model=ai_model,
            status='queued'
        )

        print(f"✅ 創建了測試任務: {processing_task.id}")

        # 直接調用任務（同步）
        print("🔄 執行任務...")
        result = process_ai_response(processing_task.id)

        print(f"✅ 任務執行成功: {result}")
        return True

    except Exception as e:
        print(f"❌ 任務執行失敗: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_celery_task()
