from django.db.models import Count, Q
from users.permissions import is_admin_user

from common.models import AuditLog

from .models import Category, Novel, NovelRating


def get_enabled_categories():
    return Category.objects.filter(is_active=True).order_by("sort_order", "id")


def get_admin_categories(params):
    queryset = Category.objects.select_related("parent").annotate(
        children_count=Count("children", distinct=True),
        novel_count=Count("novels", distinct=True),
    )

    keyword = params.get("keyword")
    if keyword:
        queryset = queryset.filter(Q(name__icontains=keyword) | Q(slug__icontains=keyword))

    if "is_active" in params:
        queryset = queryset.filter(is_active=params["is_active"])

    parent_id = params.get("parent_id")
    if parent_id:
        queryset = queryset.filter(parent_id=parent_id)

    return queryset.order_by("sort_order", "id")


def get_admin_category_by_id(category_id):
    return (
        Category.objects.select_related("parent")
        .annotate(
            children_count=Count("children", distinct=True),
            novel_count=Count("novels", distinct=True),
        )
        .filter(id=category_id)
        .first()
    )


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


def get_author_novel_audit_logs(novel_id):
    return (
        AuditLog.objects.select_related("reviewer")
        .filter(content_type=AuditLog.ContentType.NOVEL, object_id=novel_id)
        .order_by("-created_at")
    )


def get_admin_pending_novels(params):
    queryset = Novel.objects.select_related("author", "category", "reviewer").filter(audit_status=Novel.AuditStatus.PENDING)

    keyword = params.get("keyword")
    if keyword:
        queryset = queryset.filter(
            Q(title__icontains=keyword)
            | Q(description__icontains=keyword)
            | Q(author__username__icontains=keyword)
            | Q(author__nickname__icontains=keyword)
        )

    return queryset.order_by("-updated_at", "-created_at")


def get_admin_novels(params):
    queryset = Novel.objects.select_related("author", "category", "reviewer")

    keyword = params.get("keyword")
    if keyword:
        queryset = queryset.filter(
            Q(title__icontains=keyword)
            | Q(description__icontains=keyword)
            | Q(author__username__icontains=keyword)
            | Q(author__nickname__icontains=keyword)
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

    audit_status = params.get("audit_status")
    if audit_status:
        queryset = queryset.filter(audit_status=audit_status)

    author_id = params.get("author_id")
    if author_id:
        queryset = queryset.filter(author_id=author_id)

    return queryset.order_by("-created_at", "-id")


def get_admin_novel_by_id(novel_id):
    return (
        Novel.objects.select_related("author", "category", "reviewer")
        .annotate(chapter_count=Count("chapters", distinct=True))
        .filter(id=novel_id)
        .first()
    )


def get_reviewer_pending_novels(params):
    return get_admin_pending_novels(params)


def get_reviewer_reviewing_novels(user, params):
    queryset = Novel.objects.select_related("author", "category", "reviewer").filter(
        audit_status=Novel.AuditStatus.REVIEWING,
    )
    if not is_admin_user(user):
        queryset = queryset.filter(reviewer=user)

    keyword = params.get("keyword")
    if keyword:
        queryset = queryset.filter(
            Q(title__icontains=keyword)
            | Q(description__icontains=keyword)
            | Q(author__username__icontains=keyword)
            | Q(author__nickname__icontains=keyword)
        )

    return queryset.order_by("-updated_at", "-created_at")


def get_reviewer_novel_by_id(user, novel_id):
    queryset = (
        Novel.objects.select_related("author", "category", "reviewer")
        .annotate(chapter_count=Count("chapters", distinct=True))
        .filter(id=novel_id)
    )
    if not is_admin_user(user):
        queryset = queryset.filter(Q(audit_status=Novel.AuditStatus.PENDING) | Q(reviewer=user))
    return queryset.first()


def get_reviewer_audit_logs(params):
    queryset = AuditLog.objects.select_related("reviewer")

    content_type = params.get("content_type")
    if content_type:
        queryset = queryset.filter(content_type=content_type)

    action = params.get("action")
    if action:
        queryset = queryset.filter(action=action)

    return queryset.order_by("-created_at")
