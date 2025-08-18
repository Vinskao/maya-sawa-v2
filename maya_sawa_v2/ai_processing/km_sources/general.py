"""
通用知識庫源 - 處理一般性問題
"""

from typing import Dict, Any, List
from .base import BaseKMSource, KMQuery, KMResult


class GeneralKMSource(BaseKMSource):
    """通用知識庫源"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("general_km", config)

        # 通用關鍵詞
        self.general_keywords = self.config.get('general_keywords', [
            '什麼是', '如何', '怎麼', '說明', '介紹', '指南', '教學', '學習',
            'what is', 'how to', 'guide', 'tutorial', 'manual', 'faq',
            '知識', '資訊', '資料', '問題', '答案', '解決', '幫助',
            'knowledge', 'information', 'help', 'solution', 'answer'
        ])

    def get_priority(self) -> int:
        """通用知識庫優先級 - 較低"""
        return 50

    def is_suitable_for(self, query: KMQuery) -> bool:
        """判斷是否適合處理通用查詢"""
        # 通用知識庫作為兜底，總是適合
        return True

    def search(self, query: KMQuery) -> List[KMResult]:
        """搜索通用知識庫"""
        # 模擬搜索結果
        results = []

        # 根據查詢內容返回相關結果
        query_lower = query.query.lower()

        if '什麼是' in query_lower or 'what is' in query_lower:
            results.append(KMResult(
                content="通用概念解釋：\n這裡提供各種概念和術語的解釋說明",
                source="general_km",
                confidence=0.6,
                relevance_score=0.7,
                metadata={'category': 'concept_explanation'}
            ))
        elif '如何' in query_lower or 'how to' in query_lower:
            results.append(KMResult(
                content="操作指南：\n1. 步驟一\n2. 步驟二\n3. 步驟三",
                source="general_km",
                confidence=0.6,
                relevance_score=0.7,
                metadata={'category': 'how_to'}
            ))
        else:
            results.append(KMResult(
                content="通用知識庫內容：\n提供各種常見問題的解答和相關資訊",
                source="general_km",
                confidence=0.5,
                relevance_score=0.6,
                metadata={'category': 'general'}
            ))

        return results
