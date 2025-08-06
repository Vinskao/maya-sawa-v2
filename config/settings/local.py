"""
Local development settings
"""

from .base import *  # noqa

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Database - 使用PostgreSQL
# https://docs.djangoproject.com/en/dev/ref/settings/#databases
# 保持使用base.py中的DATABASES配置（从.env读取PostgreSQL URL）

# ALLOWED_HOSTS for development
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', '0.0.0.0']

# API Security Configuration - 开发环境禁用安全限制
API_REQUIRE_AUTHENTICATION = False
API_REQUIRE_CSRF = False
API_RATE_LIMIT_ENABLED = False
