"""
编程知识库源 - 整合paprika的source逻辑
专门处理编程相关问题，从paprika API获取真实数据
"""

import logging
import asyncio
from typing import Dict, Any, List
from .base import BaseKMSource, KMQuery, KMResult

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)


class ProgrammingKMSource(BaseKMSource):
    """编程知识库源 - 整合所有编程相关数据"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("programming_km", config)

        # Paprika API 配置
        self.paprika_api_url = self.config.get('paprika_api_url', 'https://peoplesystem.tatdvsonorth.com/paprika/articles')
        self.cache_timeout = self.config.get('cache_timeout', 3600)  # 缓存1小时
        self._articles_cache = None
        self._cache_timestamp = 0

        # 移除硬编码关键词 - 让AI处理相关性判断

    async def _fetch_articles_from_paprika(self) -> List[Dict[str, Any]]:
        """从paprika API获取文章数据"""
        if not httpx:
            logger.error("httpx 未安装，无法获取paprika文章")
            return []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.paprika_api_url)
                response.raise_for_status()
                data = response.json()

                if not data.get("success"):
                    logger.error("Paprika API 返回错误")
                    return []

                articles = data.get("data", [])
                logger.info("从paprika API获取了 %d 篇文章", len(articles))
                return articles

        except Exception as e:
            logger.error("获取paprika文章时发生错误: %s", str(e))
            return []

    def _get_cached_articles(self) -> List[Dict[str, Any]]:
        """获取缓存的文章数据"""
        import time
        current_time = time.time()

        # 如果缓存过期或不存在，重新获取
        if (self._articles_cache is None or
            current_time - self._cache_timestamp > self.cache_timeout):

            try:
                # 使用同步方式运行异步方法
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # 如果在异步上下文中，创建新的事件循环
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, self._fetch_articles_from_paprika())
                        self._articles_cache = future.result()
                else:
                    self._articles_cache = asyncio.run(self._fetch_articles_from_paprika())

                self._cache_timestamp = current_time

            except Exception as e:
                logger.error("获取文章缓存失败: %s", str(e))
                if self._articles_cache is None:
                    self._articles_cache = []

        return self._articles_cache or []

    def get_priority(self) -> int:
        """编程知识库优先级 - 高优先级"""
        return 10

    def is_suitable_for(self, query: KMQuery) -> bool:
        """简单判断：如果filter已经识别为programming_km，就处理"""
        # 信任filter链的判断 - 如果调用到这里，说明filter已经判断这是编程问题
        return (query.domain == 'programming' or
                'programming_km' in str(query.metadata) or
                query.metadata.get('km_source') == 'programming_km')

    def search(self, query: KMQuery) -> List[KMResult]:
        """搜索编程知识库 - 简化版，让AI处理相关性"""
        results = []

        try:
            # 1. 获取所有文章
            all_articles = self._get_cached_articles()

            # 2. 简单文本匹配 - 让AI处理相关性
            query_words = [word.strip() for word in query.query.lower().split() if len(word.strip()) > 2]
            relevant_articles = []

            for article in all_articles:
                content = article.get('content', '').lower()

                # 简单检查：查询词汇是否在文章中出现
                if any(word in content for word in query_words):
                    relevant_articles.append(article)

                # 限制搜索范围，提高效率
                if len(relevant_articles) >= 10:
                    break

            # 3. 转换为KMResult格式，返回前5篇
            for article in relevant_articles[:5]:
                results.append(KMResult(
                    content=article.get('content', ''),
                    source=f"paprika_{article.get('id', 'unknown')}",
                    confidence=0.8,  # 固定置信度
                    relevance_score=1.0,  # 让后续AI处理相关性
                    metadata={
                        'article_id': article.get('id'),
                        'file_path': article.get('file_path'),
                        'file_date': article.get('file_date'),
                        'source_type': 'paprika_api',
                        'title': self._extract_title_from_content(article.get('content', ''))
                    }
                ))

            logger.info("从paprika API找到 %d 篇相关文章，返回前5篇", len(relevant_articles))

        except Exception as e:
            logger.error("搜索paprika文章时发生错误: %s", str(e))
            # API失败时返回空结果
            results = []

        return results

    def _extract_title_from_content(self, content: str) -> str:
        """从内容中提取标题"""
        lines = content.split('\n')
        for line in lines[:5]:  # 检查前5行
            line = line.strip()
            if line and len(line) < 100:  # 标题通常比较短
                return line
        return "编程文档"


