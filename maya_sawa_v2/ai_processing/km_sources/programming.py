"""
程式設計知識庫源 - 整合paprika的source邏輯
專門處理程式設計相關問題，從paprika API獲取真實資料
"""

import logging
import asyncio
import re
import json
import math
import os
from typing import Dict, Any, List, Tuple, Optional
import psycopg
from .base import BaseKMSource, KMQuery, KMResult

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)


class ProgrammingKMSource(BaseKMSource):
    """程式設計知識庫源 - 整合所有程式設計相關資料"""

    def __init__(self, config: Dict[str, Any] = None):
        super().__init__("programming_km", config)

        # Paprika API 配置
        self.paprika_api_url = self.config.get('paprika_api_url', 'https://peoplesystem.tatdvsonorth.com/paprika/articles')
        self.cache_timeout = self.config.get('cache_timeout', 3600)  # 快取1小時
        self._articles_cache = None
        self._cache_timestamp = 0

        # 移除硬編碼關鍵詞 - 讓AI處理相關性判斷

    async def _fetch_articles_from_paprika(self) -> List[Dict[str, Any]]:
        """從paprika API獲取文章資料"""
        if not httpx:
            logger.error("httpx 未安裝，無法獲取paprika文章")
            return []

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.paprika_api_url)
                response.raise_for_status()
                data = response.json()

                if not data.get("success"):
                    logger.error("Paprika API 返回錯誤")
                    return []

                articles = data.get("data", [])
                logger.info("從paprika API獲取了 %d 篇文章", len(articles))
                return articles

        except Exception as e:
            logger.error("獲取paprika文章時發生錯誤: %s", str(e))
            return []

    def _get_cached_articles(self) -> List[Dict[str, Any]]:
        """獲取快取的文章資料"""
        import time
        current_time = time.time()

        # 如果快取過期或不存在，重新獲取
        if (self._articles_cache is None or
            current_time - self._cache_timestamp > self.cache_timeout):

            logger.info("開始從 Paprika API 獲取文章...")
            try:
                # 優先使用當前執行緒的 running loop 檢測
                try:
                    _ = asyncio.get_running_loop()
                    # 有 running loop：改用執行緒中執行 asyncio.run，避免 RuntimeError
                    import concurrent.futures
                    logger.info("使用 ThreadPoolExecutor 執行異步請求...")
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(lambda: asyncio.run(self._fetch_articles_from_paprika()))
                        # 添加超時處理
                        self._articles_cache = future.result(timeout=10)  # 10秒超時
                except RuntimeError:
                    # 無 running loop：可直接 asyncio.run
                    logger.info("直接使用 asyncio.run...")
                    self._articles_cache = asyncio.run(self._fetch_articles_from_paprika())
                except concurrent.futures.TimeoutError:
                    logger.warning("Paprika API 請求超時，使用空快取")
                    self._articles_cache = []

                self._cache_timestamp = current_time
                logger.info(f"成功獲取 {len(self._articles_cache)} 篇文章")

            except Exception as e:
                # 最後回退：手動建立事件迴圈
                logger.warning(f"主要獲取方式失敗，嘗試回退方式: {str(e)}")
                try:
                    loop = asyncio.new_event_loop()
                    try:
                        asyncio.set_event_loop(loop)
                        self._articles_cache = loop.run_until_complete(self._fetch_articles_from_paprika())
                    finally:
                        loop.close()
                    self._cache_timestamp = current_time
                except Exception as e2:
                    logger.error("獲取文章快取失敗: %s / %s", str(e), str(e2))
                    if self._articles_cache is None:
                        self._articles_cache = []

        return self._articles_cache or []

    def get_priority(self) -> int:
        """程式設計知識庫優先級 - 高優先級"""
        return 10

    def is_suitable_for(self, query: KMQuery) -> bool:
        """簡單判斷：如果filter已經識別為programming_km，就處理"""
        # 信任filter鏈的判斷 - 如果調用至此，說明filter已經判斷這是程式設計問題
        return (query.domain == 'programming' or
                'programming_km' in str(query.metadata) or
                query.metadata.get('km_source') == 'programming_km')

    def search(self, query: KMQuery) -> List[KMResult]:
        """搜索程式設計知識庫，支援中英文與回退策略，並回傳引用資訊"""
        results: List[KMResult] = []

        try:
            # 0) 若資料庫存在缺少 embedding 的文章，先嘗試自動補齊（僅處理 content 不為空者）
            try:
                self._backfill_missing_embeddings(limit=int(os.getenv('EMBED_BACKFILL_LIMIT', '200')),
                                                  batch_size=int(os.getenv('EMBED_BACKFILL_BATCH', '50')))
            except Exception as _e:
                logger.warning("自動補齊 embedding 失敗或已略過: %s", str(_e))

            # 1) 先嘗試直接用資料庫的語義/全文進行檢索
            all_articles: List[Dict[str, Any]] = []

            # 2) 優先使用向量相似度（若可計算查詢向量）與 trigram 全文檢索（pg_trgm）
            query_vec = self._compute_query_embedding_safe(query.query)

            # 3) 嘗試從資料庫檢索（過濾測試文章）
            if query_vec is not None:
                db_semantic = self._search_db_by_embedding(query_vec, k=8, threshold=0.0)
            else:
                db_semantic = []

            db_trgm = self._search_db_by_trigram(query.query or "", k=12, min_sim=0.1)

            # 合併候選（以 file_path 為 key 去重），並保留各自分數
            merged: Dict[str, Dict[str, Any]] = {}
            for art in db_semantic:
                key = art.get('file_path') or f"id:{art.get('id')}"
                merged[key] = {**art, 'emb_score': float(art.get('_match_score') or 0.0), 'text_score': 0.0}
            for art in db_trgm:
                key = art.get('file_path') or f"id:{art.get('id')}"
                existing = merged.get(key, {**art, 'emb_score': 0.0})
                existing.update(art)
                existing['text_score'] = float(art.get('_text_score') or 0.0)
                merged[key] = existing

            merged_list = list(merged.values())
            all_articles = self._filter_test_articles(merged_list)
            logger.info(f"DB 候選文章：semantic={len(db_semantic)}，trigram={len(db_trgm)}，合併後={len(all_articles)}")

            # 如果資料庫沒有足夠的文章，回退到 Paprika API
            if len(all_articles) < 3:
                paprika_articles = self._get_cached_articles()
                paprika_filtered = self._filter_test_articles(paprika_articles)
                logger.info(f"從 Paprika API 檢索到 {len(paprika_articles)} 篇文章，過濾後剩 {len(paprika_filtered)} 篇")
                # 合併結果，優先使用資料庫的結果
                all_articles.extend(paprika_filtered)
                # 去重（基於 file_path）
                seen_paths = set()
                unique_articles = []
                for article in all_articles:
                    file_path = article.get('file_path', '')
                    if file_path and file_path not in seen_paths:
                        seen_paths.add(file_path)
                        unique_articles.append(article)
                all_articles = unique_articles

            # 如果還是沒有文章，使用原始的 Paprika 結果（但過濾測試）
            if not all_articles:
                all_articles = self._filter_test_articles(self._get_cached_articles())

            # 4) 萃取查詢關鍵字（支援中文句子中夾英數，如 Java, Python, .NET, C#）
            query_text = (query.query or '').lower()
            alpha_num_terms = re.findall(r"[a-z0-9\+\#\.\-]+", query_text)
            split_terms = [w.strip() for w in query_text.split() if len(w.strip()) > 1]
            query_terms = list({t for t in (alpha_num_terms + split_terms) if t})

            # 5) 構建相似度/關聯度分數
            #    優先使用混合分數：text(0.6) + embedding(0.4)；若皆無則關鍵詞匹配回退
            scored: List[Tuple[Dict[str, Any], float]] = []
            for article in all_articles:
                content_l = (article.get('content') or '').lower()
                path_l = (article.get('file_path') or '').lower()

                sim_score: float = 0.0
                matched_terms: List[str] = []

                # 先取混合分數（若存在）
                text_score = float(article.get('text_score') or 0.0)
                emb_score = float(article.get('emb_score') or 0.0)
                if text_score > 0.0 or emb_score > 0.0:
                    sim_score = 0.6 * text_score + 0.4 * emb_score
                else:
                    # 關鍵詞匹配作為回退
                    term_score = 0
                    for t in query_terms:
                        if t and (t in content_l or t in path_l):
                            term_score += 1
                            matched_terms.append(t)
                    sim_score = float(term_score)

                article['_match_score'] = sim_score
                article['_matched_terms'] = matched_terms
                scored.append((article, sim_score))

            # 6) 取得相關文章（若無匹配，回退取前3篇以確保有引用輸出）
            scored.sort(key=lambda x: x[1], reverse=True)
            if scored and scored[0][1] > 0:
                relevant_articles = [a for a, s in scored if s > 0][:5]
                fallback_used = False
            else:
                # 回退策略：若 DB 取不到或無匹配，改用 Paprika API 快取
                paprika_articles = self._get_cached_articles()
                if paprika_articles:
                    # 簡單取前三篇保證有引用
                    relevant_articles = paprika_articles[:3]
                    fallback_used = True
                else:
                    relevant_articles = []
                    fallback_used = True

            # 6) 組裝 KMResult
            for article in relevant_articles:
                confidence = 0.4 if fallback_used else 0.8
                relevance_score = float(article.get('_match_score', 0))
                # 組裝工作站可瀏覽的來源連結
                file_path = article.get('file_path') or ''
                work_url = f"https://peoplesystem.tatdvsonorth.com/work/{file_path}" if file_path else self.paprika_api_url

                results.append(KMResult(
                    content=article.get('content', ''),
                    source=f"paprika_{article.get('id', 'unknown')}",
                    confidence=confidence,
                    relevance_score=relevance_score,
                    metadata={
                        'article_id': article.get('id'),
                        'file_path': file_path,
                        'file_date': article.get('file_date'),
                        'source_type': 'paprika_api',
                        'title': self._extract_title_from_content(article.get('content', '')),
                        'source_url': work_url,
                        'provider': 'Paprika',
                        'matched_terms': article.get('_matched_terms', []),
                        'fallback_used': fallback_used,
                        'similarity': relevance_score,
                        'embedding_model': os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small') if query_vec is not None else None
                    }
                ))

            logger.info("從 paprika API 產生 %d 筆引用（fallback=%s）", len(results), fallback_used)

        except Exception as e:
            logger.error("搜索paprika文章時發生錯誤: %s", str(e))
            results = []

        return results

    # ========== Embedding helpers ==========
    def _backfill_missing_embeddings(self, limit: int = 200, batch_size: int = 50) -> None:
        """為 articles 表補齊缺少的 embedding。若無需要則不動作。

        僅處理 content 不為空且 embedding 為 NULL 的文章；若沒有 OpenAI 金鑰或資料庫連線則略過。
        """
        conn_str = os.getenv('POSTGRES_CONNECTION_STRING') or os.getenv('DATABASE_URL')
        if not conn_str:
            # 試著組裝拆分環境變數
            db_host = os.getenv('DB_HOST')
            db_port = os.getenv('DB_PORT')
            db_name = os.getenv('DB_DATABASE')
            db_user = os.getenv('DB_USERNAME')
            db_pass = os.getenv('DB_PASSWORD')
            db_sslmode = os.getenv('DB_SSLMODE')
            if all([db_host, db_port, db_name, db_user, db_pass]):
                conn_str = f"postgres://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
                if db_sslmode:
                    conn_str = f"{conn_str}?sslmode={db_sslmode}"
        if not conn_str:
            return  # 無法連線資料庫則略過

        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return  # 沒有金鑰則略過

        try:
            import psycopg
        except Exception:
            return
        try:
            from openai import OpenAI
        except Exception:
            return

        # 抓取需要補齊的文章
        rows: List[Tuple[Any, Any, Any]] = []
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, file_path, content
                    FROM articles
                    WHERE embedding IS NULL
                      AND content IS NOT NULL AND length(content) > 0
                    ORDER BY file_date DESC
                    LIMIT %s
                    """,
                    (limit,)
                )
                rows = cur.fetchall()

        if not rows:
            return  # 無待處理

        client = OpenAI(api_key=api_key)

        processed = 0
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                for i in range(0, len(rows), batch_size):
                    batch = rows[i:i + batch_size]
                    inputs = [r[2] for r in batch if r[2]]
                    if not inputs:
                        continue
                    try:
                        resp = client.embeddings.create(model=os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small'),
                                                        input=inputs)
                    except Exception as e:
                        logger.warning("產生 embedding 失敗，停止自動補齊: %s", str(e))
                        return

                    # 寫回資料庫
                    idx = 0
                    for row in batch:
                        art_id = row[0]
                        content_val = row[2]
                        if not content_val:
                            continue
                        vec = resp.data[idx].embedding
                        idx += 1
                        emb_str = '[' + ','.join(map(str, vec)) + ']'
                        cur.execute(
                            "UPDATE articles SET embedding = %s::vector, updated_at = NOW() WHERE id = %s",
                            (emb_str, art_id)
                        )
                        processed += 1
                    conn.commit()
        logger.info("自動補齊 embedding 完成，共更新 %d 筆", processed)

    def _compute_query_embedding_safe(self, text: str) -> Optional[List[float]]:
        """嘗試用 OpenAI 產生查詢向量，失敗則回傳 None。"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                return None
            model = os.getenv('OPENAI_EMBEDDING_MODEL', 'text-embedding-3-small')
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            resp = client.embeddings.create(model=model, input=text or "")
            vec = resp.data[0].embedding
            if isinstance(vec, list) and vec:
                return [float(x) for x in vec]
            return None
        except Exception:
            return None

    def _parse_embedding(self, emb_field: Any) -> Optional[List[float]]:
        """解析 paprika 回傳的 embedding 欄位，支援字串或陣列。"""
        try:
            if emb_field is None:
                return None
            if isinstance(emb_field, list):
                return [float(x) for x in emb_field]
            if isinstance(emb_field, str):
                # 移除空白並解析 JSON 陣列字串
                s = emb_field.strip()
                return [float(x) for x in json.loads(s)]
            return None
        except Exception:
            return None

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """計算餘弦相似度，長度不等時以最短長度對齊。"""
        n = min(len(v1), len(v2))
        if n == 0:
            return 0.0
        dot = 0.0
        norm1 = 0.0
        norm2 = 0.0
        for i in range(n):
            a = float(v1[i])
            b = float(v2[i])
            dot += a * b
            norm1 += a * a
            norm2 += b * b
        if norm1 == 0.0 or norm2 == 0.0:
            return 0.0
        return dot / (math.sqrt(norm1) * math.sqrt(norm2))

    # ========== Database helpers ==========
    def _search_db_by_embedding(self, query_vec: List[float], k: int = 5, threshold: float = 0.0) -> List[Dict[str, Any]]:
        """用 PostgreSQL pgvector 做語義檢索。"""
        conn_str = os.getenv('POSTGRES_CONNECTION_STRING') or os.getenv('DATABASE_URL')
        if not conn_str:
            # 允許以拆分的 DB_* 變數組裝連線字串
            db_host = os.getenv('DB_HOST')
            db_port = os.getenv('DB_PORT')
            db_name = os.getenv('DB_DATABASE')
            db_user = os.getenv('DB_USERNAME')
            db_pass = os.getenv('DB_PASSWORD')
            db_sslmode = os.getenv('DB_SSLMODE')
            if all([db_host, db_port, db_name, db_user, db_pass]):
                conn_str = f"postgres://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
                if db_sslmode:
                    conn_str = f"{conn_str}?sslmode={db_sslmode}"
            else:
                return []
        embedding_str = '[' + ','.join(map(str, query_vec)) + ']'
        rows: List[Dict[str, Any]] = []
        try:
            with psycopg.connect(conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT
                            id,
                            file_path,
                            content,
                            file_date,
                            1 - (embedding <=> %s::vector) AS similarity
                        FROM articles
                        WHERE 1 - (embedding <=> %s::vector) > %s
                        AND file_path NOT LIKE 'test/%%'
                        AND file_path NOT LIKE '%%test%%'
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """,
                        (embedding_str, embedding_str, threshold, embedding_str, k)
                    )
                    for r in cur.fetchall():
                        rows.append({
                            'id': r[0],
                            'file_path': r[1],
                            'content': r[2],
                            'file_date': r[3].isoformat() if r[3] else None,
                            '_match_score': float(r[4] or 0.0),
                            '_matched_terms': []
                        })
        except Exception as e:
            logger.error("DB 向量檢索失敗: %s", str(e))
            return []
        return rows

    def _search_db_by_trigram(self, query_text: str, k: int = 10, min_sim: float = 0.1) -> List[Dict[str, Any]]:
        """用 pg_trgm 對 content 做全文近似檢索，利用 GIN(trgm) 索引。"""
        if not query_text:
            return []
        conn_str = os.getenv('POSTGRES_CONNECTION_STRING') or os.getenv('DATABASE_URL')
        if not conn_str:
            db_host = os.getenv('DB_HOST')
            db_port = os.getenv('DB_PORT')
            db_name = os.getenv('DB_DATABASE')
            db_user = os.getenv('DB_USERNAME')
            db_pass = os.getenv('DB_PASSWORD')
            db_sslmode = os.getenv('DB_SSLMODE')
            if all([db_host, db_port, db_name, db_user, db_pass]):
                conn_str = f"postgres://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
                if db_sslmode:
                    conn_str = f"{conn_str}?sslmode={db_sslmode}"
            else:
                return []
        rows: List[Dict[str, Any]] = []
        try:
            # 使用獨立的連線避免 transaction 衝突
            with psycopg.connect(conn_str, autocommit=True) as conn:
                with conn.cursor() as cur:
                    # 設定本連線的 trigram 門檻，讓 % 運算子使用指定 min_sim
                    try:
                        cur.execute("SELECT set_limit(%s)", (float(min_sim),))
                    except Exception:
                        pass
                    cur.execute(
                        """
                        SELECT
                            id,
                            file_path,
                            content,
                            file_date,
                            similarity(content, %s) AS sim
                        FROM articles
                        WHERE content %% %s
                        AND file_path NOT LIKE 'test/%%'
                        AND file_path NOT LIKE '%%test%%'
                        ORDER BY sim DESC
                        LIMIT %s
                        """,
                        (query_text, query_text, k)
                    )
                    for r in cur.fetchall():
                        sim_val = float(r[4] or 0.0)
                        if sim_val < min_sim:
                            continue
                        rows.append({
                            'id': r[0],
                            'file_path': r[1],
                            'content': r[2],
                            'file_date': r[3].isoformat() if r[3] else None,
                            '_text_score': sim_val,
                        })
        except Exception as e:
            logger.error("DB trigram 檢索失敗: %s", str(e))
            return []
        return rows

    def _filter_test_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """過濾掉測試文章，只保留正式技術文檔"""
        filtered = []
        for article in articles:
            file_path = article.get('file_path', '')
            # 排除測試相關的路徑
            if (not file_path.startswith('test/') and
                'test' not in file_path.lower() and
                not file_path.endswith('test.md') and
                not file_path.endswith('test.txt')):
                filtered.append(article)
        return filtered

    def _extract_title_from_content(self, content: str) -> str:
        """從內容中提取標題"""
        lines = content.split('\n')
        for line in lines[:5]:  # 檢查前5行
            line = line.strip()
            if line and len(line) < 100:  # 標題通常比較短
                return line
        return "程式設計文檔"


