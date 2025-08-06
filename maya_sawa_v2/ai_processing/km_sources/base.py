"""
知识库源基类 - 独立的基础模块
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class KMQuery:
    """知识库查询请求"""
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
    """知识库查询结果"""
    content: str
    source: str
    confidence: float
    relevance_score: float
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseKMSource(ABC):
    """知识库源基类"""

    def __init__(self, name: str, config: Dict[str, Any] = None):
        self.name = name
        self.config = config or {}

    @abstractmethod
    def search(self, query: KMQuery) -> List[KMResult]:
        """搜索知识库"""
        pass

    @abstractmethod
    def is_suitable_for(self, query: KMQuery) -> bool:
        """判断是否适合处理此查询"""
        pass

    def get_priority(self) -> int:
        """获取优先级，数字越小优先级越高"""
        return 100

    def get_source_type(self) -> str:
        """获取源类型"""
        return self.__class__.__name__.lower()
