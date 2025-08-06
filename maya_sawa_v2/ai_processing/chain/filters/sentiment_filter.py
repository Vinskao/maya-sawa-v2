import re
from typing import Dict, Any, List
from ..base import BaseFilter, FilterContext, FilterResult


class SentimentFilter(BaseFilter):
    """情感過濾器 - 檢測用戶情感傾向"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.negative_words = self.config.get('negative_words', [
            '不滿', '生氣', '憤怒', '失望', '沮喪', '煩惱', '困擾', '討厭', '討厭',
            '不滿意', '投訴', '抱怨', '抗議', '抗議', '抗議', '抗議', '抗議',
            'angry', 'frustrated', 'disappointed', 'upset', 'annoyed', 'complaint'
        ])
        self.positive_words = self.config.get('positive_words', [
            '滿意', '開心', '高興', '感謝', '謝謝', '讚', '好', '棒', '優秀',
            '滿意', '開心', '高興', '感謝', '謝謝', '讚', '好', '棒', '優秀',
            'happy', 'satisfied', 'thankful', 'great', 'excellent', 'wonderful'
        ])
        self.urgent_words = self.config.get('urgent_words', [
            '緊急', '急', '快', '立即', '馬上', '現在', '立刻', '趕快',
            '緊急', '急', '快', '立即', '馬上', '現在', '立刻', '趕快',
            'urgent', 'emergency', 'immediate', 'quick', 'fast', 'now'
        ])
    
    def get_priority(self) -> int:
        """最低優先級 - 最後執行，用於調整結果"""
        return 40
    
    def process(self, context: FilterContext) -> FilterResult:
        """處理情感檢測"""
        message_lower = context.message.lower()
        
        # 檢測負面情感
        negative_count = sum(1 for word in self.negative_words if word.lower() in message_lower)
        
        # 檢測正面情感
        positive_count = sum(1 for word in self.positive_words if word.lower() in message_lower)
        
        # 檢測緊急程度
        urgent_count = sum(1 for word in self.urgent_words if word.lower() in message_lower)
        
        # 計算情感分數
        sentiment_score = positive_count - negative_count
        
        # 根據情感調整對話類型
        if negative_count > 0 and urgent_count > 0:
            # 負面情感 + 緊急 = 客服
            return FilterResult(
                should_continue=False,  # 停止鏈，確定為客服
                conversation_type='customer_service',
                confidence=0.8,
                reason=f"檢測到負面情感({negative_count}個詞)和緊急程度({urgent_count}個詞)，建議客服處理",
                metadata={
                    'negative_count': negative_count,
                    'positive_count': positive_count,
                    'urgent_count': urgent_count,
                    'sentiment_score': sentiment_score
                }
            )
        elif negative_count > positive_count:
            # 負面情感為主 = 客服
            return FilterResult(
                should_continue=True,
                conversation_type='customer_service',
                confidence=0.6,
                reason=f"檢測到負面情感({negative_count}個詞)，建議客服處理",
                metadata={
                    'negative_count': negative_count,
                    'positive_count': positive_count,
                    'urgent_count': urgent_count,
                    'sentiment_score': sentiment_score
                }
            )
        elif positive_count > negative_count:
            # 正面情感為主 = 一般對話
            return FilterResult(
                should_continue=True,
                conversation_type='general',
                confidence=0.4,
                reason=f"檢測到正面情感({positive_count}個詞)，建議一般對話",
                metadata={
                    'negative_count': negative_count,
                    'positive_count': positive_count,
                    'urgent_count': urgent_count,
                    'sentiment_score': sentiment_score
                }
            )
        
        # 情感中性，不影響決策
        return FilterResult(
            should_continue=True,
            confidence=0.0,
            reason="情感檢測中性，不影響對話類型決策",
            metadata={
                'negative_count': negative_count,
                'positive_count': positive_count,
                'urgent_count': urgent_count,
                'sentiment_score': sentiment_score
            }
        ) 