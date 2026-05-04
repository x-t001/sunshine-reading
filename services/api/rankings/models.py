from decimal import Decimal

from django.db import models

from common.models import TimeStampedModel


class RankingType(TimeStampedModel):
    name = models.CharField("榜单名称", max_length=100)
    code = models.SlugField("榜单编码", max_length=100, unique=True)
    description = models.TextField("描述", blank=True)
    is_active = models.BooleanField("是否启用", default=True, db_index=True)

    class Meta:
        verbose_name = "榜单类型"
        verbose_name_plural = "榜单类型管理"
        ordering = ["code"]
        indexes = [
            models.Index(fields=["is_active", "code"]),
        ]

    def __str__(self):
        return self.name


class RankingItem(TimeStampedModel):
    ranking_type = models.ForeignKey(
        RankingType,
        verbose_name="榜单类型",
        related_name="items",
        on_delete=models.CASCADE,
    )
    novel = models.ForeignKey(
        "novels.Novel",
        verbose_name="小说",
        related_name="ranking_items",
        on_delete=models.CASCADE,
    )
    score = models.DecimalField(
        "分数",
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        db_index=True,
    )
    rank = models.PositiveIntegerField("排名", db_index=True)
    calculated_at = models.DateTimeField("计算时间", db_index=True)

    class Meta:
        verbose_name = "榜单条目"
        verbose_name_plural = "榜单条目管理"
        ordering = ["ranking_type_id", "rank"]
        constraints = [
            models.UniqueConstraint(
                fields=["ranking_type", "novel", "calculated_at"],
                name="unique_ranking_item_per_snapshot",
            ),
            models.UniqueConstraint(
                fields=["ranking_type", "rank", "calculated_at"],
                name="unique_ranking_rank_per_snapshot",
            ),
        ]
        indexes = [
            models.Index(fields=["ranking_type", "rank"]),
            models.Index(fields=["ranking_type", "calculated_at"]),
            models.Index(fields=["novel"]),
            models.Index(fields=["-score"]),
        ]

    def __str__(self):
        return f"{self.ranking_type} #{self.rank} {self.novel}"
