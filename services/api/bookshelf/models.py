from decimal import Decimal

from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class Bookshelf(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="用户",
        related_name="bookshelves",
        on_delete=models.CASCADE,
    )
    novel = models.ForeignKey(
        "novels.Novel",
        verbose_name="小说",
        related_name="bookshelf_entries",
        on_delete=models.CASCADE,
    )
    last_read_chapter = models.ForeignKey(
        "chapters.Chapter",
        verbose_name="最近阅读章节",
        null=True,
        blank=True,
        related_name="bookshelf_entries",
        on_delete=models.SET_NULL,
    )
    reading_progress = models.DecimalField(
        "阅读进度",
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    last_read_at = models.DateTimeField("最近阅读时间", null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = "书架"
        verbose_name_plural = "书架管理"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "novel"],
                name="unique_bookshelf_user_novel",
            ),
        ]
        indexes = [
            models.Index(fields=["user", "last_read_at"]),
            models.Index(fields=["novel"]),
            models.Index(fields=["last_read_chapter"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.novel}"


class ReadingHistory(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="用户",
        related_name="reading_histories",
        on_delete=models.CASCADE,
    )
    novel = models.ForeignKey(
        "novels.Novel",
        verbose_name="小说",
        related_name="reading_histories",
        on_delete=models.CASCADE,
    )
    chapter = models.ForeignKey(
        "chapters.Chapter",
        verbose_name="章节",
        related_name="reading_histories",
        on_delete=models.CASCADE,
    )
    reading_position = models.PositiveIntegerField("阅读位置", default=0)
    read_at = models.DateTimeField("阅读时间", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "阅读历史"
        verbose_name_plural = "阅读历史管理"
        ordering = ["-read_at"]
        indexes = [
            models.Index(fields=["user", "read_at"]),
            models.Index(fields=["novel", "read_at"]),
            models.Index(fields=["chapter", "read_at"]),
        ]

    def __str__(self):
        return f"{self.user} read {self.chapter}"
