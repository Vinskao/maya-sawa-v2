from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class FilterContext:
    """過濾器上下文"""
    message: str
    user_id: int
    conversation_id: str
    conversation_type: str = 'general'
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class FilterResult:
    """過濾器結果"""
    should_continue: bool = True
    conversation_type: Optional[str] = None
    confidence: float = 0.0
    reason: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseFilter(ABC):
    """基礎過濾器類別"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.name = self.__class__.__name__

    @abstractmethod
    def process(self, context: FilterContext) -> FilterResult:
        """處理過濾邏輯"""
        pass

    def should_execute(self, context: FilterContext) -> bool:
        """判斷是否應該執行此過濾器"""
        return True

    def get_priority(self) -> int:
        """獲取過濾器優先級，數字越小優先級越高"""
        return 100

    def __str__(self):
        return f"{self.name}(priority={self.get_priority()})"

    def __repr__(self):
        return self.__str__()
