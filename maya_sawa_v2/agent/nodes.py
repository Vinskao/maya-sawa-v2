import logging
from typing import Dict, Any
from maya_sawa_v2.agent.models import AgentState
from maya_sawa_v2.ai_processing.chain.service import conversation_type_service
from maya_sawa_v2.ai_processing.km_sources.manager import KMSourceManager
from maya_sawa_v2.ai_processing.services.ai_response_service import AIResponseService
from maya_sawa_v2.conversations.models import Conversation, Message
from maya_sawa_v2.ai_processing.models import AIModel

logger = logging.getLogger(__name__)


def classify_intent_node(state: AgentState) -> AgentState:
    """意圖分類節點 - 使用現有的 FilterChain 邏輯"""
    try:
        logger.info(f"Classifying intent for: {state.user_input[:50]}...")
        
        # 使用現有的 conversation_type_service
        result = conversation_type_service.classify_conversation_type(
            message=state.user_input,
            user_id=state.user_id,
            conversation_id=state.session_id,
            current_type='general'
        )
        
        # 更新狀態
        state.intent = result['conversation_type']
        state.confidence = result['confidence']
        state.reason = result['reason']
        state.metadata.update(result.get('metadata', {}))
        state.current_step = "intent_classified"
        
        logger.info(f"Intent classified as: {state.intent} (confidence: {state.confidence})")
        
    except Exception as e:
        logger.error(f"Error in intent classification: {str(e)}")
        state.error_message = f"Intent classification failed: {str(e)}"
        state.should_continue = False
    
    return state


def retrieve_knowledge_node(state: AgentState) -> AgentState:
    """知識檢索節點"""
    try:
        logger.info("Retrieving knowledge context...")
        
        # 使用現有的 KMSourceManager
        km_manager = KMSourceManager()
        from maya_sawa_v2.ai_processing.km_sources.base import KMQuery
        
        # 創建查詢對象
        query = KMQuery(
            query=state.user_input,
            user_id=state.user_id,
            conversation_id=state.session_id
        )
        
        # 搜索所有適合的知識庫
        knowledge_results = km_manager.search_all_suitable(query)
        
        if knowledge_results:
            # 構建知識上下文
            context_parts = []
            sources = []
            
            for result in knowledge_results[:5]:  # 限制前5個結果
                context_parts.append(f"內容: {result.content}")
                sources.append({
                    'content': result.content[:200] + '...' if len(result.content) > 200 else result.content,
                    'score': result.relevance_score,
                    'source': result.source
                })
            
            state.knowledge_context = "\n\n".join(context_parts)
            state.knowledge_used = True
            state.knowledge_sources = sources
            logger.info(f"Found {len(sources)} knowledge sources")
        else:
            state.knowledge_used = False
            state.knowledge_context = None
            logger.info("No relevant knowledge found")
        
        state.current_step = "knowledge_retrieved"
        
    except Exception as e:
        logger.error(f"Error in knowledge retrieval: {str(e)}")
        state.error_message = f"Knowledge retrieval failed: {str(e)}"
        state.should_continue = False
    
    return state


def select_tools_node(state: AgentState) -> AgentState:
    """工具選擇節點"""
    try:
        logger.info("Selecting tools based on intent...")
        
        # 根據意圖和用戶輸入選擇工具
        tools_to_use = []
        
        # 檢查是否需要 PDF 解析
        if any(keyword in state.user_input.lower() for keyword in ['pdf', '文件', '文檔']):
            tools_to_use.append('pdf_parser')
        
        # 檢查是否需要 OCR
        if any(keyword in state.user_input.lower() for keyword in ['ocr', '圖片', '圖像', '識別']):
            tools_to_use.append('ocr_tool')
        
        # 檢查是否需要計算
        if any(keyword in state.user_input.lower() for keyword in ['計算', '算', '數學', '公式']):
            tools_to_use.append('calculator')
        
        # 檢查是否需要搜索
        if any(keyword in state.user_input.lower() for keyword in ['搜索', '查詢', '查找', '最新']):
            tools_to_use.append('web_search')
        
        state.tools_used = tools_to_use
        state.current_step = "tools_selected"
        
        logger.info(f"Selected tools: {tools_to_use}")
        
    except Exception as e:
        logger.error(f"Error in tool selection: {str(e)}")
        state.error_message = f"Tool selection failed: {str(e)}"
        state.should_continue = False
    
    return state


