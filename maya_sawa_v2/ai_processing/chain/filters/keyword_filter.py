import re
from typing import Dict, Any, List
from ..base import BaseFilter, FilterContext, FilterResult


class KeywordFilter(BaseFilter):
    """關鍵字過濾器 - 檢測客服相關關鍵字"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.customer_service_keywords = self.config.get('customer_service_keywords', [
            '客服', '服務', '幫助', '協助', '支援', '問題', '故障', '錯誤', '退款', '退貨',
            '訂單', '付款', '配送', '運費', '保固', '維修', '換貨', '投訴', '建議',
            'customer service', 'help', 'support', 'issue', 'problem', 'refund', 'return',
            'order', 'payment', 'shipping', 'warranty', 'complaint'
        ])
        self.knowledge_keywords = self.config.get('knowledge_keywords', [
            '知識', '資訊', '說明', '介紹', '指南', '教學', '學習', '研究', '分析',
            '知識庫', 'FAQ', '常見問題', '使用說明', '操作指南',
            'knowledge', 'information', 'guide', 'tutorial', 'manual', 'faq'
        ])

    def get_priority(self) -> int:
        """高優先級 - 關鍵字檢測應該優先執行"""
        return 10

    def process(self, context: FilterContext) -> FilterResult:
        """處理關鍵字檢測"""
        message_lower = context.message.lower()

        # 檢測客服關鍵字
        customer_service_matches = []
        for keyword in self.customer_service_keywords:
            if keyword.lower() in message_lower:
                customer_service_matches.append(keyword)

        # 檢測知識查詢關鍵字
        knowledge_matches = []
        for keyword in self.knowledge_keywords:
            if keyword.lower() in message_lower:
                knowledge_matches.append(keyword)

        # 計算置信度
        total_keywords = len(self.customer_service_keywords) + len(self.knowledge_keywords)
        customer_service_confidence = len(customer_service_matches) / len(self.customer_service_keywords) if self.customer_service_keywords else 0
        knowledge_confidence = len(knowledge_matches) / len(self.knowledge_keywords) if self.knowledge_keywords else 0

                # 決定對話類型和知識庫源
        if customer_service_confidence > 0.3:  # 如果找到超過30%的客服關鍵字
            return FilterResult(
                should_continue=True,
                conversation_type='customer_service',
                confidence=customer_service_confidence,
                reason=f"檢測到客服關鍵字: {', '.join(customer_service_matches)}",
                metadata={
                    'matched_keywords': customer_service_matches,
                    'km_source': 'customer_service_km',  # 指定客服知识库
                    'original_message': context.message  # 保存原始消息
                }
            )
        elif knowledge_confidence > 0.3:  # 如果找到超過30%的知識關鍵字
            # 根据关键词判断使用哪个知识库
            km_source = self._determine_km_source(knowledge_matches, message_lower)

            return FilterResult(
                should_continue=True,
                conversation_type='knowledge_query',
                confidence=knowledge_confidence,
                reason=f"檢測到知識查詢關鍵字: {', '.join(knowledge_matches)}",
                metadata={
                    'matched_keywords': knowledge_matches,
                    'km_source': km_source,
                    'original_message': context.message  # 保存原始消息
                }
            )

        # 沒有明確匹配，繼續下一個過濾器
        return FilterResult(
            should_continue=True,
            confidence=0.0,
            reason="未檢測到明確的關鍵字模式"
        )

    def _determine_km_source(self, knowledge_matches: List[str], message_lower: str) -> str:
        """根據關鍵字判斷使用哪個知識庫源"""
        # 檢查是否包含編程相關關鍵字 - 擴展版
        programming_keywords = [
            # 編程語言
            'java', 'python', 'javascript', 'typescript', 'c++', 'c#', 'php', 'ruby', 'go', 'rust',
            'swift', 'kotlin', 'scala', 'groovy', 'perl', 'bash', 'shell', 'sql', 'html', 'css',
            'r', 'matlab', 'octave', 'fortran', 'cobol', 'pascal', 'basic', 'assembly',

            # 框架和庫
            'spring', 'django', 'flask', 'express', 'react', 'vue', 'angular', 'node.js', 'nodejs',
            'hibernate', 'mybatis', 'jpa', 'jdbc', 'junit', 'maven', 'gradle', 'docker', 'kubernetes',
            'git', 'svn', 'jenkins', 'sonar', 'nexus', 'redis', 'mysql', 'postgresql', 'mongodb',
            'elasticsearch', 'kafka', 'rabbitmq', 'nginx', 'apache', 'tomcat', 'jetty',

            # 編程概念
            'class', 'method', 'function', 'variable', 'object', 'interface', 'inheritance', 'polymorphism',
            'encapsulation', 'abstraction', 'api', 'rest', 'soap', 'microservice', 'monolith', 'architecture',
            'design pattern', 'algorithm', 'data structure', 'database', 'orm', 'mvc', 'mvvm',
            'dependency injection', 'inversion of control', 'solid principles', 'clean code',

            # 開發工具和環境
            'ide', 'eclipse', 'intellij', 'vscode', 'vim', 'emacs', 'debug', 'testing', 'unit test',
            'integration test', 'ci/cd', 'deployment', 'production', 'development', 'staging', 'qa',
            'version control', 'branch', 'merge', 'pull request', 'code review',

            # 中文編程相關詞彙
            '程式', '代碼', '編程', '開發', '軟體', '系統', '應用', '網站', 'app', '應用程式',
            '資料庫', '伺服器', '客戶端', '後端', '前端', '全端', '架構', '設計模式', '演算法',
            '測試', '除錯', '部署', '版本控制', '程式碼', '函數', '類別', '物件', '介面',
            '模組', '套件', '依賴', '建置', '編譯', '執行', '打包', '引入', '匯出',

            # 問題類型
            'error', 'bug', 'issue', 'problem', 'exception', 'stack trace', 'log', 'debug',
            '錯誤', '問題', '異常', '崩潰', '當機', '卡住', '慢', '效能', '記憶體', 'cpu',
            'memory leak', 'deadlock', 'race condition', 'buffer overflow', 'segmentation fault',

            # 編程語法
            'syntax', 'compilation', 'runtime', 'compile', 'build', 'package', 'import', 'export',
            '語法', '編譯', '執行', '建置', '打包', '引入', '匯出', '模組', '套件', '依賴',
        ]

        if any(keyword in message_lower for keyword in programming_keywords):
            return 'programming_km'

        # 檢查是否包含特定領域關鍵字
        domain_keywords = {
            'product_km': ['產品', '功能', '使用', 'product', 'feature', 'usage'],
            'service_km': ['服務', '政策', '流程', 'service', 'policy', 'process'],
            'technical_km': ['技術', '系統', '架構', 'technical', 'system', 'architecture']
        }

        for domain, keywords in domain_keywords.items():
            if any(keyword in message_lower for keyword in keywords):
                return domain

        # 默認使用通用知識庫
        return 'general_km'
