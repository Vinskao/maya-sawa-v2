import re
from typing import Dict, Any, List
from ..base import BaseFilter, FilterContext, FilterResult


class IntentFilter(BaseFilter):
    """意圖過濾器 - 使用模式匹配檢測用戶意圖"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.intent_patterns = self.config.get('intent_patterns', {
            'customer_service': [
                r'我(有|遇到|發生).*問題',
                r'.*(壞掉|故障|不能用|不能用).*',
                r'我要(退貨|退款|換貨)',
                r'.*(客服|服務|幫助).*',
                r'.*(投訴|建議|意見).*',
                r'訂單.*(問題|錯誤)',
                r'付款.*(失敗|錯誤)',
                r'配送.*(延遲|問題)',
            ],
            'knowledge_query': [
                r'什麼是.*',
                r'如何.*',
                r'怎麼.*',
                r'.*(說明|介紹|指南).*',
                r'.*(知識|資訊|資料).*',
                r'.*(FAQ|常見問題).*',
                r'.*(教學|學習|研究).*',
            ]
        })
    
    def get_priority(self) -> int:
        """中等優先級 - 在關鍵字檢測之後執行"""
        return 20
    
    def process(self, context: FilterContext) -> FilterResult:
        """處理意圖檢測"""
        message = context.message
        
        # 檢測客服意圖
        customer_service_matches = []
        for pattern in self.intent_patterns.get('customer_service', []):
            if re.search(pattern, message, re.IGNORECASE):
                customer_service_matches.append(pattern)
        
        # 檢測知識查詢意圖
        knowledge_matches = []
        for pattern in self.intent_patterns.get('knowledge_query', []):
            if re.search(pattern, message, re.IGNORECASE):
                knowledge_matches.append(pattern)
        
        # 計算置信度
        customer_service_confidence = len(customer_service_matches) / len(self.intent_patterns.get('customer_service', [])) if self.intent_patterns.get('customer_service') else 0
        knowledge_confidence = len(knowledge_matches) / len(self.intent_patterns.get('knowledge_query', [])) if self.intent_patterns.get('knowledge_query') else 0
        
        # 決定對話類型
        if customer_service_confidence > 0.2:  # 如果匹配到超過20%的客服模式
            return FilterResult(
                should_continue=True,
                conversation_type='customer_service',
                confidence=customer_service_confidence,
                reason=f"檢測到客服意圖模式: {len(customer_service_matches)}個匹配",
                metadata={'matched_patterns': customer_service_matches}
            )
        elif knowledge_confidence > 0.2:  # 如果匹配到超過20%的知識查詢模式
            return FilterResult(
                should_continue=True,
                conversation_type='knowledge_query',
                confidence=knowledge_confidence,
                reason=f"檢測到知識查詢意圖模式: {len(knowledge_matches)}個匹配",
                metadata={'matched_patterns': knowledge_matches}
            )
        
        # 沒有明確匹配，繼續下一個過濾器
        return FilterResult(
            should_continue=True,
            confidence=0.0,
            reason="未檢測到明確的意圖模式"
        ) 