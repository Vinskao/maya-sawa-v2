"""
權限類單元測試
測試不需要連資料庫的方法
"""

import pytest
from unittest.mock import patch, MagicMock
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from maya_sawa_v2.api.permissions import (
    DynamicAuthenticationPermission,
    AllowAnyPermission
)
from rest_framework.permissions import IsAuthenticated


class TestDynamicAuthenticationPermission:
    """動態認證權限類測試"""

    def setup_method(self):
        """設置測試環境"""
        self.permission = DynamicAuthenticationPermission()
        self.factory = RequestFactory()

    def test_permission_initialization(self):
        """測試權限類初始化"""
        assert isinstance(self.permission, DynamicAuthenticationPermission)

    @patch('maya_sawa_v2.api.permissions.settings')
    def test_has_permission_when_authentication_required(self, mock_settings):
        """測試當需要認證時的權限檢查"""
        # 設置需要認證
        mock_settings.API_REQUIRE_AUTHENTICATION = True

        # 建立已認證用戶的請求
        user = MagicMock()
        user.is_authenticated = True
        request = self.factory.get('/')
        request.user = user

        # 測試已認證用戶
        result = self.permission.has_permission(request, None)
        assert result is True

        # 建立未認證用戶的請求
        request.user = AnonymousUser()

        # 測試未認證用戶
        result = self.permission.has_permission(request, None)
        assert result is False

    @patch('maya_sawa_v2.api.permissions.settings')
    def test_has_permission_when_authentication_not_required(self, mock_settings):
        """測試當不需要認證時的權限檢查"""
        # 設置不需要認證
        mock_settings.API_REQUIRE_AUTHENTICATION = False

        # 建立已認證用戶的請求
        user = MagicMock()
        user.is_authenticated = True
        request = self.factory.get('/')
        request.user = user

        # 測試已認證用戶
        result = self.permission.has_permission(request, None)
        assert result is True

        # 建立未認證用戶的請求
        request.user = AnonymousUser()

        # 測試未認證用戶
        result = self.permission.has_permission(request, None)
        assert result is True

    @patch('maya_sawa_v2.api.permissions.settings')
    def test_has_permission_with_missing_setting(self, mock_settings):
        """測試當設置缺失時的權限檢查"""
        # 移除設置
        if hasattr(mock_settings, 'API_REQUIRE_AUTHENTICATION'):
            delattr(mock_settings, 'API_REQUIRE_AUTHENTICATION')

        # 建立未認證用戶的請求
        request = self.factory.get('/')
        request.user = AnonymousUser()

        # 測試未認證用戶（預設允許）
        result = self.permission.has_permission(request, None)
        assert result is True

    @patch('maya_sawa_v2.api.permissions.settings')
    def test_has_permission_with_none_user(self, mock_settings):
        """測試當用戶為 None 時的權限檢查"""
        # 設置需要認證
        mock_settings.API_REQUIRE_AUTHENTICATION = True

        # 建立用戶為 None 的請求
        request = self.factory.get('/')
        request.user = None

        # 測試用戶為 None
        result = self.permission.has_permission(request, None)
        assert result is False

    @patch('maya_sawa_v2.api.permissions.settings')
    def test_has_permission_with_view_context(self, mock_settings):
        """測試帶視圖上下文的權限檢查"""
        # 設置需要認證
        mock_settings.API_REQUIRE_AUTHENTICATION = True

        # 建立模擬視圖
        view = MagicMock()

        # 建立已認證用戶的請求
        user = MagicMock()
        user.is_authenticated = True
        request = self.factory.get('/')
        request.user = user

        # 測試帶視圖的權限檢查
        result = self.permission.has_permission(request, view)
        assert result is True


class TestAllowAnyPermission:
    """允許所有請求權限類測試"""

    def setup_method(self):
        """設置測試環境"""
        self.permission = AllowAnyPermission()
        self.factory = RequestFactory()

    def test_permission_initialization(self):
        """測試權限類初始化"""
        assert isinstance(self.permission, AllowAnyPermission)

    def test_has_permission_with_authenticated_user(self):
        """測試已認證用戶的權限檢查"""
        # 建立已認證用戶的請求
        user = MagicMock()
        user.is_authenticated = True
        request = self.factory.get('/')
        request.user = user

        result = self.permission.has_permission(request, None)
        assert result is True

    def test_has_permission_with_anonymous_user(self):
        """測試匿名用戶的權限檢查"""
        # 建立匿名用戶的請求
        request = self.factory.get('/')
        request.user = AnonymousUser()

        result = self.permission.has_permission(request, None)
        assert result is True

    def test_has_permission_with_none_user(self):
        """測試用戶為 None 的權限檢查"""
        # 建立用戶為 None 的請求
        request = self.factory.get('/')
        request.user = None

        result = self.permission.has_permission(request, None)
        assert result is True

    def test_has_permission_with_different_request_methods(self):
        """測試不同請求方法的權限檢查"""
        methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']

        for method in methods:
            request = self.factory.generic(method, '/')
            request.user = AnonymousUser()

            result = self.permission.has_permission(request, None)
            assert result is True

    def test_has_permission_with_view_context(self):
        """測試帶視圖上下文的權限檢查"""
        # 建立模擬視圖
        view = MagicMock()

        # 建立請求
        request = self.factory.get('/')
        request.user = AnonymousUser()

        result = self.permission.has_permission(request, view)
        assert result is True

    def test_has_permission_consistency(self):
        """測試權限檢查的一致性"""
        # 建立多個不同的請求
        requests = [
            self.factory.get('/'),
            self.factory.post('/'),
            self.factory.put('/'),
            self.factory.delete('/'),
        ]

        for request in requests:
            request.user = AnonymousUser()
            result = self.permission.has_permission(request, None)
            assert result is True


class TestPermissionComparison:
    """權限類比較測試"""

    def test_dynamic_vs_allow_any_permission(self):
        """測試動態權限與允許所有權限的差異"""
        dynamic_permission = DynamicAuthenticationPermission()
        allow_any_permission = AllowAnyPermission()

        factory = RequestFactory()
        request = factory.get('/')
        request.user = AnonymousUser()

        # 當不需要認證時，兩者行為相同
        with patch('maya_sawa_v2.api.permissions.settings') as mock_settings:
            mock_settings.API_REQUIRE_AUTHENTICATION = False

            dynamic_result = dynamic_permission.has_permission(request, None)
            allow_any_result = allow_any_permission.has_permission(request, None)

            assert dynamic_result == allow_any_result
            assert dynamic_result is True

    def test_dynamic_vs_is_authenticated_permission(self):
        """測試動態權限與標準認證權限的差異"""
        dynamic_permission = DynamicAuthenticationPermission()
        is_authenticated_permission = IsAuthenticated()

        factory = RequestFactory()
        request = factory.get('/')
        request.user = AnonymousUser()

        # 當需要認證時，動態權限應該與標準認證權限行為相同
        with patch('maya_sawa_v2.api.permissions.settings') as mock_settings:
            mock_settings.API_REQUIRE_AUTHENTICATION = True

            dynamic_result = dynamic_permission.has_permission(request, None)
            is_authenticated_result = is_authenticated_permission.has_permission(request, None)

            assert dynamic_result == is_authenticated_result
            assert dynamic_result is False
