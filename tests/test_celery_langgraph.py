#!/usr/bin/env python3
"""
測試 Celery 和 LangGraph 整合的腳本

這個腳本用於驗證：
1. Celery Worker 是否正常運行
2. LangGraph 工作流是否正常執行
3. RabbitMQ 連接是否正常
4. API 端點是否正常響應
"""

import os
import sys
import time
import requests
import subprocess
import json
from pathlib import Path

# 設置 Django 環境
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

import django
django.setup()

from maya_sawa_v2.ai_processing.models import AIModel
from maya_sawa_v2.agent import maya_agent_service


def test_celery_worker():
    """測試 Celery Worker 是否正常運行"""
    print("🔍 測試 Celery Worker...")

    try:
        # 檢查 Celery Worker 進程
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )

        if 'celery' in result.stdout.lower():
            print("✅ Celery Worker 進程正在運行")
            return True
        else:
            print("❌ 未找到 Celery Worker 進程")
            print("請啟動 Celery Worker:")
            print("  poetry run celery -A config worker -l info -Q maya_v2")
            return False

    except Exception as e:
        print(f"❌ 檢查 Celery Worker 時出錯: {str(e)}")
        return False


def test_rabbitmq_connection():
    """測試 RabbitMQ 連接"""
    print("\n🔍 測試 RabbitMQ 連接...")

    try:
        # 檢查 RabbitMQ 端口是否開放
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', 5672))
        sock.close()

        if result == 0:
            print("✅ RabbitMQ 端口 5672 開放")
            return True
        else:
            print("❌ RabbitMQ 端口 5672 未開放")
            print("請啟動 RabbitMQ:")
            print("  docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 \\")
            print("    -e RABBITMQ_DEFAULT_USER=admin -e RABBITMQ_DEFAULT_PASS=admin123 \\")
            print("    rabbitmq:3-management")
            return False

    except Exception as e:
        print(f"❌ 檢查 RabbitMQ 時出錯: {str(e)}")
        return False


def test_ai_models():
    """測試 AI 模型是否可用"""
    print("\n🔍 測試 AI 模型...")

    try:
        models = AIModel.objects.filter(is_active=True)
        if models.exists():
            print(f"✅ 找到 {models.count()} 個可用模型:")
            for model in models:
                print(f"   - {model.name} ({model.provider})")
            return models.first()
        else:
            print("❌ 沒有找到可用的 AI 模型")
            print("請運行: python manage.py setup_ai_models")
            return None

    except Exception as e:
        print(f"❌ 檢查 AI 模型時出錯: {str(e)}")
        return None


def test_langgraph_workflow():
    """測試 LangGraph 工作流"""
    print("\n🔍 測試 LangGraph 工作流...")

    try:
        # 測試工作流組件
        from maya_sawa_v2.agent.workflow import MayaAgentWorkflow
        workflow = MayaAgentWorkflow()
        print("✅ LangGraph 工作流初始化成功")

        # 測試節點
        from maya_sawa_v2.agent.nodes import classify_intent_node
        from maya_sawa_v2.agent.models import AgentState

        test_state = AgentState(
            user_input="測試問題",
            user_id=1,
            session_id="test_session"
        )

        result_state = classify_intent_node(test_state)
        print("✅ 意圖分類節點測試成功")

        return True

    except Exception as e:
        print(f"❌ LangGraph 工作流測試失敗: {str(e)}")
        return False


def test_api_endpoint():
    """測試 API 端點"""
    print("\n🔍 測試 API 端點...")

    try:
        # 測試健康檢查端點
        response = requests.get('http://127.0.0.1:8000/healthz', timeout=5)
        if response.status_code == 200:
            print("✅ API 服務器正在運行")
            return True
        else:
            print(f"❌ API 服務器響應異常: {response.status_code}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ 無法連接到 API 服務器")
        print("請啟動 Django 服務器:")
        print("  poetry run python manage.py runserver")
        return False
    except Exception as e:
        print(f"❌ API 測試失敗: {str(e)}")
        return False


def test_agent_service():
    """測試 Agent 服務"""
    print("\n🔍 測試 Agent 服務...")

    try:
        # 獲取測試模型
        model = AIModel.objects.filter(is_active=True).first()
        if not model:
            print("❌ 沒有可用的 AI 模型")
            return False

        # 測試 Agent 服務
        result = maya_agent_service.process_request(
            question="你好，這是一個測試問題",
            model_name=model.name,
            session_id="test_session_123",
            user_id=1,
            use_knowledge_base=True,
            sync=True
        )

        if result.get('success', False):
            print("✅ Agent 服務測試成功")
            print(f"   回應: {result['response'][:100]}...")
            print(f"   知識庫使用: {result.get('knowledge_used', False)}")
            print(f"   工具使用: {result.get('tools_used', [])}")
            return True
        else:
            print(f"❌ Agent 服務測試失敗: {result.get('error_message', '未知錯誤')}")
            return False

    except Exception as e:
        print(f"❌ Agent 服務測試失敗: {str(e)}")
        return False


def test_celery_task():
    """測試 Celery 任務"""
    print("\n🔍 測試 Celery 任務...")

    try:
        from maya_sawa_v2.ai_processing.tasks import process_ai_response
        from maya_sawa_v2.ai_processing.models import ProcessingTask
        from maya_sawa_v2.conversations.models import Conversation, Message
        from maya_sawa_v2.ai_processing.models import AIModel

        # 創建測試數據
        model = AIModel.objects.filter(is_active=True).first()
        if not model:
            print("❌ 沒有可用的 AI 模型")
            return False

        conversation = Conversation.objects.create(user_id=1)
        user_message = Message.objects.create(
            conversation=conversation,
            message_type="user",
            content="Celery 測試問題"
        )

        # 創建處理任務
        task = ProcessingTask.objects.create(
            conversation=conversation,
            message=user_message,
            ai_model=model
        )

        # 執行 Celery 任務
        print(f"   發送任務 {task.id} 到 Celery...")
        celery_task = process_ai_response.delay(task.id)

        # 等待任務完成
        print("   等待任務完成...")
        result = celery_task.get(timeout=30)

        print("✅ Celery 任務執行成功")
        return True

    except Exception as e:
        print(f"❌ Celery 任務測試失敗: {str(e)}")
        return False


def main():
    """主測試函數"""
    print("🚀 開始 Celery + LangGraph 整合測試")
    print("=" * 60)

    tests = [
        ("Celery Worker", test_celery_worker),
        ("RabbitMQ 連接", test_rabbitmq_connection),
        ("AI 模型", test_ai_models),
        ("LangGraph 工作流", test_langgraph_workflow),
        ("API 端點", test_api_endpoint),
        ("Agent 服務", test_agent_service),
        ("Celery 任務", test_celery_task),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} 測試異常: {str(e)}")
            results.append((test_name, False))

    # 輸出測試結果
    print("\n" + "=" * 60)
    print("📊 測試結果總結")
    print("=" * 60)

    passed = 0
    for test_name, result in results:
        status = "✅ 通過" if result else "❌ 失敗"
        print(f"{test_name:20} {status}")
        if result:
            passed += 1

    print(f"\n總計: {passed}/{len(results)} 項測試通過")

    if passed == len(results):
        print("\n🎉 所有測試通過！Celery + LangGraph 整合正常")
        return True
    else:
        print(f"\n💥 {len(results) - passed} 項測試失敗，請檢查配置")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
