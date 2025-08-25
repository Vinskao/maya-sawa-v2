import logging
from typing import Dict, Any, Optional

try:
    from langgraph.graph import StateGraph, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    StateGraph = None
    END = None
from maya_sawa_v2.agent.models import AgentState, WorkflowResult
from maya_sawa_v2.agent.nodes import (
    classify_intent_node,
    retrieve_knowledge_node,
    select_tools_node,
    execute_tools_node,
    generate_response_node,
    save_result_node,
    error_handler_node
)
from maya_sawa_v2.ai_processing.models import AIModel

logger = logging.getLogger(__name__)


class MayaAgentWorkflow:
    """Maya Agent 工作流 - 使用 LangGraph 編排"""

    def __init__(self):
        if not LANGGRAPH_AVAILABLE:
            logger.warning("LangGraph not available, workflow will be disabled")
            self.graph = None
        else:
            self.graph = self._build_graph()
            logger.info("Maya Agent Workflow initialized")

    def _build_graph(self) -> StateGraph:
        """構建工作流圖"""
        if not LANGGRAPH_AVAILABLE:
            raise ImportError("LangGraph is not available")
        workflow = StateGraph(AgentState)

        # 添加節點
        workflow.add_node("classify_intent", classify_intent_node)
        workflow.add_node("retrieve_knowledge", retrieve_knowledge_node)
        workflow.add_node("select_tools", select_tools_node)
        workflow.add_node("execute_tools", execute_tools_node)
        workflow.add_node("generate_response", generate_response_node)
        workflow.add_node("save_result", save_result_node)
        workflow.add_node("error_handler", error_handler_node)

        # 添加邊 - 線性流程
        workflow.add_edge("classify_intent", "retrieve_knowledge")
        workflow.add_edge("retrieve_knowledge", "select_tools")
        workflow.add_edge("select_tools", "execute_tools")
        workflow.add_edge("execute_tools", "generate_response")
        workflow.add_edge("generate_response", "save_result")
        workflow.add_edge("save_result", END)

        # 錯誤處理邊
        workflow.add_edge("error_handler", END)

        # 添加條件邊 - 如果出現錯誤，跳轉到錯誤處理
        workflow.add_conditional_edges(
            "classify_intent",
            self._should_continue,
            {
                "continue": "retrieve_knowledge",
                "error": "error_handler"
            }
        )

        workflow.add_conditional_edges(
            "retrieve_knowledge",
            self._should_continue,
            {
                "continue": "select_tools",
                "error": "error_handler"
            }
        )

        workflow.add_conditional_edges(
            "select_tools",
            self._should_continue,
            {
                "continue": "execute_tools",
                "error": "error_handler"
            }
        )

        workflow.add_conditional_edges(
            "execute_tools",
            self._should_continue,
            {
                "continue": "generate_response",
                "error": "error_handler"
            }
        )

        workflow.add_conditional_edges(
            "generate_response",
            self._should_continue,
            {
                "continue": "save_result",
                "error": "error_handler"
            }
        )

        # 設置入口點
        workflow.set_entry_point("classify_intent")

        return workflow.compile()

    def _should_continue(self, state: AgentState) -> str:
        """判斷是否應該繼續執行"""
        if state.error_message or not state.should_continue:
            return "error"
        return "continue"

    async def execute(self,
                     user_input: str,
                     user_id: int,
                     session_id: str,
                     ai_model: Optional[AIModel] = None) -> WorkflowResult:
        """執行工作流"""
        try:
            logger.info(f"Starting workflow execution for session: {session_id}")

            # 初始化狀態
            initial_state = AgentState(
                user_input=user_input,
                user_id=user_id,
                session_id=session_id,
                ai_model=ai_model
            )

            # 執行工作流
            final_state = await self.graph.ainvoke(initial_state)

            # 構建結果
            result = WorkflowResult(
                success=not bool(final_state.error_message),
                response=final_state.ai_response or "抱歉，無法生成回應",
                knowledge_used=final_state.knowledge_used,
                knowledge_sources=final_state.knowledge_sources,
                tools_used=final_state.tools_used,
                metadata={
                    'intent': final_state.intent,
                    'confidence': final_state.confidence,
                    'current_step': final_state.current_step,
                    'tool_results': final_state.tool_results,
                    'ai_metadata': final_state.ai_metadata
                },
                error_message=final_state.error_message
            )

            logger.info(f"Workflow execution completed for session: {session_id}")
            return result

        except Exception as e:
            logger.error(f"Workflow execution failed: {str(e)}")
            return WorkflowResult(
                success=False,
                response="抱歉，處理您的請求時發生錯誤",
                error_message=str(e)
            )

    def execute_sync(self,
                    user_input: str,
                    user_id: int,
                    session_id: str,
                    ai_model: Optional[AIModel] = None) -> WorkflowResult:
        """同步執行工作流"""
        import asyncio

        try:
            # 在同步環境中運行異步函數
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                self.execute(user_input, user_id, session_id, ai_model)
            )
            loop.close()
            return result
        except Exception as e:
            logger.error(f"Sync workflow execution failed: {str(e)}")
            return WorkflowResult(
                success=False,
                response="抱歉，處理您的請求時發生錯誤",
                error_message=str(e)
            )


# 全局工作流實例
maya_agent_workflow = MayaAgentWorkflow()
