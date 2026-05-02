from django.contrib import admin

from .models import RankingItem, RankingType


@admin.register(RankingType)
class RankingTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "is_active", "created_at")
    list_filter = ("is_active",)
    search_fields = ("name", "code")
    prepopulated_fields = {"code": ("name",)}


@admin.register(RankingItem)
class RankingItemAdmin(admin.ModelAdmin):
    list_display = ("ranking_type", "rank", "novel", "score", "calculated_at")
    list_filter = ("ranking_type", "calculated_at")
    search_fields = ("ranking_type__name", "ranking_type__code", "novel__title")
    autocomplete_fields = ("ranking_type", "novel")
