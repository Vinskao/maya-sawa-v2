"""
通用知识库源 - 处理一般性问题
"""

from typing import Dict, Any, List
from .base import BaseKMSource, KMQuery, KMResult


class GeneralKMSource(BaseKMSource):
    """通用知识库源"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("general_km", config)

        # 通用关键词
        self.general_keywords = self.config.get('general_keywords', [
            '什麼是', '如何', '怎麼', '說明', '介紹', '指南', '教學', '學習',
            'what is', 'how to', 'guide', 'tutorial', 'manual', 'faq',
            '知識', '資訊', '資料', '問題', '答案', '解決', '幫助',
            'knowledge', 'information', 'help', 'solution', 'answer'
        ])

    def get_priority(self) -> int:
        """通用知识库优先级 - 较低"""
        return 50

    def is_suitable_for(self, query: KMQuery) -> bool:
        """判断是否适合处理通用查询"""
        # 通用知识库作为兜底，总是适合
        return True

    def search(self, query: KMQuery) -> List[KMResult]:
        """搜索通用知识库"""
        # 模拟搜索结果
        results = []

        # 根据查询内容返回相关结果
        query_lower = query.query.lower()

        if '什麼是' in query_lower or 'what is' in query_lower:
            results.append(KMResult(
                content="通用概念解释：\n这里提供各种概念和术语的解释说明",
                source="general_km",
                confidence=0.6,
                relevance_score=0.7,
                metadata={'category': 'concept_explanation'}
            ))
        elif '如何' in query_lower or 'how to' in query_lower:
            results.append(KMResult(
                content="操作指南：\n1. 步骤一\n2. 步骤二\n3. 步骤三",
                source="general_km",
                confidence=0.6,
                relevance_score=0.7,
                metadata={'category': 'how_to'}
            ))
        else:
            results.append(KMResult(
                content="通用知识库内容：\n提供各种常见问题的解答和相关信息",
                source="general_km",
                confidence=0.5,
                relevance_score=0.6,
                metadata={'category': 'general'}
            ))

        return results
