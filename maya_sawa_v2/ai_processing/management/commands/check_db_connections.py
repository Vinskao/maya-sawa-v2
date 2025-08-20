from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import psycopg2


class Command(BaseCommand):
    help = "檢查 PostgreSQL 資料庫連接使用情況"

    def handle(self, *args, **options):
        try:
            # 獲取資料庫配置
            db_config = settings.DATABASES['default']

            # 連接到資料庫
            conn = psycopg2.connect(
                host=db_config['HOST'],
                port=db_config['PORT'],
                database=db_config['NAME'],
                user=db_config['USER'],
                password=db_config['PASSWORD']
            )

            cursor = conn.cursor()

            # 查詢當前連接數
            cursor.execute("""
                SELECT
                    count(*) as total_connections,
                    count(*) FILTER (WHERE state = 'active') as active_connections,
                    count(*) FILTER (WHERE state = 'idle') as idle_connections,
                    count(*) FILTER (WHERE state = 'idle in transaction') as idle_in_transaction
                FROM pg_stat_activity
                WHERE datname = %s
            """, (db_config['NAME'],))

            result = cursor.fetchone()
            total, active, idle, idle_in_transaction = result

            # 獲取最大連接數限制
            max_connections_query = "SHOW max_connections;"
            cursor.execute(max_connections_query)
            max_connections = cursor.fetchone()[0]

            # 獲取應用程式配置的最大連接數
            app_max_conns = db_config.get('OPTIONS', {}).get('MAX_CONNS', 'Not set')

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n=== PostgreSQL 連接狀態 ===\n"
                    f"資料庫: {db_config['NAME']}\n"
                    f"總連接數: {total}\n"
                    f"活躍連接: {active}\n"
                    f"空閒連接: {idle}\n"
                    f"事務中空閒: {idle_in_transaction}\n"
                    f"PostgreSQL 最大連接數: {max_connections}\n"
                    f"應用程式最大連接數: {app_max_conns}\n"
                    f"剩餘可用連接: {int(max_connections) - total}\n"
                )
            )

            # 顯示詳細的連接信息
            cursor.execute("""
                SELECT
                    pid,
                    usename,
                    application_name,
                    client_addr,
                    state,
                    query_start,
                    state_change
                FROM pg_stat_activity
                WHERE datname = %s
                ORDER BY state, query_start DESC
            """, (db_config['NAME'],))

            connections = cursor.fetchall()

            if connections:
                self.stdout.write("\n=== 詳細連接信息 ===")
                for conn_info in connections:
                    pid, user, app, client, state, query_start, state_change = conn_info
                    self.stdout.write(
                        f"PID: {pid}, 用戶: {user}, 應用: {app}, "
                        f"客戶端: {client}, 狀態: {state}"
                    )

            cursor.close()
            conn.close()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"檢查連接時發生錯誤: {e}")
            )
