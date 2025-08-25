from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from maya_sawa_v2.ai_processing.models import AIModel
from maya_sawa_v2.conversations.models import Conversation, Message


@dataclass
class AgentState:
    """Agent 工作流狀態"""
    
    # 用戶輸入
    user_input: str
    user_id: int
    session_id: str
    
    # 意圖分析結果
    intent: Optional[str] = None
    confidence: float = 0.0
    reason: Optional[str] = None
    
    # 知識檢索結果
    knowledge_context: Optional[str] = None
    knowledge_used: bool = False
    knowledge_sources: List[Dict[str, Any]] = field(default_factory=list)
    
    # 工具執行結果
    tools_used: List[str] = field(default_factory=list)
    tool_results: Dict[str, Any] = field(default_factory=dict)
    
    # AI 模型和回應
    ai_model: Optional[AIModel] = None
    ai_response: Optional[str] = None
    ai_metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 會話上下文
    conversation: Optional[Conversation] = None
    chat_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # 工作流控制
    current_step: str = "start"
    should_continue: bool = True
    error_message: Optional[str] = None
    
    # 元數據
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            'user_input': self.user_input,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'intent': self.intent,
            'confidence': self.confidence,
            'reason': self.reason,
            'knowledge_context': self.knowledge_context,
            'knowledge_used': self.knowledge_used,
            'knowledge_sources': self.knowledge_sources,
            'tools_used': self.tools_used,
            'tool_results': self.tool_results,
            'ai_model_id': self.ai_model.id if self.ai_model else None,
            'ai_response': self.ai_response,
            'ai_metadata': self.ai_metadata,
            'conversation_id': self.conversation.id if self.conversation else None,
            'chat_history': self.chat_history,
            'current_step': self.current_step,
            'should_continue': self.should_continue,
            'error_message': self.error_message,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentState':
        """從字典創建狀態"""
        return cls(
            user_input=data.get('user_input', ''),
            user_id=data.get('user_id', 0),
            session_id=data.get('session_id', ''),
            intent=data.get('intent'),
            confidence=data.get('confidence', 0.0),
            reason=data.get('reason'),
            knowledge_context=data.get('knowledge_context'),
            knowledge_used=data.get('knowledge_used', False),
            knowledge_sources=data.get('knowledge_sources', []),
            tools_used=data.get('tools_used', []),
            tool_results=data.get('tool_results', {}),
            ai_response=data.get('ai_response'),
            ai_metadata=data.get('ai_metadata', {}),
            chat_history=data.get('chat_history', []),
            current_step=data.get('current_step', 'start'),
            should_continue=data.get('should_continue', True),
            error_message=data.get('error_message'),
            metadata=data.get('metadata', {})
        )


@dataclass
class WorkflowResult:
    """工作流執行結果"""
    
    success: bool
    response: str
    knowledge_used: bool = False
    knowledge_sources: List[Dict[str, Any]] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    def to_api_response(self) -> Dict[str, Any]:
        """轉換為 API 回應格式"""
        return {
            'response': self.response,
            'knowledge_used': self.knowledge_used,
            'knowledge_sources': self.knowledge_sources,
            'tools_used': self.tools_used,
            'metadata': self.metadata,
            'success': self.success,
            'error_message': self.error_message
        }
