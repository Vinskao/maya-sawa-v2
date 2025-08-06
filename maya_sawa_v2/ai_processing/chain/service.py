import logging
from typing import Dict, Any, Optional
from django.conf import settings
from .manager import FilterChainManager
from .filters import KeywordFilter, IntentFilter, DomainFilter, SentimentFilter
from .base import FilterContext, FilterResult

logger = logging.getLogger(__name__)


class ConversationTypeService:
    """對話類型分類服務"""

    def __init__(self):
        self.chain_manager = FilterChainManager()
        self._setup_filters()

    def _setup_filters(self):
        """設置過濾器鏈"""
        # 從設定檔獲取過濾器配置
        filter_configs = getattr(settings, 'FILTER_CHAIN_CONFIG', {})

        # 添加過濾器到鏈中（按優先級順序）
        self.chain_manager.add_filter(
            KeywordFilter(config=filter_configs.get('keyword_filter', {}))
        )
        self.chain_manager.add_filter(
            IntentFilter(config=filter_configs.get('intent_filter', {}))
        )
        self.chain_manager.add_filter(
            DomainFilter(config=filter_configs.get('domain_filter', {}))
        )
        self.chain_manager.add_filter(
            SentimentFilter(config=filter_configs.get('sentiment_filter', {}))
        )

        logger.info(f"Filter chain setup completed with {len(self.chain_manager)} filters")

    def classify_conversation_type(self, message: str, user_id: int, conversation_id: str,
                                 current_type: str = 'general') -> Dict[str, Any]:
        """分類對話類型"""
        # 創建過濾器上下文
        context = FilterContext(
            message=message,
            user_id=user_id,
            conversation_id=conversation_id,
            conversation_type=current_type
        )

        # 執行過濾器鏈
        result = self.chain_manager.process(context)

        # 返回分類結果
        return {
            'conversation_type': result.conversation_type or current_type,
            'confidence': result.confidence,
            'reason': result.reason,
            'metadata': result.metadata or {},
            'should_update': result.conversation_type != current_type
        }

    def get_filter_chain_info(self) -> Dict[str, Any]:
        """獲取過濾器鏈資訊"""
        return {
            'total_filters': len(self.chain_manager),
            'filter_names': self.chain_manager.list_filters(),
            'chain_status': 'active'
        }


# 全局服務實例
conversation_type_service = ConversationTypeService()
