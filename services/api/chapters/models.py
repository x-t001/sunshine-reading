from decimal import Decimal

from django.db import models

from common.models import TimeStampedModel


class Chapter(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        PUBLISHED = "published", "已发布"
        HIDDEN = "hidden", "已隐藏"

    class AuditStatus(models.TextChoices):
        PENDING = "pending", "待审核"
        APPROVED = "approved", "已通过"
        REJECTED = "rejected", "已拒绝"

    novel = models.ForeignKey(
        "novels.Novel",
        verbose_name="所属小说",
        related_name="chapters",
        on_delete=models.CASCADE,
    )
    title = models.CharField("章节标题", max_length=255, db_index=True)
    chapter_number = models.PositiveIntegerField("章节序号")
    content = models.TextField("章节正文")
    word_count = models.PositiveIntegerField("章节字数", default=0)
    is_free = models.BooleanField("是否免费", default=True, db_index=True)
    price = models.DecimalField("价格", max_digits=8, decimal_places=2, default=Decimal("0.00"))
    status = models.CharField(
        "章节状态",
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    audit_status = models.CharField(
        "审核状态",
        max_length=20,
        choices=AuditStatus.choices,
        default=AuditStatus.PENDING,
        db_index=True,
    )
    published_at = models.DateTimeField("发布时间", null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = "章节"
        verbose_name_plural = "章节管理"
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
