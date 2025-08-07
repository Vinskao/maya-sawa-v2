import logging
from typing import List, Dict, Any, Optional
from .base import BaseFilter, FilterContext, FilterResult

logger = logging.getLogger(__name__)


class FilterChainManager:
    """過濾器鏈管理器"""

    def __init__(self):
        self.filters: List[BaseFilter] = []
        self._filters_by_name: Dict[str, BaseFilter] = {}

    def add_filter(self, filter_instance: BaseFilter) -> None:
        """添加過濾器到鏈中"""
        self.filters.append(filter_instance)
        self._filters_by_name[filter_instance.name] = filter_instance
        # 按優先級排序
        self.filters.sort(key=lambda f: f.get_priority())
        logger.info(f"Added filter: {filter_instance}")

    def remove_filter(self, filter_name: str) -> bool:
        """移除過濾器"""
        if filter_name in self._filters_by_name:
            filter_instance = self._filters_by_name[filter_name]
            self.filters.remove(filter_instance)
            del self._filters_by_name[filter_name]
            logger.info(f"Removed filter: {filter_name}")
            return True
        return False

    def get_filter(self, filter_name: str) -> Optional[BaseFilter]:
        """獲取指定過濾器"""
        return self._filters_by_name.get(filter_name)

    def list_filters(self) -> List[str]:
        """列出所有過濾器名稱"""
        return list(self._filters_by_name.keys())

    def process(self, context: FilterContext) -> FilterResult:
        """執行過濾器鏈"""
        logger.info(f"Starting filter chain processing for message: {context.message[:50]}...")

        # 創建初始結果
        result = FilterResult()

        # 按優先級執行過濾器
        for filter_instance in self.filters:
            if not filter_instance.should_execute(context):
                logger.debug(f"Skipping filter {filter_instance.name} - should_execute returned False")
                continue

            try:
                logger.debug(f"Executing filter: {filter_instance.name}")
                filter_result = filter_instance.process(context)

                # 更新結果 - 只有當新結果的置信度更高時才覆蓋
                if filter_result.conversation_type:
                    # 如果是編程類型，優先保留
                    if filter_result.conversation_type == 'programming':
                        result.conversation_type = filter_result.conversation_type
                        result.confidence = filter_result.confidence
                        result.reason = filter_result.reason
                    # 否則只有當新結果的置信度更高時才覆蓋
                    elif not result.conversation_type or filter_result.confidence > result.confidence:
                        result.conversation_type = filter_result.conversation_type
                        result.confidence = filter_result.confidence
                        result.reason = filter_result.reason

                if filter_result.reason:
                    result.reason = filter_result.reason

                # 合併元資料
                if filter_result.metadata:
                    result.metadata.update(filter_result.metadata)

                # 檢查是否應該停止
                if not filter_result.should_continue:
                    logger.info(f"Filter {filter_instance.name} stopped the chain")
                    break

            except Exception as e:
                logger.error(f"Error in filter {filter_instance.name}: {str(e)}")
                # 繼續執行下一個過濾器
                continue

        logger.info(f"Filter chain completed. Final type: {result.conversation_type}, confidence: {result.confidence}")
        return result

    def reset(self) -> None:
        """重置過濾器鏈"""
        self.filters.clear()
        self._filters_by_name.clear()
        logger.info("Filter chain reset")

    def __len__(self) -> int:
        return len(self.filters)

    def __str__(self) -> str:
        return f"FilterChainManager(filters={len(self.filters)})"
