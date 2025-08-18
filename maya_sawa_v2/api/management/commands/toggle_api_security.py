"""
API安全配置管理命令
用於一鍵啟用或關閉API安全設置
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = '一鍵啟用或關閉API安全設置'

    def add_arguments(self, parser):
        parser.add_argument(
            '--enable',
            action='store_true',
            help='啟用API安全設置（需要認證和CSRF）',
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help='關閉API安全設置（無需認證和CSRF）',
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='顯示當前API安全設置狀態',
        )

    def handle(self, *args, **options):
        # 使用當前工作目錄的 .env，方便在測試中切換目錄
        env_file = os.path.join(os.getcwd(), '.env')

        if not os.path.exists(env_file):
            self.stdout.write(
                self.style.ERROR(f'環境檔案 {env_file} 不存在，請先建立')
            )
            return

        if options['status']:
            self.show_status()
            return

        if options['enable']:
            self.enable_security(env_file)
        elif options['disable']:
            self.disable_security(env_file)
        else:
            self.stdout.write(
                self.style.WARNING('請指定 --enable 或 --disable 參數')
            )

    def enable_security(self, env_file):
        """啟用API安全設置"""
        self.update_env_file(env_file, {
            'API_REQUIRE_AUTHENTICATION': 'True',
            'API_REQUIRE_CSRF': 'True',
            'API_RATE_LIMIT_ENABLED': 'True',
        })
        self.stdout.write(
            self.style.SUCCESS('✅ API安全設置已啟用')
        )
        self.show_status()

    def disable_security(self, env_file):
        """關閉API安全設置"""
        self.update_env_file(env_file, {
            'API_REQUIRE_AUTHENTICATION': 'False',
            'API_REQUIRE_CSRF': 'False',
            'API_RATE_LIMIT_ENABLED': 'False',
        })
        self.stdout.write(
            self.style.SUCCESS('✅ API安全設置已關閉')
        )
        self.show_status()

    def update_env_file(self, env_file, updates):
        """更新環境檔案"""
        # 讀取現有內容
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 更新或添加配置項
        updated_lines = []
        updated_keys = set()

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                updated_lines.append(line)
                continue

            if '=' in line:
                key = line.split('=')[0]
                if key in updates:
                    updated_lines.append(f"{key}={updates[key]}")
                    updated_keys.add(key)
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)

        # 添加新的配置項
        for key, value in updates.items():
            if key not in updated_keys:
                updated_lines.append(f"{key}={value}")

        # 寫回檔案
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(updated_lines) + '\n')

    def show_status(self):
        """顯示當前安全設置狀態"""
        self.stdout.write('\n📊 當前API安全設置狀態：')
        self.stdout.write('─' * 50)

        # 從settings獲取當前值
        auth_required = getattr(settings, 'API_REQUIRE_AUTHENTICATION', False)
        csrf_required = getattr(settings, 'API_REQUIRE_CSRF', False)
        rate_limit_enabled = getattr(settings, 'API_RATE_LIMIT_ENABLED', False)

        self.stdout.write(f"🔐 認證要求: {'✅ 啟用' if auth_required else '❌ 禁用'}")
        self.stdout.write(f"🛡️  CSRF保護: {'✅ 啟用' if csrf_required else '❌ 禁用'}")
        self.stdout.write(f"⚡ 速率限制: {'✅ 啟用' if rate_limit_enabled else '❌ 禁用'}")

        if not auth_required:
            self.stdout.write('\n💡 提示：認證已禁用，API無需Bearer Token即可訪問')
        else:
            self.stdout.write('\n💡 提示：認證已啟用，API需要Bearer Token才能訪問')

        self.stdout.write('─' * 50)
