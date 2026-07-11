from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditLog(models.Model):
    class ContentType(models.TextChoices):
        NOVEL = "novel", "\u5c0f\u8bf4"
        CHAPTER = "chapter", "\u7ae0\u8282"
        USER = "user", "\u7528\u6237"
        CATEGORY = "category", "\u5206\u7c7b"
        COMMENT = "comment", "\u8bc4\u8bba"
        RANKING_TYPE = "ranking_type", "\u699c\u5355\u7c7b\u578b"
        RANKING_ITEM = "ranking_item", "\u699c\u5355\u6761\u76ee"
        VIDEO_PROJECT = "video_project", "Video project"
        VIDEO_SCENE = "video_scene", "Video scene"

    class Action(models.TextChoices):
        SUBMIT = "submit", "\u63d0\u4ea4\u5ba1\u6838"
        CLAIM = "claim", "\u9886\u53d6\u5ba1\u6838"
        APPROVE = "approve", "\u5ba1\u6838\u901a\u8fc7"
        REJECT = "reject", "\u5ba1\u6838\u9a73\u56de"
        CREATE = "create", "\u521b\u5efa"
        UPDATE = "update", "\u66f4\u65b0"
        STATUS_UPDATE = "status_update", "\u72b6\u6001\u53d8\u66f4"
        FEATURE_UPDATE = "feature_update", "\u63a8\u8350\u53d8\u66f4"
        ROLE_UPDATE = "role_update", "\u89d2\u8272\u53d8\u66f4"
        BAN = "ban", "\u5c01\u7981"
        UNBAN = "unban", "\u89e3\u5c01"
        DELETE = "delete", "Delete"

    content_type = models.CharField(
        "\u5ba1\u6838\u5bf9\u8c61\u7c7b\u578b",
        max_length=20,
        choices=ContentType.choices,
        db_index=True,
    )
    object_id = models.PositiveBigIntegerField("\u5ba1\u6838\u5bf9\u8c61 ID", db_index=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="\u5ba1\u6838\u5458",
        null=True,
        blank=True,
        related_name="audit_logs",
        on_delete=models.SET_NULL,
    )
    action = models.CharField("\u64cd\u4f5c\u7c7b\u578b", max_length=20, choices=Action.choices, db_index=True)
    from_status = models.CharField("\u539f\u5ba1\u6838\u72b6\u6001", max_length=20, blank=True)
    to_status = models.CharField("\u65b0\u5ba1\u6838\u72b6\u6001", max_length=20, blank=True)
    reason = models.TextField("\u5ba1\u6838\u610f\u89c1", blank=True)
    created_at = models.DateTimeField("\u521b\u5efa\u65f6\u95f4", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "\u5ba1\u6838\u8bb0\u5f55"
        verbose_name_plural = "\u5ba1\u6838\u8bb0\u5f55\u7ba1\u7406"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id", "created_at"]),
            models.Index(fields=["reviewer", "action", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_content_type_display()} #{self.object_id} {self.get_action_display()}"
