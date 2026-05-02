from decimal import Decimal

from django.db import models

from common.models import TimeStampedModel


class RankingType(TimeStampedModel):
    name = models.CharField(max_length=100)
    code = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["code"]
        indexes = [
            models.Index(fields=["is_active", "code"]),
        ]

    def __str__(self):
        return self.name


class RankingItem(TimeStampedModel):
    ranking_type = models.ForeignKey(
        RankingType,
        related_name="items",
        on_delete=models.CASCADE,
    )
    novel = models.ForeignKey(
        "novels.Novel",
        related_name="ranking_items",
        on_delete=models.CASCADE,
    )
    score = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        db_index=True,
    )
    rank = models.PositiveIntegerField(db_index=True)
    calculated_at = models.DateTimeField(db_index=True)

    class Meta:
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
