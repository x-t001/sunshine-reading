from django.db.models import Count, Q

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


def get_admin_ranking_types(params):
    queryset = RankingType.objects.annotate(item_count=Count("items", distinct=True))

    keyword = params.get("keyword")
    if keyword:
        queryset = queryset.filter(Q(name__icontains=keyword) | Q(code__icontains=keyword) | Q(description__icontains=keyword))

    if "is_active" in params:
        queryset = queryset.filter(is_active=params["is_active"])

    return queryset.order_by("code", "id")


def get_admin_ranking_type_by_id(ranking_type_id):
    return RankingType.objects.annotate(item_count=Count("items", distinct=True)).filter(id=ranking_type_id).first()


def get_admin_ranking_items(params):
    queryset = RankingItem.objects.select_related("ranking_type", "novel")

    ranking_type_id = params.get("ranking_type_id")
    if ranking_type_id:
        queryset = queryset.filter(ranking_type_id=ranking_type_id)

    novel_id = params.get("novel_id")
    if novel_id:
        queryset = queryset.filter(novel_id=novel_id)

    keyword = params.get("keyword")
    if keyword:
        queryset = queryset.filter(Q(novel__title__icontains=keyword) | Q(ranking_type__name__icontains=keyword) | Q(ranking_type__code__icontains=keyword))

    return queryset.order_by("ranking_type_id", "-calculated_at", "rank", "id")


def get_admin_ranking_item_by_id(item_id):
    return RankingItem.objects.select_related("ranking_type", "novel").filter(id=item_id).first()
