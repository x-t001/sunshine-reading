from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        "content_type",
        "object_id",
        "reviewer",
        "action",
        "from_status",
        "to_status",
        "created_at",
    )
    list_filter = ("content_type", "action", "created_at")
    search_fields = ("object_id", "reviewer__username", "reviewer__nickname", "reason")
    ordering = ("-created_at",)
    readonly_fields = (
        "content_type",
        "object_id",
        "reviewer",
        "action",
        "from_status",
        "to_status",
        "reason",
        "created_at",
    )
    fieldsets = (
        ("审核对象", {"fields": ("content_type", "object_id")}),
        ("审核操作", {"fields": ("reviewer", "action", "from_status", "to_status", "reason")}),
        ("时间信息", {"fields": ("created_at",)}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
