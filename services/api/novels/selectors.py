from django.db.models import Q

from .models import Category, Novel


def get_enabled_categories():
    return Category.objects.filter(is_active=True).order_by("sort_order", "id")


def get_public_novels(params):
    queryset = (
        Novel.objects.select_related("author", "category")
        .filter(audit_status=Novel.AuditStatus.APPROVED)
        .exclude(status=Novel.Status.REMOVED)
    )

    category = params.get("category")
    if category:
        if str(category).isdigit():
            queryset = queryset.filter(category_id=int(category))
        else:
            queryset = queryset.filter(category__slug=category)

    status = params.get("status")
    if status:
        queryset = queryset.filter(status=status)

    keyword = params.get("keyword")
    if keyword:
        queryset = queryset.filter(
            Q(title__icontains=keyword)
            | Q(author__nickname__icontains=keyword)
            | Q(description__icontains=keyword)
        )

    ordering = params.get("ordering")
    ordering_map = {
        "latest": ("-latest_chapter_updated_at", "-created_at"),
        "views": ("-view_count", "-latest_chapter_updated_at", "-created_at"),
        "collects": ("-collect_count", "-latest_chapter_updated_at", "-created_at"),
        "rating": ("-rating_score", "-latest_chapter_updated_at", "-created_at"),
    }
    return queryset.order_by(*ordering_map.get(ordering, ordering_map["latest"]))


def get_public_novel_by_id(novel_id):
    return (
        Novel.objects.select_related("author", "category")
        .filter(
            id=novel_id,
            audit_status=Novel.AuditStatus.APPROVED,
        )
        .exclude(status=Novel.Status.REMOVED)
        .first()
    )
