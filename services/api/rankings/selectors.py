from novels.models import Novel

from .models import RankingItem, RankingType


def get_active_ranking_types_with_items():
    ranking_types = list(RankingType.objects.filter(is_active=True).order_by("code"))

    for ranking_type in ranking_types:
        ranking_type.public_items = list(
            RankingItem.objects.select_related("novel", "novel__author", "novel__category")
            .filter(
                ranking_type=ranking_type,
                novel__audit_status=Novel.AuditStatus.APPROVED,
            )
            .exclude(novel__status=Novel.Status.REMOVED)
            .order_by("rank")[:10]
        )

    return ranking_types
