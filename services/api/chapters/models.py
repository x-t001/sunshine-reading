from decimal import Decimal

from django.db import models

from common.models import TimeStampedModel


class Chapter(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        HIDDEN = "hidden", "Hidden"

    class AuditStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    novel = models.ForeignKey(
        "novels.Novel",
        related_name="chapters",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=255, db_index=True)
    chapter_number = models.PositiveIntegerField()
    content = models.TextField()
    word_count = models.PositiveIntegerField(default=0)
    is_free = models.BooleanField(default=True, db_index=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    audit_status = models.CharField(
        max_length=20,
        choices=AuditStatus.choices,
        default=AuditStatus.PENDING,
        db_index=True,
    )
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["novel_id", "chapter_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["novel", "chapter_number"],
                name="unique_chapter_number_per_novel",
            ),
        ]
        indexes = [
            models.Index(fields=["novel", "chapter_number"]),
            models.Index(fields=["novel", "status", "chapter_number"]),
            models.Index(fields=["status", "published_at"]),
            models.Index(fields=["audit_status"]),
        ]

    def __str__(self):
        return f"{self.novel} - {self.chapter_number}. {self.title}"
