from django.db.models import Count, Q
from users.permissions import is_admin_user

from .models import Category, Novel, NovelRating


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


def get_rating_for_user(novel_id, user):
    if not user or not user.is_authenticated:
        return None

    return NovelRating.objects.filter(novel_id=novel_id, user=user).first()


def get_author_novels(user, params):
    queryset = Novel.objects.select_related("author", "category")
    if not is_admin_user(user):
        queryset = queryset.filter(author=user)

    keyword = params.get("keyword")
    if keyword:
        queryset = queryset.filter(Q(title__icontains=keyword) | Q(description__icontains=keyword))

    status = params.get("status")
    if status:
        queryset = queryset.filter(status=status)

    audit_status = params.get("audit_status")
    if audit_status:
        queryset = queryset.filter(audit_status=audit_status)

    return queryset.order_by("-updated_at", "-created_at")


def get_author_novel_by_id(user, novel_id):
    queryset = (
        Novel.objects.select_related("author", "category")
        .annotate(chapter_count=Count("chapters", distinct=True))
        .filter(id=novel_id)
    )
    if not is_admin_user(user):
        queryset = queryset.filter(author=user)
    return queryset.first()

