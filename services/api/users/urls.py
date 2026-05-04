from django.urls import path

from .views import (
    AdminUserBanView,
    AdminUserDetailView,
    AdminUserListView,
    AdminUserRoleView,
    AdminUserUnbanView,
    CurrentUserView,
    LoginView,
    RefreshTokenView,
    RegisterView,
)

app_name = "users"

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", RefreshTokenView.as_view(), name="auth-refresh"),
    path("users/me/", CurrentUserView.as_view(), name="users-me"),
    path("admin/users/", AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/<int:id>/", AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/users/<int:id>/role/", AdminUserRoleView.as_view(), name="admin-user-role"),
    path("admin/users/<int:id>/ban/", AdminUserBanView.as_view(), name="admin-user-ban"),
    path("admin/users/<int:id>/unban/", AdminUserUnbanView.as_view(), name="admin-user-unban"),
]
