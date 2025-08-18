"""
知識庫源管理器 - 負責管理所有知識庫源
"""

import logging
from typing import Dict, List, Optional, Any
from .base import BaseKMSource, KMQuery, KMResult

logger = logging.getLogger(__name__)


class KMSourceManager:
    """知識庫源管理器"""

    def __init__(self):
        self.sources: List[BaseKMSource] = []
        self._sources_by_name: Dict[str, BaseKMSource] = {}
        self._sources_by_type: Dict[str, BaseKMSource] = {}
        self._setup_default_sources()

    def _setup_default_sources(self):
        """設置預設的知識庫源"""
        try:
            # 導入並添加編程知識庫源
            from .programming import ProgrammingKMSource
            programming_source = ProgrammingKMSource()
            self.add_source(programming_source)
            logger.info("已添加編程知識庫源")
        except Exception as e:
            logger.error(f"設置編程知識庫源失敗: {e}")

        try:
            # 導入並添加一般知識庫源
            from .general import GeneralKMSource
            general_source = GeneralKMSource()
            self.add_source(general_source)
            logger.info("已添加一般知識庫源")
        except Exception as e:
            logger.error(f"設置一般知識庫源失敗: {e}")

    def add_source(self, source: BaseKMSource) -> None:
        """添加知識庫源"""
        self.sources.append(source)
        self._sources_by_name[source.name] = source
        self._sources_by_type[source.get_source_type()] = source
        # 按優先級排序
        self.sources.sort(key=lambda s: s.get_priority())
        logger.info(f"Added KM source: {source.name} (type: {source.get_source_type()})")

    def get_source_by_name(self, name: str) -> Optional[BaseKMSource]:
        """根據名稱獲取知識庫源"""
        return self._sources_by_name.get(name)

    def get_source_by_type(self, source_type: str) -> Optional[BaseKMSource]:
        """根據類型獲取知識庫源"""
        return self._sources_by_type.get(source_type)

    def get_suitable_sources(self, query: KMQuery) -> List[BaseKMSource]:
        """獲取適合處理查詢的知識庫源"""
        suitable_sources = []
        for source in self.sources:
            if source.is_suitable_for(query):
                suitable_sources.append(source)
        return suitable_sources

    def search_by_source_name(self, query: KMQuery, source_name: str) -> List[KMResult]:
        """根據源名稱搜索特定知識庫"""
        source = self.get_source_by_name(source_name)
        if source and source.is_suitable_for(query):
            try:
                return source.search(query)
            except Exception as e:
                logger.error(f"Error searching source {source_name}: {e}")
                return []
        return []

    def search_by_source_type(self, query: KMQuery, source_type: str) -> List[KMResult]:
        """根據源類型搜索特定知識庫"""
        source = self.get_source_by_type(source_type)
        if source and source.is_suitable_for(query):
            try:
                return source.search(query)
            except Exception as e:
                logger.error(f"Error searching source type {source_type}: {e}")
                return []
        return []

    def search_all_suitable(self, query: KMQuery) -> List[KMResult]:
        """搜索所有適合的知識庫源"""
        suitable_sources = self.get_suitable_sources(query)
        all_results = []

        for source in suitable_sources:
            try:
                results = source.search(query)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Error searching source {source.name}: {e}")
                continue

        # 按相關性排序
        all_results.sort(key=lambda r: r.relevance_score, reverse=True)
        return all_results

    def list_sources(self) -> List[Dict[str, Any]]:
        """列出所有知識庫源資訊"""
        return [
            {
                'name': source.name,
                'type': source.get_source_type(),
                'priority': source.get_priority()
            }
            for source in self.sources
        ]

    def remove_source(self, source_name: str) -> bool:
        """移除知識庫源"""
        if source_name in self._sources_by_name:
            source = self._sources_by_name[source_name]
            self.sources.remove(source)
            del self._sources_by_name[source_name]
            del self._sources_by_type[source.get_source_type()]
            logger.info(f"Removed KM source: {source_name}")
            return True
        return False
