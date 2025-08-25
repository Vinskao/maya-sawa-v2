import logging
from typing import Dict, Any, Optional
from maya_sawa_v2.agent.workflow import maya_agent_workflow
from maya_sawa_v2.agent.models import WorkflowResult
from maya_sawa_v2.ai_processing.models import AIModel
from maya_sawa_v2.conversations.models import Conversation, Message
from maya_sawa_v2.api.services.message_service import MessageAppService

logger = logging.getLogger(__name__)


class MayaAgentService:
    """Maya Agent 服務 - 整合 LangGraph 工作流到現有 API"""
    
    def __init__(self):
        self.message_service = MessageAppService()
        logger.info("Maya Agent Service initialized")
    
    def process_request(self,
                       question: str,
                       model_name: str,
                       session_id: str,
                       user_id: int,
                       use_knowledge_base: bool = True,
                       sync: bool = True) -> Dict[str, Any]:
        """處理用戶請求 - 保持與現有 API 格式兼容"""
        
        try:
            logger.info(f"Processing request for session: {session_id}, model: {model_name}")
            
            # 獲取或創建對話
            conversation, created = Conversation.objects.get_or_create(
                id=session_id,
                defaults={'user_id': user_id}
            )
            
            # 獲取 AI 模型
            ai_model = self._get_ai_model(model_name)
            if not ai_model:
                return {
                    'error': f'Model {model_name} not found or not available',
                    'success': False
                }
            
            # 創建用戶消息
            user_message = Message.objects.create(
                conversation=conversation,
                message_type="user",
                content=question
            )
            
            if sync:
                # 同步處理 - 使用 LangGraph 工作流
                result = self._process_sync(
                    question=question,
                    user_id=user_id,
                    session_id=session_id,
                    ai_model=ai_model,
                    use_knowledge_base=use_knowledge_base
                )
                
                # 創建 AI 回應消息
                if result.success:
                    Message.objects.create(
                        conversation=conversation,
                        message_type="ai",
                        content=result.response,
                        metadata={
                            'knowledge_used': result.knowledge_used,
                            'knowledge_sources': result.knowledge_sources,
                            'tools_used': result.tools_used,
                            'workflow_metadata': result.metadata
                        }
                    )
                
                # 返回與現有 API 格式兼容的回應
                return {
                    'response': result.response,
                    'knowledge_used': result.knowledge_used,
                    'knowledge_sources': result.knowledge_sources,
                    'tools_used': result.tools_used,
                    'metadata': result.metadata,
                    'success': result.success,
                    'error_message': result.error_message
                }
            else:
                # 異步處理 - 使用現有的 Celery 任務
                task = self.message_service.create_user_message_and_enqueue(
                    conversation=conversation,
                    content=question,
                    ai_model_id=ai_model.id
                )
                
                return {
                    'task_id': str(task.id),
                    'status': 'queued',
                    'message': 'Task has been queued for processing'
                }
                
        except Exception as e:
            logger.error(f"Error processing request: {str(e)}")
            return {
                'error': f'Processing failed: {str(e)}',
                'success': False
            }
    
    def _process_sync(self,
                     question: str,
                     user_id: int,
                     session_id: str,
                     ai_model: AIModel,
                     use_knowledge_base: bool = True) -> WorkflowResult:
        """同步處理請求"""
        
        try:
            # 使用 LangGraph 工作流
            result = maya_agent_workflow.execute_sync(
                user_input=question,
                user_id=user_id,
                session_id=session_id,
                ai_model=ai_model
            )
            
            # 如果不使用知識庫，覆蓋結果
            if not use_knowledge_base:
                result.knowledge_used = False
                result.knowledge_sources = []
            
            return result
            
        except Exception as e:
            logger.error(f"Sync processing failed: {str(e)}")
            return WorkflowResult(
                success=False,
                response="抱歉，處理您的請求時發生錯誤",
                error_message=str(e)
            )
    
    def _get_ai_model(self, model_name: str) -> Optional[AIModel]:
        """根據模型名稱獲取 AI 模型"""
        try:
            return AIModel.objects.get(name=model_name, is_active=True)
        except AIModel.DoesNotExist:
            logger.warning(f"Model {model_name} not found")
            return None
    
    def get_workflow_status(self, session_id: str) -> Dict[str, Any]:
        """獲取工作流狀態"""
        try:
            # 獲取最近的對話記錄
            conversation = Conversation.objects.filter(id=session_id).first()
            if not conversation:
                return {'status': 'not_found'}
            
            messages = Message.objects.filter(conversation=conversation).order_by('-created_at')[:10]
            
            return {
                'status': 'active',
                'session_id': session_id,
                'message_count': messages.count(),
                'last_message': messages.first().content if messages.exists() else None,
                'last_message_type': messages.first().message_type if messages.exists() else None
            }
            
        except Exception as e:
            logger.error(f"Error getting workflow status: {str(e)}")
            return {'status': 'error', 'error': str(e)}


# 全局服務實例
maya_agent_service = MayaAgentService()
