"""
知識庫源基類 - 獨立的基礎模組
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class KMQuery:
    """知識庫查詢請求"""
    query: str
    user_id: int
    conversation_id: str
    domain: Optional[str] = None
    confidence: float = 0.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class KMResult:
    """知識庫查詢結果"""
    content: str
    source: str
    confidence: float
    relevance_score: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseKMSource(ABC):
    """知識庫源基類"""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}

    @abstractmethod
    def search(self, query: KMQuery) -> List[KMResult]:
        """搜索知識庫"""
        pass

    @abstractmethod
    def is_suitable_for(self, query: KMQuery) -> bool:
        """判斷是否適合處理此查詢"""
        pass

    def get_priority(self) -> int:
        """獲取優先級，數字越小優先級越高"""
        return 100

    def get_source_type(self) -> str:
        """獲取源類型"""
        return self.__class__.__name__.lower()
