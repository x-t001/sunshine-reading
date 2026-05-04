from decimal import Decimal

from django.conf import settings
from django.db import models

from common.models import TimeStampedModel


class Category(TimeStampedModel):
    name = models.CharField("分类名称", max_length=100)
    slug = models.SlugField("分类标识", max_length=120, unique=True)
    parent = models.ForeignKey(
        "self",
        verbose_name="父分类",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.SET_NULL,
    )
    sort_order = models.PositiveIntegerField("排序值", default=0, db_index=True)
    is_active = models.BooleanField("是否启用", default=True, db_index=True)

    class Meta:
        verbose_name = "分类"
        verbose_name_plural = "分类管理"
        ordering = ["sort_order", "name"]
        indexes = [
            models.Index(fields=["parent", "sort_order"]),
            models.Index(fields=["is_active", "sort_order"]),
        ]

    def __str__(self):
        return self.name


class Novel(TimeStampedModel):
    class Status(models.TextChoices):
        SERIALIZING = "serializing", "连载中"
        COMPLETED = "completed", "已完结"
        PAUSED = "paused", "暂停更新"
        REMOVED = "removed", "已下架"

    class AuditStatus(models.TextChoices):
        DRAFT = "draft", "草稿"
        PENDING = "pending", "待审核"
        REVIEWING = "reviewing", "审核中"
        APPROVED = "approved", "已通过"
        REJECTED = "rejected", "已驳回"

    title = models.CharField("小说标题", max_length=255, db_index=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="作者",
        related_name="novels",
        on_delete=models.PROTECT,
    )
    category = models.ForeignKey(
        Category,
        verbose_name="分类",
        null=True,
        blank=True,
        related_name="novels",
        on_delete=models.SET_NULL,
    )
    cover = models.URLField("封面", max_length=500, blank=True)
    description = models.TextField("简介", blank=True)
    status = models.CharField(
        "连载状态",
        max_length=20,
        choices=Status.choices,
        default=Status.SERIALIZING,
        db_index=True,
    )
    audit_status = models.CharField(
        "审核状态",
        max_length=20,
        choices=AuditStatus.choices,
        default=AuditStatus.DRAFT,
        db_index=True,
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="审核员",
        null=True,
        blank=True,
        related_name="reviewed_novels",
        on_delete=models.SET_NULL,
    )
    reviewed_at = models.DateTimeField("审核完成时间", null=True, blank=True, db_index=True)
    word_count = models.PositiveIntegerField("字数", default=0)
    view_count = models.PositiveIntegerField("阅读量", default=0, db_index=True)
    collect_count = models.PositiveIntegerField("收藏数", default=0)
    comment_count = models.PositiveIntegerField("评论数", default=0)
    rating_score = models.DecimalField(
        "平均评分",
        max_digits=4,
        decimal_places=2,
        default=Decimal("0.00"),
        db_index=True,
    )
    rating_count = models.PositiveIntegerField("评分人数", default=0, db_index=True)
    latest_chapter_title = models.CharField("最新章节标题", max_length=255, blank=True)
    latest_chapter_updated_at = models.DateTimeField("最新章节更新时间", null=True, blank=True, db_index=True)
    is_featured = models.BooleanField("是否推荐", default=False, db_index=True)

    class Meta:
        verbose_name = "小说"
        verbose_name_plural = "小说管理"
        ordering = ["-latest_chapter_updated_at", "-created_at"]
        indexes = [
            models.Index(fields=["author", "status"]),
            models.Index(fields=["category", "status"]),
            models.Index(fields=["status", "audit_status"]),
            models.Index(fields=["audit_status", "reviewer"]),
            models.Index(fields=["reviewer", "reviewed_at"]),
            models.Index(fields=["is_featured", "audit_status"]),
            models.Index(fields=["-view_count"]),
        ]

    def __str__(self):
        return self.title


class NovelRating(TimeStampedModel):
    class Score(models.IntegerChoices):
        ONE = 1, "1 分"
        TWO = 2, "2 分"
        THREE = 3, "3 分"
        FOUR = 4, "4 分"
        FIVE = 5, "5 分"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="用户",
        related_name="novel_ratings",
        on_delete=models.CASCADE,
    )
    novel = models.ForeignKey(
        Novel,
        verbose_name="小说",
        related_name="ratings",
        on_delete=models.CASCADE,
    )
    score = models.PositiveSmallIntegerField("评分", choices=Score.choices, db_index=True)
    comment = models.CharField("短评", max_length=500, blank=True)

    class Meta:
        verbose_name = "小说评分"
        verbose_name_plural = "小说评分管理"
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
