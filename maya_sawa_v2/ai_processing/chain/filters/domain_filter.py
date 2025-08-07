from typing import Dict, Any, List
from ..base import BaseFilter, FilterContext, FilterResult


class DomainFilter(BaseFilter):
    """領域過濾器 - 檢測特定業務領域的關鍵詞"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.domain_keywords = self.config.get('domain_keywords', {
            'ecommerce': [
                '商品', '產品', '購買', '購物', '商城', '商店', '價格', '優惠', '折扣',
                '商品', '產品', '購買', '購物', '商城', '商店', '價格', '優惠', '折扣',
                'product', 'purchase', 'shopping', 'store', 'price', 'discount', 'sale'
            ],
            'technical': [
                '技術', '程式', '代碼', '開發', 'API', '資料庫', '伺服器', '網路',
                '技術', '程式', '代碼', '開發', 'API', '資料庫', '伺服器', '網路',
                'technical', 'programming', 'code', 'development', 'api', 'database', 'server'
            ],
            'programming': [
                'java', 'python', 'javascript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'swift',
                '程式語言', '編程語言', '程式設計', '編程', '代碼', '函數', '類別', '物件',
                '變數', '迴圈', '條件', '演算法', '資料結構', '框架', '函式庫', 'API',
                'java', 'python', 'javascript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'swift',
                'programming language', 'coding', 'function', 'class', 'object', 'variable',
                'loop', 'condition', 'algorithm', 'data structure', 'framework', 'library'
            ],
            'financial': [
                '財務', '會計', '稅務', '投資', '理財', '保險', '銀行', '貸款',
                '財務', '會計', '稅務', '投資', '理財', '保險', '銀行', '貸款',
                'financial', 'accounting', 'tax', 'investment', 'insurance', 'bank', 'loan'
            ]
        })

    def get_priority(self) -> int:
        """低優先級 - 在基本意圖檢測之後執行"""
        return 30

    def process(self, context: FilterContext) -> FilterResult:
        """處理領域檢測"""
        message_lower = context.message.lower()

        # 檢測各領域關鍵詞
        domain_matches = {}
        for domain, keywords in self.domain_keywords.items():
            matches = []
            for keyword in keywords:
                if keyword.lower() in message_lower:
                    matches.append(keyword)
            if matches:
                domain_matches[domain] = matches

        # 如果檢測到特定領域，可能影響對話類型
        if domain_matches:
            # 根據領域調整對話類型
            if 'ecommerce' in domain_matches:
                # 電商領域通常與客服相關
                return FilterResult(
                    should_continue=True,
                    conversation_type='customer_service',
                    confidence=0.6,
                    reason=f"檢測到電商領域關鍵詞: {', '.join(domain_matches['ecommerce'])}",
                    metadata={'detected_domains': domain_matches}
                )
            elif 'programming' in domain_matches:
                # 編程領域使用編程知識庫
                return FilterResult(
                    should_continue=True,
                    conversation_type='programming',
                    confidence=0.8,
                    reason=f"檢測到編程領域關鍵詞: {', '.join(domain_matches['programming'])}",
                    metadata={'detected_domains': domain_matches, 'km_source': 'programming_km'}
                )
            elif 'technical' in domain_matches:
                # 技術領域可能是知識查詢
                return FilterResult(
                    should_continue=True,
                    conversation_type='knowledge_query',
                    confidence=0.5,
                    reason=f"檢測到技術領域關鍵詞: {', '.join(domain_matches['technical'])}",
                    metadata={'detected_domains': domain_matches}
                )
            elif 'financial' in domain_matches:
                # 財務領域可能是知識查詢或客服
                return FilterResult(
                    should_continue=True,
                    conversation_type='knowledge_query',
                    confidence=0.4,
                    reason=f"檢測到財務領域關鍵詞: {', '.join(domain_matches['financial'])}",
                    metadata={'detected_domains': domain_matches}
                )

        # 沒有檢測到特定領域，繼續下一個過濾器
        return FilterResult(
            should_continue=True,
            confidence=0.0,
            reason="未檢測到特定業務領域"
        )
