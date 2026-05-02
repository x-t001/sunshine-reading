from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission


class IsAuthenticatedAndNotBanned(BasePermission):
    message = "请先登录。"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated("请先登录。")
        if getattr(user, "is_banned", False):
            raise PermissionDenied("用户已被封禁。")
        return True
