from typing import Dict, Any
from ..base import BaseFilter, FilterContext, FilterResult


class ExampleNewFilter(BaseFilter):
    """示例新过滤器 - 展示如何扩展"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        # 从配置中读取参数
        self.custom_keywords = self.config.get('custom_keywords', [])
        self.threshold = self.config.get('threshold', 0.5)

    def get_priority(self) -> int:
        """设置优先级 - 数字越小优先级越高"""
        return 15  # 在keyword_filter(10)之后，intent_filter(20)之前

    def process(self, context: FilterContext) -> FilterResult:
        """处理逻辑"""
        message_lower = context.message.lower()

        # 自定义检测逻辑
        matches = [kw for kw in self.custom_keywords if kw.lower() in message_lower]

        if matches and len(matches) / len(self.custom_keywords) >= self.threshold:
            return FilterResult(
                should_continue=False,  # 停止链
                conversation_type='custom_type',
                confidence=0.8,
                reason=f"检测到自定义关键词: {', '.join(matches)}",
                metadata={'matched_keywords': matches}
            )

        return FilterResult(
            should_continue=True,
            confidence=0.0,
            reason="未检测到自定义模式"
        )
