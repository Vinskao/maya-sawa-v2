from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import time


class Command(BaseCommand):
    help = "監控 Django 資料庫連接使用情況"

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='監控間隔（秒），預設為 5 秒'
        )
        parser.add_argument(
            '--count',
            type=int,
            default=10,
            help='監控次數，預設為 10 次'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        count = options['count']

        self.stdout.write(
            self.style.SUCCESS(
                f"開始監控資料庫連接，間隔 {interval} 秒，共 {count} 次\n"
            )
        )

        for i in range(count):
            try:
                # 獲取連接池信息
                db_config = settings.DATABASES['default']
                max_conns = db_config.get('OPTIONS', {}).get('MAX_CONNS', 'Not set')
                conn_max_age = db_config.get('CONN_MAX_AGE', 0)

                # 檢查當前連接狀態
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            count(*) as total_connections,
                            count(*) FILTER (WHERE state = 'active') as active_connections,
                            count(*) FILTER (WHERE state = 'idle') as idle_connections
                        FROM pg_stat_activity
                        WHERE datname = current_database()
                    """)

                    result = cursor.fetchone()
                    total, active, idle = result

                    # 獲取最大連接數
                    cursor.execute("SHOW max_connections;")
                    max_connections = cursor.fetchone()[0]

                    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

                    self.stdout.write(
                        f"[{timestamp}] "
                        f"總連接: {total}/{max_connections} "
                        f"(活躍: {active}, 空閒: {idle}) "
                        f"應用限制: {max_conns} "
                        f"連接存活: {conn_max_age}s"
                    )

                    # 如果連接數接近限制，顯示警告
                    if total > int(max_connections) * 0.8:
                        self.stdout.write(
                            self.style.WARNING(
                                f"⚠️  警告：連接數已達到 {total}/{max_connections} "
                                f"({total/int(max_connections)*100:.1f}%)"
                            )
                        )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"監控時發生錯誤: {e}")
                )

            if i < count - 1:  # 最後一次不需要等待
                time.sleep(interval)

        self.stdout.write(
            self.style.SUCCESS("\n監控完成！")
        )
