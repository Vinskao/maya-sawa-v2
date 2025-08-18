from typing import Dict, Any
from ..base import BaseFilter, FilterContext, FilterResult


class ExampleNewFilter(BaseFilter):
    """範例新過濾器 - 展示如何擴展"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        # 從配置中讀取參數
        self.custom_keywords = self.config.get('custom_keywords', [])
        self.threshold = self.config.get('threshold', 0.5)

    def get_priority(self) -> int:
        """設置優先級 - 數字越小優先級越高"""
        return 15  # 在keyword_filter(10)之後，intent_filter(20)之前

    def process(self, context: FilterContext) -> FilterResult:
        """處理邏輯"""
        message_lower = context.message.lower()

        # 自定義檢測邏輯
        matches = [kw for kw in self.custom_keywords if kw.lower() in message_lower]

        if matches and len(matches) / len(self.custom_keywords) >= self.threshold:
            return FilterResult(
                should_continue=False,  # 停止鏈
                conversation_type='custom_type',
                confidence=0.8,
                reason=f"檢測到自定義關鍵詞: {', '.join(matches)}",
                metadata={'matched_keywords': matches}
            )

        return FilterResult(
            should_continue=True,
            confidence=0.0,
            reason="未檢測到自定義模式"
        )
