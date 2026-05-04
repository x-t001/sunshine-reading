from django.contrib import admin

from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "novel", "chapter", "status", "like_count", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("content", "user__username", "user__nickname", "novel__title")
    ordering = ("-created_at",)
    autocomplete_fields = ("user", "novel", "chapter", "parent")
    readonly_fields = ("like_count", "created_at", "updated_at")
    fieldsets = (
        ("基本信息", {"fields": ("user", "novel", "chapter", "parent")}),
        ("评论内容", {"fields": ("content",)}),
        ("状态信息", {"fields": ("status",)}),
        ("统计信息", {"fields": ("like_count",)}),
        ("时间信息", {"fields": ("created_at", "updated_at")}),
    )
