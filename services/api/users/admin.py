from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class SunshineUserAdmin(UserAdmin):
    fieldsets = (
        ("账号信息", {"fields": ("username", "password")}),
        (
            "个人资料",
            {
                "fields": (
                    "nickname",
                    "email",
                    "avatar",
                    "bio",
                    "phone",
                ),
            },
        ),
        (
            "权限与状态",
            {
                "fields": (
                    "role",
                    "is_banned",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        ("时间信息", {"fields": ("last_login", "date_joined", "created_at", "updated_at")}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "个人资料",
            {
                "fields": (
                    "nickname",
                    "role",
                    "phone",
                ),
            },
        ),
    )
    readonly_fields = ("last_login", "date_joined", "created_at", "updated_at")
    list_display = (
        "username",
        "nickname",
        "email",
        "role",
        "is_banned",
        "is_staff",
        "date_joined",
    )
    list_filter = ("role", "is_banned", "is_staff", "is_superuser", "is_active", "date_joined")
    search_fields = ("username", "nickname", "email", "phone")
    ordering = ("-date_joined",)
