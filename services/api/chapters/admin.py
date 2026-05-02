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
    list_filter = ("status", "audit_status", "is_free", "published_at")
    search_fields = ("title", "novel__title")
    autocomplete_fields = ("novel",)
