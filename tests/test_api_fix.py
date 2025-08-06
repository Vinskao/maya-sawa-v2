#!/usr/bin/env python3
"""
简单的API测试脚本
验证修复后的API是否正常工作
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000"
API_PREFIX = "/maya-v2"

def test_api_endpoints():
    """测试API端点"""
    print("=== Maya Sawa V2 API 测试 ===")
    print("✅ 认证已停用，无需Bearer Token")
    print()

    # 1. 测试获取对话列表
    print("1. 测试获取对话列表...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/conversations/")
        print(f"✅ 状态码: {response.status_code}")
        print(f"✅ 响应: {response.json()}")
    except Exception as e:
        print(f"❌ 错误: {e}")

    print()
    print("─" * 50)
    print()

    # 2. 测试获取AI模型
    print("2. 测试获取AI模型...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/ai-models/")
        print(f"✅ 状态码: {response.status_code}")
        print(f"✅ 响应: {response.json()}")
    except Exception as e:
        print(f"❌ 错误: {e}")

    print()
    print("─" * 50)
    print()

    # 3. 测试发送消息
    print("3. 测试发送消息...")
    try:
        data = {
            "content": "Java Spring Boot如何配置数据库连接？"
        }
        response = requests.post(
            f"{BASE_URL}{API_PREFIX}/conversations/1/send_message/",
            json=data,
            headers={"Content-Type": "application/json"}
        )
        print(f"✅ 状态码: {response.status_code}")
        print(f"✅ 响应: {response.json()}")
    except Exception as e:
        print(f"❌ 错误: {e}")

    print()
    print("─" * 50)
    print()

    # 4. 测试获取消息历史
    print("4. 测试获取消息历史...")
    try:
        response = requests.get(f"{BASE_URL}{API_PREFIX}/conversations/1/messages/")
        print(f"✅ 状态码: {response.status_code}")
        print(f"✅ 响应: {response.json()}")
    except Exception as e:
        print(f"❌ 错误: {e}")

    print()
    print("=== 测试完成 ===")

if __name__ == "__main__":
    test_api_endpoints()
