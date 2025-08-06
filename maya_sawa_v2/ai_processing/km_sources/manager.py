"""
知识库源管理器 - 负责管理所有知识库源
"""

import logging
from typing import List, Dict, Any, Optional
from .base import BaseKMSource, KMQuery, KMResult

logger = logging.getLogger(__name__)


class KMSourceManager:
    """知识库源管理器"""

    def __init__(self):
        self.sources: List[BaseKMSource] = []
        self._sources_by_name: Dict[str, BaseKMSource] = {}
        self._sources_by_type: Dict[str, BaseKMSource] = {}

    def add_source(self, source: BaseKMSource) -> None:
        """添加知识库源"""
        self.sources.append(source)
        self._sources_by_name[source.name] = source
        self._sources_by_type[source.get_source_type()] = source
        # 按优先级排序
        self.sources.sort(key=lambda s: s.get_priority())
        logger.info(f"Added KM source: {source.name} (type: {source.get_source_type()})")

    def get_source_by_name(self, name: str) -> Optional[BaseKMSource]:
        """根据名称获取知识库源"""
        return self._sources_by_name.get(name)

    def get_source_by_type(self, source_type: str) -> Optional[BaseKMSource]:
        """根据类型获取知识库源"""
        return self._sources_by_type.get(source_type)

    def get_suitable_sources(self, query: KMQuery) -> List[BaseKMSource]:
        """获取适合处理查询的知识库源"""
        suitable_sources = []
        for source in self.sources:
            if source.is_suitable_for(query):
                suitable_sources.append(source)
        return suitable_sources

    def search_by_source_name(self, query: KMQuery, source_name: str) -> List[KMResult]:
        """根据源名称搜索特定知识库"""
        source = self.get_source_by_name(source_name)
        if source and source.is_suitable_for(query):
            try:
                return source.search(query)
            except Exception as e:
                logger.error(f"Error searching source {source_name}: {e}")
                return []
        return []

    def search_by_source_type(self, query: KMQuery, source_type: str) -> List[KMResult]:
        """根据源类型搜索特定知识库"""
        source = self.get_source_by_type(source_type)
        if source and source.is_suitable_for(query):
            try:
                return source.search(query)
            except Exception as e:
                logger.error(f"Error searching source type {source_type}: {e}")
                return []
        return []

    def search_all_suitable(self, query: KMQuery) -> List[KMResult]:
        """搜索所有适合的知识库源"""
        suitable_sources = self.get_suitable_sources(query)
        all_results = []

        for source in suitable_sources:
            try:
                results = source.search(query)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Error searching source {source.name}: {e}")
                continue

        # 按相关性排序
        all_results.sort(key=lambda r: r.relevance_score, reverse=True)
        return all_results

    def list_sources(self) -> List[Dict[str, Any]]:
        """列出所有知识库源信息"""
        return [
            {
                'name': source.name,
                'type': source.get_source_type(),
                'priority': source.get_priority()
            }
            for source in self.sources
        ]

    def remove_source(self, source_name: str) -> bool:
        """移除知识库源"""
        if source_name in self._sources_by_name:
            source = self._sources_by_name[source_name]
            self.sources.remove(source)
            del self._sources_by_name[source_name]
            del self._sources_by_type[source.get_source_type()]
            logger.info(f"Removed KM source: {source_name}")
            return True
        return False
