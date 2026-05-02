from django.contrib import admin

from .models import Category, Novel, NovelRating


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "sort_order", "is_active")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Novel)
class NovelAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "author",
        "category",
        "status",
        "audit_status",
        "word_count",
        "view_count",
        "rating_score",
        "rating_count",
        "is_featured",
        "latest_chapter_updated_at",
    )
    list_filter = ("status", "audit_status", "is_featured", "category")
    search_fields = ("title", "author__username", "author__nickname")
    autocomplete_fields = ("author", "category")


@admin.register(NovelRating)
class NovelRatingAdmin(admin.ModelAdmin):
    list_display = ("user", "novel", "score", "comment", "created_at", "updated_at")
    list_filter = ("score", "created_at")
    search_fields = ("user__username", "user__nickname", "novel__title", "comment")
    autocomplete_fields = ("user", "novel")
