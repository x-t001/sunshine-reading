from django.db.models import Q

from users.permissions import is_admin_user

from .models import Chapter


def get_public_chapters_for_novel(novel_id):
    return (
        Chapter.objects.filter(
            novel_id=novel_id,
            novel__audit_status="approved",
            status=Chapter.Status.PUBLISHED,
            audit_status=Chapter.AuditStatus.APPROVED,
        )
        .exclude(novel__status="removed")
        .order_by("chapter_number")
    )


def get_public_chapter_by_id(chapter_id):
    return (
        Chapter.objects.select_related("novel", "novel__author", "novel__category")
        .filter(
            id=chapter_id,
            novel__audit_status="approved",
            status=Chapter.Status.PUBLISHED,
            audit_status=Chapter.AuditStatus.APPROVED,
        )
        .exclude(novel__status="removed")
        .first()
    )


def get_adjacent_chapter_ids(chapter):
    public_chapters = get_public_chapters_for_novel(chapter.novel_id)
    previous_id = (
        public_chapters.filter(chapter_number__lt=chapter.chapter_number)
        .order_by("-chapter_number")
        .values_list("id", flat=True)
        .first()
    )
    next_id = (
        public_chapters.filter(chapter_number__gt=chapter.chapter_number)
        .order_by("chapter_number")
        .values_list("id", flat=True)
        .first()
    )
    return previous_id, next_id


def get_author_chapters_for_novel(user, novel_id):
    queryset = Chapter.objects.select_related("novel", "novel__author").filter(novel_id=novel_id)
    if not is_admin_user(user):
        queryset = queryset.filter(novel__author=user)
    return queryset.order_by("chapter_number", "id")


def get_author_chapter_by_id(user, chapter_id):
    queryset = Chapter.objects.select_related("novel", "novel__author", "novel__category").filter(id=chapter_id)
    if not is_admin_user(user):
        queryset = queryset.filter(novel__author=user)
    return queryset.first()


def get_admin_pending_chapters(params):
    queryset = Chapter.objects.select_related("novel", "novel__author", "novel__category").filter(
        audit_status=Chapter.AuditStatus.PENDING,
    )

    novel_id = params.get("novel_id")
    if novel_id:
        queryset = queryset.filter(novel_id=novel_id)

    keyword = params.get("keyword")
    if keyword:
        queryset = queryset.filter(Q(title__icontains=keyword) | Q(novel__title__icontains=keyword))

    return queryset.order_by("-updated_at", "-created_at")


def get_admin_chapter_by_id(chapter_id):
    return (
        Chapter.objects.select_related("novel", "novel__author", "novel__category")
        .filter(id=chapter_id)
        .first()
    )


def get_reviewer_pending_chapters(params):
    return get_admin_pending_chapters(params)


def get_reviewer_chapter_by_id(chapter_id):
    return get_admin_chapter_by_id(chapter_id)
