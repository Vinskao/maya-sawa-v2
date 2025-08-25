"""
Maya Agent 模組 - 基於 LangGraph 的智能代理系統

這個模組提供了基於 LangGraph 的 Agent 工作流，用於處理複雜的 AI 任務。
主要組件包括：

1. Agent 狀態管理 (models.py)
2. 工作流節點 (nodes.py)
3. LangGraph 工作流 (workflow.py)
4. Agent 服務層 (service.py)

使用方式：
    from maya_sawa_v2.agent import maya_agent_service
    
    # 處理用戶請求
    result = maya_agent_service.process_request(
        question="你的問題",
        model_name="gpt-4o-mini",
        session_id="session_123",
        user_id=1,
        use_knowledge_base=True,
        sync=True
    )
"""

from .service import maya_agent_service
from .workflow import maya_agent_workflow
from .models import AgentState, WorkflowResult

__all__ = [
    'maya_agent_service',
    'maya_agent_workflow',
    'AgentState',
    'WorkflowResult'
]
