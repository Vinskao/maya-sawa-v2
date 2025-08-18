"""
Filter到Source連接器 - 負責連接filter結果和知識庫源
"""

from typing import Dict, Any, List, Optional
from .chain.base import FilterResult
from .km_sources.base import KMQuery, KMResult
from .km_sources.manager import KMSourceManager


class FilterSourceConnector:
    """Filter到Source連接器"""

    def __init__(self, km_manager: KMSourceManager):
        self.km_manager = km_manager

        # 定義filter結果到source的映射規則
        self.source_mapping = {
            'programming_km': 'programmingkmsource',
            'general_km': 'generalkmsource',
            'customer_service_km': 'customerservicekmsource',
            'product_km': 'productkmsource',
            'service_km': 'servicekmsource',
            'technical_km': 'technicalkmsource',
        }

    def connect_filter_to_source(self, filter_result: FilterResult,
                               user_id: int, conversation_id: str) -> List[KMResult]:
        """連接filter結果到相應的知識庫源"""

        # 如果不是知識查詢，返回空結果
        if filter_result.conversation_type != 'knowledge_query':
            return []

        # 從filter結果中獲取知識庫源資訊
        km_source_name = filter_result.metadata.get('km_source', 'general_km')

        # 建立知識庫查詢
        km_query = KMQuery(
            query=filter_result.metadata.get('original_message', ''),
            user_id=user_id,
            conversation_id=conversation_id,
            domain=filter_result.conversation_type,
            confidence=filter_result.confidence,
            metadata=filter_result.metadata
        )

        # 根據映射規則確定source類型
        source_type = self.source_mapping.get(km_source_name, 'generalkmsource')

        # 搜尋對應的知識庫源
        results = self.km_manager.search_by_source_type(km_query, source_type)

        return results

    def get_available_sources(self) -> List[Dict[str, Any]]:
        """獲取可用的知識庫源資訊"""
        return self.km_manager.list_sources()

    def add_source_mapping(self, filter_source: str, km_source_type: str) -> None:
        """添加新的源映射規則"""
        self.source_mapping[filter_source] = km_source_type

    def remove_source_mapping(self, filter_source: str) -> bool:
        """移除源映射規則"""
        if filter_source in self.source_mapping:
            del self.source_mapping[filter_source]
            return True
        return False
