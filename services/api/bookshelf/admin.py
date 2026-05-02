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
    autocomplete_fields = ("user", "novel", "last_read_chapter")


@admin.register(ReadingHistory)
class ReadingHistoryAdmin(admin.ModelAdmin):
    list_display = ("user", "novel", "chapter", "reading_position", "read_at")
    list_filter = ("read_at",)
    search_fields = ("user__username", "user__nickname", "novel__title", "chapter__title")
    autocomplete_fields = ("user", "novel", "chapter")
