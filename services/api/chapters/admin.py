from django.contrib import admin

from .models import Chapter


@admin.register(Chapter)
class ChapterAdmin(admin.ModelAdmin):
    list_display = (
        "novel",
        "chapter_number",
        "title",
        "status",
        "audit_status",
        "is_free",
        "price",
        "word_count",
        "published_at",
    )
    list_filter = ("status", "audit_status", "is_free", "novel__category", "published_at", "created_at")
    search_fields = ("title", "content", "novel__title")
    ordering = ("novel", "chapter_number")
    autocomplete_fields = ("novel",)
    readonly_fields = ("word_count", "published_at", "created_at", "updated_at")
    fieldsets = (
        ("基本信息", {"fields": ("novel", "title", "chapter_number", "content")}),
        ("收费信息", {"fields": ("is_free", "price")}),
        ("状态信息", {"fields": ("status", "audit_status", "published_at")}),
        ("统计信息", {"fields": ("word_count",)}),
        ("时间信息", {"fields": ("created_at", "updated_at")}),
    )
