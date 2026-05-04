from django.contrib import admin

from .models import Category, Novel, NovelRating


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "parent", "sort_order", "is_active")
    list_filter = ("is_active", "parent")
    search_fields = ("name", "slug")
    ordering = ("sort_order", "name")
    prepopulated_fields = {"slug": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("基本信息", {"fields": ("name", "slug", "parent")}),
        ("状态信息", {"fields": ("sort_order", "is_active")}),
        ("时间信息", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(Novel)
class NovelAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "author",
        "category",
        "status",
        "audit_status",
        "reviewer",
        "reviewed_at",
        "word_count",
        "view_count",
        "rating_score",
        "rating_count",
        "is_featured",
        "latest_chapter_updated_at",
    )
    list_filter = ("status", "audit_status", "reviewer", "is_featured", "category", "created_at")
    search_fields = ("title", "description", "author__username", "author__nickname")
    ordering = ("-updated_at", "-created_at")
    autocomplete_fields = ("author", "category", "reviewer")
    readonly_fields = (
        "word_count",
        "view_count",
        "collect_count",
        "comment_count",
        "rating_score",
        "rating_count",
        "reviewed_at",
        "latest_chapter_title",
        "latest_chapter_updated_at",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("基本信息", {"fields": ("title", "author", "category", "cover", "description")}),
        ("状态信息", {"fields": ("status", "audit_status", "reviewer", "reviewed_at", "is_featured")}),
        (
            "统计信息",
            {
                "fields": (
                    "word_count",
                    "view_count",
                    "collect_count",
                    "comment_count",
                    "rating_score",
                    "rating_count",
                    "latest_chapter_title",
                    "latest_chapter_updated_at",
                ),
            },
        ),
        ("时间信息", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(NovelRating)
class NovelRatingAdmin(admin.ModelAdmin):
    list_display = ("user", "novel", "score", "comment", "created_at", "updated_at")
    list_filter = ("score", "created_at")
    search_fields = ("user__username", "user__nickname", "novel__title", "comment")
    ordering = ("-created_at",)
    autocomplete_fields = ("user", "novel")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("基本信息", {"fields": ("user", "novel", "score", "comment")}),
        ("时间信息", {"fields": ("created_at", "updated_at")}),
    )
