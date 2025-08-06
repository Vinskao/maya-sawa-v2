#!/usr/bin/env python3
"""
简单的API测试
"""

import requests

def test_conversations():
    """测试对话API"""
    url = "http://127.0.0.1:8000/maya-v2/conversations/"

    print(f"测试URL: {url}")

    try:
        response = requests.get(url)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.text[:200]}...")

        if response.status_code == 200:
            print("✅ API正常工作")
        else:
            print("❌ API有问题")

    except Exception as e:
        print(f"❌ 错误: {e}")

if __name__ == "__main__":
    test_conversations()
