from django.contrib import admin

from .models import RankingItem, RankingType


@admin.register(RankingType)
class RankingTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code", "description")
    ordering = ("code",)
    prepopulated_fields = {"code": ("name",)}
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("基本信息", {"fields": ("name", "code", "description")}),
        ("状态信息", {"fields": ("is_active",)}),
        ("时间信息", {"fields": ("created_at", "updated_at")}),
    )


@admin.register(RankingItem)
class RankingItemAdmin(admin.ModelAdmin):
    list_display = ("ranking_type", "rank", "novel", "score", "calculated_at")
    list_filter = ("ranking_type", "calculated_at")
    search_fields = ("ranking_type__name", "ranking_type__code", "novel__title")
    ordering = ("ranking_type", "rank")
    autocomplete_fields = ("ranking_type", "novel")
    readonly_fields = ("created_at", "updated_at")
    fieldsets = (
        ("基本信息", {"fields": ("ranking_type", "novel")}),
        ("排行信息", {"fields": ("rank", "score", "calculated_at")}),
        ("时间信息", {"fields": ("created_at", "updated_at")}),
    )
