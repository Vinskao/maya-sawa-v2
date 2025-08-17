import os
from typing import List, Tuple

from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    help = "為 articles 表補齊缺少的 embedding（OpenAI）並可選擇建立索引"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--limit", type=int, default=500, help="本次處理的最大文章數量")
        parser.add_argument("--batch-size", type=int, default=50, help="每批送入 OpenAI 的筆數")
        parser.add_argument("--where", type=str, default="", help="額外的 SQL 過濾條件（不含 WHERE）")
        parser.add_argument("--force", action="store_true", help="即使已有 embedding 也重新計算")
        parser.add_argument("--dry-run", action="store_true", help="僅列出將處理的筆數，不實際更新")
        parser.add_argument("--ensure-extension", action="store_true", help="確保安裝 pgvector 擴展")
        parser.add_argument("--create-index", action="store_true", help="為 embedding 建立 ivfflat 索引（若未存在）")

    def handle(self, *args, **options):
        limit: int = options["limit"]
        batch_size: int = options["batch_size"]
        where: str = options["where"].strip()
        force: bool = options["force"]
        dry_run: bool = options["dry_run"]
        ensure_extension: bool = options["ensure_extension"]
        create_index: bool = options["create_index"]

        conn_str = (os.getenv("POSTGRES_CONNECTION_STRING")
                    or os.getenv("DATABASE_URL")
                    or self._build_conn_str_from_split_env())
        if not conn_str:
            self.stderr.write(self.style.ERROR("找不到資料庫連線資訊（DATABASE_URL 或 DB_* 環境變數）。"))
            return

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            self.stderr.write(self.style.ERROR("OPENAI_API_KEY 未設定，無法產生 embedding。"))
            return

        model = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

        try:
            import psycopg
        except Exception as e:  # pragma: no cover
            self.stderr.write(self.style.ERROR(f"未安裝 psycopg：{e}"))
            return

        try:
            from openai import OpenAI
        except Exception as e:  # pragma: no cover
            self.stderr.write(self.style.ERROR(f"未安裝 openai 套件：{e}"))
            return

        self.stdout.write(self.style.NOTICE(f"連線資料庫: {conn_str.split('@')[-1]}"))

        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                if ensure_extension:
                    try:
                        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                        conn.commit()
                        self.stdout.write(self.style.SUCCESS("已確保安裝 pgvector 擴展。"))
                    except Exception as e:
                        self.stderr.write(self.style.WARNING(f"建立擴展失敗（可忽略若已安裝）：{e}"))

                where_parts: List[str] = []
                # 僅在需要補齊時處理：預設只挑選 embedding 為空者
                if not force:
                    where_parts.append("embedding IS NULL")
                # 內容必須存在且不為空字串
                where_parts.append("content IS NOT NULL AND length(content) > 0")
                if where:
                    where_parts.append(f"({where})")
                where_sql = (" WHERE " + " AND ".join(where_parts)) if where_parts else ""

                select_sql = (
                    "SELECT id, file_path, content FROM articles"
                    f"{where_sql} ORDER BY file_date DESC LIMIT %s"
                )
                cur.execute(select_sql, (limit,))
                rows: List[Tuple[int, str, str]] = cur.fetchall()

        count = len(rows)
        if count == 0:
            self.stdout.write(self.style.SUCCESS("沒有需要處理的文章。"))
            return

        self.stdout.write(self.style.NOTICE(f"本次待處理：{count} 篇（batch={batch_size}）"))
        if dry_run:
            return

        client = OpenAI(api_key=api_key)

        processed = 0
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                for i in range(0, count, batch_size):
                    batch = rows[i:i + batch_size]
                    # 僅保留內容不為空的項目（防守式，雖然 SQL 已過濾）
                    batch = [r for r in batch if r[2]]
                    inputs = [c for (_id, _path, c) in batch]
                    try:
                        resp = client.embeddings.create(model=model, input=inputs)
                    except Exception as e:
                        self.stderr.write(self.style.ERROR(f"產生 embedding 失敗：{e}"))
                        return

                    for (row, item) in zip(batch, resp.data):
                        art_id = row[0]
                        vec = item.embedding
                        emb_str = "[" + ",".join(map(str, vec)) + "]"
                        cur.execute(
                            "UPDATE articles SET embedding = %s::vector, updated_at = NOW() WHERE id = %s",
                            (emb_str, art_id),
                        )
                        processed += 1

                    conn.commit()
                    self.stdout.write(self.style.SUCCESS(f"已更新 {processed}/{count}"))

                if create_index:
                    try:
                        cur.execute(
                            "CREATE INDEX IF NOT EXISTS articles_embedding_ivfflat ON articles USING ivfflat (embedding vector_cosine_ops)"
                        )
                        conn.commit()
                        self.stdout.write(self.style.SUCCESS("已建立（或已存在）ivfflat 向量索引。"))
                    except Exception as e:
                        self.stderr.write(self.style.WARNING(f"建立索引失敗（可忽略）：{e}"))

        self.stdout.write(self.style.SUCCESS(f"完成！共更新 {processed} 筆 embedding"))

    def _build_conn_str_from_split_env(self) -> str:
        host = os.getenv("DB_HOST")
        port = os.getenv("DB_PORT")
        name = os.getenv("DB_DATABASE")
        user = os.getenv("DB_USERNAME")
        pwd = os.getenv("DB_PASSWORD")
        sslmode = os.getenv("DB_SSLMODE")
        if not all([host, port, name, user, pwd]):
            return ""
        base = f"postgres://{user}:{pwd}@{host}:{port}/{name}"
        return f"{base}?sslmode={sslmode}" if sslmode else base


