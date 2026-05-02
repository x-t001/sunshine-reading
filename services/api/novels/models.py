from decimal import Decimal

from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.SET_NULL,
    )
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["parent", "sort_order"]),
            models.Index(fields=["is_active", "sort_order"]),
        ]

    def __str__(self):
        return self.name


class Novel(TimeStampedModel):
    class Status(models.TextChoices):
        SERIALIZING = "serializing", "Serializing"
        COMPLETED = "completed", "Completed"
        PAUSED = "paused", "Paused"
        REMOVED = "removed", "Removed"

    class AuditStatus(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    title = models.CharField(max_length=255, db_index=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="novels",
        on_delete=models.PROTECT,
    )
    category = models.ForeignKey(
        Category,
        null=True,
        blank=True,
        related_name="novels",
        on_delete=models.SET_NULL,
    )
    cover = models.URLField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SERIALIZING,
        db_index=True,
    )
    audit_status = models.CharField(
        max_length=20,
        choices=AuditStatus.choices,
        default=AuditStatus.DRAFT,
        db_index=True,
    )
    word_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0, db_index=True)
    collect_count = models.PositiveIntegerField(default=0)
    comment_count = models.PositiveIntegerField(default=0)
    rating_score = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.00"),
        db_index=True,
    )
    rating_count = models.PositiveIntegerField(default=0, db_index=True)
    latest_chapter_title = models.CharField(max_length=255, blank=True)
    latest_chapter_updated_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ["-latest_chapter_updated_at", "-created_at"]
        indexes = [
            models.Index(fields=["author", "status"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["status", "audit_status"]),
            models.Index(fields=["is_featured", "audit_status"]),
            models.Index(fields=["-view_count"]),
        ]

    def __str__(self):
        return self.title


class NovelRating(TimeStampedModel):
    class Score(models.IntegerChoices):
        ONE = 1, "1"
        TWO = 2, "2"
        THREE = 3, "3"
        FOUR = 4, "4"
        FIVE = 5, "5"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="novel_ratings",
        on_delete=models.CASCADE,
    )
    novel = models.ForeignKey(
        Novel,
        related_name="ratings",
        on_delete=models.CASCADE,
    )
    score = models.PositiveSmallIntegerField(choices=Score.choices, db_index=True)
    comment = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "novel"],
                name="unique_novel_rating_user_novel",
            ),
            models.CheckConstraint(
                condition=models.Q(score__gte=1, score__lte=5),
                name="novel_rating_score_between_1_and_5",
            ),
        ]
        indexes = [
            models.Index(fields=["novel", "score"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["novel", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user} rated {self.novel}: {self.score}"
