from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class SunshineUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (
            "Profile",
            {
                "fields": (
                    "nickname",
                    "avatar",
                    "bio",
                    "role",
                    "phone",
                    "is_banned",
                ),
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "Profile",
            {
                "fields": (
                    "nickname",
                    "role",
                    "phone",
                ),
            },
        ),
    )
    list_display = (
        "username",
        "email",
        "nickname",
        "role",
        "is_banned",
        "is_staff",
        "date_joined",
    )
    list_filter = UserAdmin.list_filter + ("role", "is_banned")
    search_fields = UserAdmin.search_fields + ("nickname", "phone")
