"""
API安全配置管理命令
用于一键启用或关闭API安全设置
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = '一键启用或关闭API安全设置'

    def add_arguments(self, parser):
        parser.add_argument(
            '--enable',
            action='store_true',
            help='启用API安全设置（需要认证和CSRF）',
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help='关闭API安全设置（无需认证和CSRF）',
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='显示当前API安全设置状态',
        )

    def handle(self, *args, **options):
        # 使用當前工作目錄的 .env，方便在測試中切換目錄
        env_file = os.path.join(os.getcwd(), '.env')

        if not os.path.exists(env_file):
            self.stdout.write(
                self.style.ERROR(f'环境文件 {env_file} 不存在，请先创建')
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
                self.style.WARNING('请指定 --enable 或 --disable 参数')
            )

    def enable_security(self, env_file):
        """启用API安全设置"""
        self.update_env_file(env_file, {
            'API_REQUIRE_AUTHENTICATION': 'True',
            'API_REQUIRE_CSRF': 'True',
            'API_RATE_LIMIT_ENABLED': 'True',
        })
        self.stdout.write(
            self.style.SUCCESS('✅ API安全设置已启用')
        )
        self.show_status()

    def disable_security(self, env_file):
        """关闭API安全设置"""
        self.update_env_file(env_file, {
            'API_REQUIRE_AUTHENTICATION': 'False',
            'API_REQUIRE_CSRF': 'False',
            'API_RATE_LIMIT_ENABLED': 'False',
        })
        self.stdout.write(
            self.style.SUCCESS('✅ API安全设置已关闭')
        )
        self.show_status()

    def update_env_file(self, env_file, updates):
        """更新环境文件"""
        # 读取现有内容
        with open(env_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # 更新或添加配置项
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

        # 添加新的配置项
        for key, value in updates.items():
            if key not in updated_keys:
                updated_lines.append(f"{key}={value}")

        # 写回文件
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(updated_lines) + '\n')

    def show_status(self):
        """显示当前安全设置状态"""
        self.stdout.write('\n📊 当前API安全设置状态：')
        self.stdout.write('─' * 50)

        # 从settings获取当前值
        auth_required = getattr(settings, 'API_REQUIRE_AUTHENTICATION', False)
        csrf_required = getattr(settings, 'API_REQUIRE_CSRF', False)
        rate_limit_enabled = getattr(settings, 'API_RATE_LIMIT_ENABLED', False)

        self.stdout.write(f"🔐 认证要求: {'✅ 启用' if auth_required else '❌ 禁用'}")
        self.stdout.write(f"🛡️  CSRF保护: {'✅ 启用' if csrf_required else '❌ 禁用'}")
        self.stdout.write(f"⚡ 速率限制: {'✅ 启用' if rate_limit_enabled else '❌ 禁用'}")

        if not auth_required:
            self.stdout.write('\n💡 提示：认证已禁用，API无需Bearer Token即可访问')
        else:
            self.stdout.write('\n💡 提示：认证已启用，API需要Bearer Token才能访问')

        self.stdout.write('─' * 50)
