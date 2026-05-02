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
