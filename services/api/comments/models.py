from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class Comment(TimeStampedModel):
    class Status(models.TextChoices):
        NORMAL = "normal", "正常"
        HIDDEN = "hidden", "已隐藏"
        DELETED = "deleted", "已删除"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="用户",
        related_name="comments",
        on_delete=models.CASCADE,
    )
    novel = models.ForeignKey(
        "novels.Novel",
        verbose_name="小说",
        related_name="comments",
        on_delete=models.CASCADE,
    )
    chapter = models.ForeignKey(
        "chapters.Chapter",
        verbose_name="章节",
        null=True,
        blank=True,
        related_name="comments",
        on_delete=models.SET_NULL,
    )
    parent = models.ForeignKey(
        "self",
        verbose_name="父评论",
        null=True,
        blank=True,
        related_name="replies",
        on_delete=models.SET_NULL,
    )
    content = models.TextField("评论内容")
    like_count = models.PositiveIntegerField("点赞数", default=0, db_index=True)
    status = models.CharField(
        "评论状态",
        max_length=20,
        choices=Status.choices,
        default=Status.NORMAL,
        db_index=True,
    )

    class Meta:
        verbose_name = "评论"
        verbose_name_plural = "评论管理"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["novel", "status", "created_at"]),
            models.Index(fields=["chapter", "status", "created_at"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        return self.content[:50]
