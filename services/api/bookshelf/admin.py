from django.contrib import admin

from .models import Bookshelf, ReadingHistory


@admin.register(Bookshelf)
class BookshelfAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "novel",
        "last_read_chapter",
        "reading_progress",
        "last_read_at",
    )
    list_filter = ("last_read_at",)
    search_fields = ("user__username", "user__nickname", "novel__title")
    ordering = ("-last_read_at", "-updated_at")
    autocomplete_fields = ("user", "novel", "last_read_chapter")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("基本信息", {"fields": ("user", "novel")}),
        ("阅读信息", {"fields": ("last_read_chapter", "reading_progress", "last_read_at")}),
        ("时间信息", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(ReadingHistory)
class ReadingHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "novel", "chapter", "reading_position", "read_at")
    list_filter = ("read_at",)
    search_fields = ("user__username", "user__nickname", "novel__title", "chapter__title")
    ordering = ("-read_at",)
    autocomplete_fields = ("user", "novel", "chapter")
    readonly_fields = ("read_at", "created_at", "updated_at")
    fieldsets = (
        ("基本信息", {"fields": ("user", "novel", "chapter")}),
        ("阅读信息", {"fields": ("reading_position", "read_at")}),
        ("时间信息", {"fields": ("created_at", "updated_at")}),
    )
