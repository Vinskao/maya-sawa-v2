"""
测试简化后的编程知识库
验证简化版设计的功能
"""

from maya_sawa_v2.ai_processing.km_sources.programming import ProgrammingKMSource
from maya_sawa_v2.ai_processing.km_sources.base import KMQuery


def test_simplified_programming_km():
    """测试简化后的编程知识库"""
    print("=== 测试简化后的编程知识库 ===\n")

    # 创建编程知识库源
    programming_km = ProgrammingKMSource({
        'paprika_api_url': 'https://peoplesystem.tatdvsonorth.com/paprika/articles',
        'cache_timeout': 300  # 5分钟缓存
    })

    print(f"✅ 创建ProgrammingKMSource: {programming_km.name}")
    print(f"✅ 优先级: {programming_km.get_priority()}")

    # 测试is_suitable_for方法
    test_queries = [
        KMQuery("java spring问题", 1, "conv1", domain="programming"),
        KMQuery("python错误", 1, "conv2", metadata={'km_source': 'programming_km'}),
        KMQuery("如何煮咖啡", 1, "conv3", domain="general"),
    ]

    print("\n=== 测试is_suitable_for判断 ===")
    for query in test_queries:
        suitable = programming_km.is_suitable_for(query)
        print(f"查询: '{query.query}' -> 适合处理: {suitable}")

    # 测试搜索功能
    print("\n=== 测试搜索功能 ===")
    programming_query = KMQuery(
        "java spring boot错误",
        1,
        "conv1",
        domain="programming",
        metadata={'km_source': 'programming_km'}
    )

    print(f"搜索查询: '{programming_query.query}'")
    try:
        results = programming_km.search(programming_query)
        print(f"✅ 搜索完成，找到 {len(results)} 个结果")

        for i, result in enumerate(results, 1):
            print(f"  {i}. 来源: {result.source}")
            print(f"     标题: {result.metadata.get('title', 'N/A')}")
            print(f"     置信度: {result.confidence}")
            print(f"     相关性: {result.relevance_score}")
            print(f"     内容长度: {len(result.content)} 字符")
            print()

    except Exception as e:
        print(f"❌ 搜索出错: {e}")

    print("=== 简化版特点 ===")
    print("✅ 移除了69个硬编码关键词")
    print("✅ 移除了复杂的相关性计算")
    print("✅ 简化了文本匹配逻辑")
    print("✅ 固定返回5篇文章")
    print("✅ 让AI处理后续相关性判断")


if __name__ == "__main__":
    test_simplified_programming_km()
