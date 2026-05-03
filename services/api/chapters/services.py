import re

from django.db import transaction
from django.db.models import Sum
from rest_framework.exceptions import ValidationError

from novels.models import Novel

from .models import Chapter


def calculate_word_count(content):
    return len(re.sub(r"\s+", "", content or ""))


def _validate_unique_chapter_number(novel_id, chapter_number, exclude_chapter_id=None):
    queryset = Chapter.objects.filter(novel_id=novel_id, chapter_number=chapter_number)
    if exclude_chapter_id is not None:
        queryset = queryset.exclude(id=exclude_chapter_id)
    if queryset.exists():
        raise ValidationError({"chapter_number": ["Chapter number already exists for this novel."]})


def recalculate_novel_chapter_stats(novel_id):
    word_count = (
        Chapter.objects.filter(novel_id=novel_id)
        .exclude(status=Chapter.Status.HIDDEN)
        .aggregate(total=Sum("word_count"))["total"]
        or 0
    )
    latest_chapter = (
        Chapter.objects.filter(
            novel_id=novel_id,
            status=Chapter.Status.PUBLISHED,
            audit_status=Chapter.AuditStatus.APPROVED,
        )
        .order_by("-published_at", "-updated_at", "-chapter_number")
        .first()
    )

    Novel.objects.filter(id=novel_id).update(
        word_count=word_count,
        latest_chapter_title=latest_chapter.title if latest_chapter else "",
        latest_chapter_updated_at=(latest_chapter.published_at or latest_chapter.updated_at) if latest_chapter else None,
    )


@transaction.atomic
def create_author_chapter(novel, data):
    _validate_unique_chapter_number(novel.id, data["chapter_number"])
    chapter = Chapter.objects.create(
        novel=novel,
        title=data["title"],
        chapter_number=data["chapter_number"],
        content=data["content"],
        word_count=calculate_word_count(data["content"]),
        is_free=data.get("is_free", True),
        price=data.get("price", "0.00"),
        status=Chapter.Status.DRAFT,
        audit_status=Chapter.AuditStatus.PENDING,
    )
    recalculate_novel_chapter_stats(novel.id)
    return chapter


@transaction.atomic
def update_author_chapter(chapter, data):
    if (
        chapter.status == Chapter.Status.PUBLISHED
        and chapter.audit_status == Chapter.AuditStatus.APPROVED
        and "content" in data
        and data["content"] != chapter.content
    ):
        raise ValidationError({"content": ["Published approved chapter content cannot be edited in this stage."]})

    if "chapter_number" in data:
        _validate_unique_chapter_number(chapter.novel_id, data["chapter_number"], exclude_chapter_id=chapter.id)

    for field in ("title", "chapter_number", "content", "is_free", "price", "status"):
        if field in data:
            setattr(chapter, field, data[field])

    if "content" in data:
        chapter.word_count = calculate_word_count(chapter.content)

    chapter.save()
    recalculate_novel_chapter_stats(chapter.novel_id)
    return chapter


@transaction.atomic
def submit_chapter_review(chapter):
    missing_fields = []
    if not chapter.title:
        missing_fields.append("title")
    if not chapter.content:
        missing_fields.append("content")
    if not chapter.chapter_number:
        missing_fields.append("chapter_number")
    if missing_fields:
        raise ValidationError({"fields": [f"Missing required fields: {', '.join(missing_fields)}."]})

    if chapter.audit_status == Chapter.AuditStatus.APPROVED:
        raise ValidationError({"audit_status": ["Chapter is already approved."]})

    chapter.audit_status = Chapter.AuditStatus.PENDING
    chapter.save(update_fields=["audit_status", "updated_at"])
    return chapter


@transaction.atomic
def delete_author_chapter(chapter):
    novel_id = chapter.novel_id
    if chapter.status == Chapter.Status.PUBLISHED:
        chapter.status = Chapter.Status.HIDDEN
        chapter.save(update_fields=["status", "updated_at"])
    else:
        chapter.delete()
    recalculate_novel_chapter_stats(novel_id)
