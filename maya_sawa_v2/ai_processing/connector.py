"""
Filter到Source连接器 - 负责连接filter结果和知识库源
"""

from typing import Dict, Any, List, Optional
from .chain.base import FilterResult
from .km_sources.base import KMQuery, KMResult
from .km_sources.manager import KMSourceManager


class FilterSourceConnector:
    """Filter到Source连接器"""

    def __init__(self, km_manager: KMSourceManager):
        self.km_manager = km_manager

        # 定义filter结果到source的映射规则
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
        """连接filter结果到相应的知识库源"""

        # 如果不是知识查询，返回空结果
        if filter_result.conversation_type != 'knowledge_query':
            return []

        # 从filter结果中获取知识库源信息
        km_source_name = filter_result.metadata.get('km_source', 'general_km')

        # 创建知识库查询
        km_query = KMQuery(
            query=filter_result.metadata.get('original_message', ''),
            user_id=user_id,
            conversation_id=conversation_id,
            domain=filter_result.conversation_type,
            confidence=filter_result.confidence,
            metadata=filter_result.metadata
        )

        # 根据映射规则确定source类型
        source_type = self.source_mapping.get(km_source_name, 'generalkmsource')

        # 搜索对应的知识库源
        results = self.km_manager.search_by_source_type(km_query, source_type)

        return results

    def get_available_sources(self) -> List[Dict[str, Any]]:
        """获取可用的知识库源信息"""
        return self.km_manager.list_sources()

    def add_source_mapping(self, filter_source: str, km_source_type: str) -> None:
        """添加新的源映射规则"""
        self.source_mapping[filter_source] = km_source_type

    def remove_source_mapping(self, filter_source: str) -> bool:
        """移除源映射规则"""
        if filter_source in self.source_mapping:
            del self.source_mapping[filter_source]
            return True
        return False
