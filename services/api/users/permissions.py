from rest_framework.exceptions import NotAuthenticated, PermissionDenied
from rest_framework.permissions import BasePermission


def is_staff_admin_user(user):
    return bool(
        user
        and user.is_authenticated
        and (
            getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
        )
    )


def is_admin_user(user):
    return bool(
        user
        and user.is_authenticated
        and (
            getattr(user, "is_staff", False)
            or getattr(user, "is_superuser", False)
            or getattr(user, "role", "") == "admin"
        )
    )


def is_reviewer_user(user):
    return bool(user and user.is_authenticated and getattr(user, "role", "") == "reviewer")


def is_author_user(user):
    return bool(user and user.is_authenticated and getattr(user, "role", "") == "author")


class IsAuthenticatedAndNotBanned(BasePermission):
    message = "请先登录。"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated("请先登录。")
        if getattr(user, "is_banned", False):
            raise PermissionDenied("用户已被封禁。")
        return True


class IsAuthorOrAdmin(BasePermission):
    message = "Author permission is required."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated("Please login first.")
        if getattr(user, "is_banned", False):
            raise PermissionDenied("User is banned.")
        if is_author_user(user) or is_admin_user(user):
            return True
        raise PermissionDenied("Only authors or admins can access author APIs.")


class IsStaffAdmin(BasePermission):
    message = "需要管理员权限。"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated("请先登录。")
        if getattr(user, "is_banned", False):
            raise PermissionDenied("用户已被封禁。")
        if is_staff_admin_user(user):
            return True
        raise PermissionDenied("只有 staff 管理员可以访问审核接口。")


class IsReviewerOrAdmin(BasePermission):
    message = "Review permission is required."

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated("请先登录。")
        if getattr(user, "is_banned", False):
            raise PermissionDenied("用户已被封禁。")
        if is_reviewer_user(user) or is_admin_user(user):
            return True
        raise PermissionDenied("只有审核员或管理员可以访问审核接口。")


class IsAdminUser(BasePermission):
    message = "需要管理员权限。"

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            raise NotAuthenticated("请先登录。")
        if getattr(user, "is_banned", False):
            raise PermissionDenied("用户已被封禁。")
        if is_admin_user(user):
            return True
        raise PermissionDenied("只有管理员可以访问管理接口。")


class IsNovelOwnerOrAdmin(BasePermission):
    message = "Only the novel owner or an admin can access this resource."

    def has_object_permission(self, request, view, obj):
        user = request.user
        if is_admin_user(user):
            return True

        novel = obj
        if hasattr(obj, "novel"):
            novel = obj.novel

        return bool(getattr(novel, "author_id", None) == getattr(user, "id", None))