def execute_tools_node(state: AgentState) -> AgentState:
    """工具執行節點"""
    try:
        logger.info(f"Executing tools: {state.tools_used}")
        
        tool_results = {}
        
        for tool_name in state.tools_used:
            try:
                if tool_name == 'pdf_parser':
                    # 這裡可以實現 PDF 解析邏輯
                    tool_results[tool_name] = {'status': 'not_implemented', 'message': 'PDF parser not implemented yet'}
                
                elif tool_name == 'ocr_tool':
                    # 這裡可以實現 OCR 邏輯
                    tool_results[tool_name] = {'status': 'not_implemented', 'message': 'OCR tool not implemented yet'}
                
                elif tool_name == 'calculator':
                    # 這裡可以實現計算邏輯
                    tool_results[tool_name] = {'status': 'not_implemented', 'message': 'Calculator not implemented yet'}
                
                elif tool_name == 'web_search':
                    # 這裡可以實現搜索邏輯
                    tool_results[tool_name] = {'status': 'not_implemented', 'message': 'Web search not implemented yet'}
                
            except Exception as e:
                logger.error(f"Error executing tool {tool_name}: {str(e)}")
                tool_results[tool_name] = {'status': 'error', 'error': str(e)}
        
        state.tool_results = tool_results
        state.current_step = "tools_executed"
        
        logger.info(f"Tool execution completed: {list(tool_results.keys())}")
        
    except Exception as e:
        logger.error(f"Error in tool execution: {str(e)}")
        state.error_message = f"Tool execution failed: {str(e)}"
        state.should_continue = False
    
    return state


def generate_response_node(state: AgentState) -> AgentState:
    """AI 回應生成節點"""
    try:
        logger.info("Generating AI response...")
        
        # 使用現有的 AIResponseService
        ai_service = AIResponseService()
        
        # 構建上下文
        context_extra = {
            'knowledge_context': state.knowledge_context,
            'knowledge_used': state.knowledge_used,
            'knowledge_sources': state.knowledge_sources,
            'tools_used': state.tools_used,
            'tool_results': state.tool_results,
            'intent': state.intent,
            'confidence': state.confidence
        }
        
        # 生成回應
        if state.ai_model:
            # 創建一個臨時的 Message 對象
            from maya_sawa_v2.conversations.models import Message
            temp_message = Message(
                conversation=state.conversation,
                message_type="user",
                content=state.user_input
            )
            
            response = ai_service.process_sync(
                user_message=temp_message,
                ai_model=state.ai_model,
                knowledge_context=state.knowledge_context
            )
            
            state.ai_response = response
            state.current_step = "response_generated"
            
            logger.info("AI response generated successfully")
        else:
            raise ValueError("No AI model specified")
        
    except Exception as e:
        logger.error(f"Error in response generation: {str(e)}")
        state.error_message = f"Response generation failed: {str(e)}"
        state.should_continue = False
    
    return state


def save_result_node(state: AgentState) -> AgentState:
    """保存結果節點"""
    try:
        logger.info("Saving conversation result...")
        
        # 這裡可以添加保存到資料庫的邏輯
        # 目前只是記錄日誌
        logger.info(f"Conversation saved - Session: {state.session_id}, Response: {state.ai_response[:100]}...")
        
        state.current_step = "result_saved"
        
    except Exception as e:
        logger.error(f"Error in saving result: {str(e)}")
        state.error_message = f"Result saving failed: {str(e)}"
        state.should_continue = False
    
    return state


def error_handler_node(state: AgentState) -> AgentState:
    """錯誤處理節點"""
    if state.error_message:
        logger.error(f"Workflow error: {state.error_message}")
        # 可以添加錯誤處理邏輯，比如發送通知、記錄到監控系統等
        state.ai_response = f"抱歉，處理您的請求時發生錯誤：{state.error_message}"
    
    return state
