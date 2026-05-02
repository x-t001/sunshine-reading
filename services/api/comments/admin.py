from django.contrib import admin

from .models import Comment


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "novel", "chapter", "status", "like_count", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("content", "user__username", "user__nickname", "novel__title")
    autocomplete_fields = ("user", "novel", "chapter", "parent")
