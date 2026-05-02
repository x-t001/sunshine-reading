from django.db.models import F

from chapters.models import Chapter
from novels.models import Novel

from .models import Bookshelf, ReadingHistory


def get_user_bookshelf(user):
    return (
        Bookshelf.objects.filter(user=user)
        .select_related(
            "novel",
            "novel__author",
            "novel__category",
            "last_read_chapter",
        )
        .order_by(F("last_read_at").desc(nulls_last=True), "-updated_at")
    )


def get_user_bookshelf_entry(user, novel_id):
    return (
        Bookshelf.objects.filter(user=user, novel_id=novel_id)
        .select_related(
            "novel",
            "novel__author",
            "novel__category",
            "last_read_chapter",
        )
        .first()
    )


def is_novel_in_user_bookshelf(user, novel_id):
    return Bookshelf.objects.filter(user=user, novel_id=novel_id).exists()


def get_public_novel(novel_id):
    return (
        Novel.objects.select_related("author", "category")
        .filter(id=novel_id, audit_status=Novel.AuditStatus.APPROVED)
        .exclude(status=Novel.Status.REMOVED)
        .first()
    )


def get_public_chapter_for_novel(novel_id, chapter_id):
    return (
        Chapter.objects.select_related("novel", "novel__author", "novel__category")
        .filter(
            id=chapter_id,
            novel_id=novel_id,
            novel__audit_status=Novel.AuditStatus.APPROVED,
            status=Chapter.Status.PUBLISHED,
            audit_status=Chapter.AuditStatus.APPROVED,
        )
        .exclude(novel__status=Novel.Status.REMOVED)
        .first()
    )


def get_user_reading_history(user):
    return (
        ReadingHistory.objects.filter(user=user)
        .select_related(
            "novel",
            "novel__author",
            "novel__category",
            "chapter",
        )
        .order_by("-read_at")
    )
