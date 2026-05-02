from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class Comment(TimeStampedModel):
    class Status(models.TextChoices):
        NORMAL = "normal", "Normal"
        HIDDEN = "hidden", "Hidden"
        DELETED = "deleted", "Deleted"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="comments",
        on_delete=models.CASCADE,
    )
    novel = models.ForeignKey(
        "novels.Novel",
        related_name="comments",
        on_delete=models.CASCADE,
    )
    chapter = models.ForeignKey(
        "chapters.Chapter",
        null=True,
        blank=True,
        related_name="comments",
        on_delete=models.SET_NULL,
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="replies",
        on_delete=models.SET_NULL,
    )
    content = models.TextField()
    like_count = models.PositiveIntegerField(default=0, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NORMAL,
        db_index=True,
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["novel", "status", "created_at"]),
            models.Index(fields=["chapter", "status", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        return self.content[:50]
