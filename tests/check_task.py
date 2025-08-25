#!/usr/bin/env python3
"""
檢查 Celery 任務狀態的腳本
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

from celery.result import AsyncResult
from config.celery import app

def check_task(task_id):
    """檢查任務狀態"""
    print(f"🔍 檢查任務: {task_id}")

    try:
        result = AsyncResult(task_id, app=app)
        print(f"Status: {result.status}")
        print(f"State: {result.state}")
        print(f"Ready: {result.ready()}")
        print(f"Successful: {result.successful()}")
        print(f"Failed: {result.failed()}")
        print(f"Info: {result.info}")
        print(f"Result: {result.result}")

        if result.failed():
            print(f"Error: {result.error}")
            print(f"Traceback: {result.traceback}")

    except Exception as e:
        print(f"❌ 檢查任務時出錯: {str(e)}")

if __name__ == "__main__":
    task_id = "315d9b28-f12a-4aa5-a423-f1baf545e07e"
    check_task(task_id)
