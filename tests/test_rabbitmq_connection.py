#!/usr/bin/env python3
"""
測試 RabbitMQ 連接的腳本
"""
import os
import sys
import pika
from urllib.parse import urlparse

def test_rabbitmq_connection():
    """測試 RabbitMQ 連接"""
    try:
        # 從環境變數獲取 RabbitMQ 配置
        rabbitmq_enabled = os.getenv('RABBITMQ_ENABLED', 'false').lower() == 'true'

        if not rabbitmq_enabled:
            print("❌ RABBITMQ_ENABLED 未設置為 true")
            return False

        # 構建連接 URL
        host = os.getenv('RABBITMQ_HOST', 'localhost')
        port = int(os.getenv('RABBITMQ_PORT', '5672'))
        username = os.getenv('RABBITMQ_USERNAME', 'admin')
        password = os.getenv('RABBITMQ_PASSWORD', 'admin123')
        virtual_host = os.getenv('RABBITMQ_VIRTUAL_HOST', '/')

        # 測試連接
        print(f"🔗 嘗試連接到 RabbitMQ: {host}:{port}")
        print(f"👤 用戶名: {username}")
        print(f"🏠 Virtual Host: {virtual_host}")

        # 建立連接
        credentials = pika.PlainCredentials(username, password)
        parameters = pika.ConnectionParameters(
            host=host,
            port=port,
            virtual_host=virtual_host,
            credentials=credentials,
            heartbeat=10
        )

        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()

        # 測試創建隊列
        queue_name = 'test_queue'
        channel.queue_declare(queue=queue_name, durable=True)
        print(f"✅ 成功創建隊列: {queue_name}")

        # 清理測試隊列
        channel.queue_delete(queue=queue_name)
        print(f"🧹 清理測試隊列: {queue_name}")

        connection.close()
        print("✅ RabbitMQ 連接測試成功！")
        return True

    except Exception as e:
        print(f"❌ RabbitMQ 連接失敗: {str(e)}")
        return False

def test_celery_broker_url():
    """測試 Celery Broker URL"""
    try:
        broker_url = os.getenv('CELERY_BROKER_URL')
        if not broker_url:
            print("❌ CELERY_BROKER_URL 未設置")
            return False

        print(f"🔗 Celery Broker URL: {broker_url}")

        # 解析 URL
        parsed = urlparse(broker_url)
        if parsed.scheme == 'amqp':
            print("✅ 使用 AMQP 協議 (RabbitMQ)")
        elif parsed.scheme == 'redis':
            print("⚠️ 使用 Redis 協議")
        else:
            print(f"❓ 未知協議: {parsed.scheme}")

        return True

    except Exception as e:
        print(f"❌ Celery Broker URL 測試失敗: {str(e)}")
        return False

if __name__ == "__main__":
    print("🧪 RabbitMQ 連接測試")
    print("=" * 50)

    # 測試環境變數
    print("📋 環境變數檢查:")
    print(f"   RABBITMQ_ENABLED: {os.getenv('RABBITMQ_ENABLED', '未設置')}")
    print(f"   RABBITMQ_HOST: {os.getenv('RABBITMQ_HOST', '未設置')}")
    print(f"   RABBITMQ_PORT: {os.getenv('RABBITMQ_PORT', '未設置')}")
    print(f"   RABBITMQ_USERNAME: {os.getenv('RABBITMQ_USERNAME', '未設置')}")
    print()

    # 測試 Celery Broker URL
    print("🔗 Celery Broker URL 測試:")
    test_celery_broker_url()
    print()

    # 測試 RabbitMQ 連接
    print("🐰 RabbitMQ 連接測試:")
    success = test_rabbitmq_connection()

    if success:
        print("\n🎉 所有測試通過！RabbitMQ 配置正確。")
        sys.exit(0)
    else:
        print("\n💥 測試失敗！請檢查 RabbitMQ 配置。")
        sys.exit(1)
