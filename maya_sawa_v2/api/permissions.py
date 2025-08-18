"""
動態權限類 - 根據配置啟用或禁用認證
"""

from rest_framework.permissions import BasePermission, IsAuthenticated, AllowAny
from django.conf import settings


class DynamicAuthenticationPermission(BasePermission):
    """
    動態認證權限類

    根據API_REQUIRE_AUTHENTICATION設置決定是否需要認證
    """

    def has_permission(self, request, view):
        """檢查權限"""
        if getattr(settings, 'API_REQUIRE_AUTHENTICATION', False):
            # 如果需要認證，使用IsAuthenticated的權限檢查
            auth_permission = IsAuthenticated()
            return auth_permission.has_permission(request, view)
        else:
            # 如果不需要認證，允許所有請求
            return True


class AllowAnyPermission(BasePermission):
    """
    簡單的允許所有請求的權限類
    """

    def has_permission(self, request, view):
        return True
