#!/usr/bin/env python3
"""
LangGraph 整合測試腳本

這個腳本用於測試 LangGraph 工作流的整合情況
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

from maya_sawa_v2.agent import maya_agent_service
from maya_sawa_v2.ai_processing.models import AIModel


def test_langgraph_workflow():
    """測試 LangGraph 工作流"""
    print("🧪 LangGraph 整合測試")
    print("=" * 50)
    
    # 檢查是否有可用的 AI 模型
    try:
        ai_models = AIModel.objects.filter(is_active=True)
        if not ai_models.exists():
            print("❌ 沒有找到可用的 AI 模型")
            print("請先運行: python manage.py setup_ai_models")
            return False
        
        test_model = ai_models.first()
        print(f"✅ 找到可用模型: {test_model.name}")
        
    except Exception as e:
        print(f"❌ 檢查 AI 模型時出錯: {str(e)}")
        return False
    
    # 測試用例
    test_cases = [
        {
            'name': '一般對話',
            'question': '你好，請介紹一下你自己',
            'expected_tools': [],
            'expected_knowledge': True
        },
        {
            'name': '編程問題',
            'question': 'Python 中的裝飾器是什麼？',
            'expected_tools': [],
            'expected_knowledge': True
        },
        {
            'name': '工具需求',
            'question': '請幫我計算 123 + 456',
            'expected_tools': ['calculator'],
            'expected_knowledge': False
        },
        {
            'name': 'PDF 處理',
            'question': '請解析這個 PDF 文件',
            'expected_tools': ['pdf_parser'],
            'expected_knowledge': False
        }
    ]
    
    success_count = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📝 測試 {i}: {test_case['name']}")
        print(f"問題: {test_case['question']}")
        
        try:
            # 執行工作流
            result = maya_agent_service.process_request(
                question=test_case['question'],
                model_name=test_model.name,
                session_id=f"test_session_{i}",
                user_id=1,
                use_knowledge_base=True,
                sync=True
            )
            
            # 檢查結果
            if result.get('success', False):
                print(f"✅ 回應: {result['response'][:100]}...")
                print(f"   知識庫使用: {result.get('knowledge_used', False)}")
                print(f"   工具使用: {result.get('tools_used', [])}")
                
                # 驗證工具使用
                actual_tools = result.get('tools_used', [])
                expected_tools = test_case['expected_tools']
                
                if set(actual_tools) == set(expected_tools):
                    print(f"✅ 工具使用符合預期")
                else:
                    print(f"⚠️ 工具使用不符合預期: 期望 {expected_tools}, 實際 {actual_tools}")
                
                # 驗證知識庫使用
                knowledge_used = result.get('knowledge_used', False)
                expected_knowledge = test_case['expected_knowledge']
                
                if knowledge_used == expected_knowledge:
                    print(f"✅ 知識庫使用符合預期")
                else:
                    print(f"⚠️ 知識庫使用不符合預期: 期望 {expected_knowledge}, 實際 {knowledge_used}")
                
                success_count += 1
                
            else:
                print(f"❌ 處理失敗: {result.get('error_message', '未知錯誤')}")
                
        except Exception as e:
            print(f"❌ 測試執行失敗: {str(e)}")
    
    print(f"\n📊 測試結果: {success_count}/{len(test_cases)} 成功")
    
    if success_count == len(test_cases):
        print("🎉 所有測試通過！LangGraph 整合成功")
        return True
    else:
        print("💥 部分測試失敗，請檢查配置")
        return False


def test_workflow_components():
    """測試工作流組件"""
    print("\n🔧 工作流組件測試")
    print("=" * 30)
    
    try:
        # 測試 Agent 服務
        from maya_sawa_v2.agent.service import MayaAgentService
        service = MayaAgentService()
        print("✅ Agent 服務初始化成功")
        
        # 測試工作流
        from maya_sawa_v2.agent.workflow import MayaAgentWorkflow
        workflow = MayaAgentWorkflow()
        print("✅ LangGraph 工作流初始化成功")
        
        # 測試節點
        from maya_sawa_v2.agent.nodes import classify_intent_node
        from maya_sawa_v2.agent.models import AgentState
        
        test_state = AgentState(
            user_input="測試問題",
            user_id=1,
            session_id="test"
        )
        
        result_state = classify_intent_node(test_state)
        print("✅ 意圖分類節點測試成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 組件測試失敗: {str(e)}")
        return False


def main():
    """主函數"""
    print("🚀 開始 LangGraph 整合測試")
    
    # 測試組件
    if not test_workflow_components():
        print("💥 組件測試失敗，停止執行")
        return False
    
    # 測試工作流
    if not test_langgraph_workflow():
        print("💥 工作流測試失敗")
        return False
    
    print("\n🎉 LangGraph 整合測試完成！")
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
