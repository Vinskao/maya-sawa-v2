"""
动态权限类 - 根据配置启用或禁用认证
"""

from rest_framework.permissions import BasePermission, IsAuthenticated, AllowAny
from django.conf import settings


class DynamicAuthenticationPermission(BasePermission):
    """
    动态认证权限类

    根据API_REQUIRE_AUTHENTICATION设置决定是否需要认证
    """

    def has_permission(self, request, view):
        """检查权限"""
        if getattr(settings, 'API_REQUIRE_AUTHENTICATION', False):
            # 如果需要认证，使用IsAuthenticated的权限检查
            auth_permission = IsAuthenticated()
            return auth_permission.has_permission(request, view)
        else:
            # 如果不需要认证，允许所有请求
            return True


class AllowAnyPermission(BasePermission):
    """
    简单的允许所有请求的权限类
    """

    def has_permission(self, request, view):
        return True
