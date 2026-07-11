import re

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from common.models import AuditLog
from common.services import create_operation_audit_log
from novels.models import Novel
from users.permissions import is_admin_user

from .models import Chapter


REVIEWABLE_AUDIT_STATUSES = (Chapter.AuditStatus.PENDING, Chapter.AuditStatus.REVIEWING)


def _create_chapter_audit_log(chapter, action, from_status, to_status, reviewer=None, reason=""):
    AuditLog.objects.create(
        content_type=AuditLog.ContentType.CHAPTER,
        object_id=chapter.id,
        reviewer=reviewer,
        action=action,
        from_status=from_status or "",
        to_status=to_status or "",
        reason=reason or "",
    )


def _ensure_can_review_chapter(chapter, reviewer):
    if (
        reviewer
        and chapter.audit_status == Chapter.AuditStatus.REVIEWING
        and chapter.reviewer_id
        and chapter.reviewer_id != reviewer.id
        and not is_admin_user(reviewer)
    ):
        raise PermissionDenied("You can only review chapters you claimed.")


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
        audit_status=Chapter.AuditStatus.DRAFT,
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
def update_admin_chapter_status(chapter, status, actor=None):
    old_status = chapter.status
    should_set_published_at = status == Chapter.Status.PUBLISHED and chapter.published_at is None
    if old_status != status or should_set_published_at:
        chapter.status = status
        if should_set_published_at:
            chapter.published_at = timezone.now()
        chapter.save(update_fields=["status", "published_at", "updated_at"])
        recalculate_novel_chapter_stats(chapter.novel_id)
        if old_status != status:
            create_operation_audit_log(
                content_type=AuditLog.ContentType.CHAPTER,
                object_id=chapter.id,
                actor=actor,
                action=AuditLog.Action.STATUS_UPDATE,
                from_status=old_status,
                to_status=status,
            )
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

    if chapter.audit_status not in (Chapter.AuditStatus.DRAFT, Chapter.AuditStatus.REJECTED):
        if chapter.audit_status == Chapter.AuditStatus.PENDING:
            raise ValidationError({"audit_status": ["Chapter is already pending review."]})
        if chapter.audit_status == Chapter.AuditStatus.REVIEWING:
            raise ValidationError({"audit_status": ["Chapter is already under review."]})
        if chapter.audit_status == Chapter.AuditStatus.APPROVED:
            raise ValidationError({"audit_status": ["Chapter is already approved."]})
        raise ValidationError({"audit_status": ["Chapter cannot be submitted from current audit status."]})

    from_status = chapter.audit_status
    chapter.audit_status = Chapter.AuditStatus.PENDING
    chapter.reviewer = None
    chapter.reviewed_at = None
    chapter.save(update_fields=["audit_status", "reviewer", "reviewed_at", "updated_at"])
    _create_chapter_audit_log(
        chapter=chapter,
        action=AuditLog.Action.SUBMIT,
        from_status=from_status,
        to_status=Chapter.AuditStatus.PENDING,
    )
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


@transaction.atomic
def claim_chapter_review(chapter, reviewer):
    if chapter.audit_status != Chapter.AuditStatus.PENDING:
        raise ValidationError({"audit_status": ["Only pending chapters can be claimed."]})

    from_status = chapter.audit_status
    chapter.audit_status = Chapter.AuditStatus.REVIEWING
    chapter.reviewer = reviewer
    chapter.reviewed_at = None
    chapter.save(update_fields=["audit_status", "reviewer", "reviewed_at", "updated_at"])
    _create_chapter_audit_log(
        chapter=chapter,
        action=AuditLog.Action.CLAIM,
        from_status=from_status,
        to_status=Chapter.AuditStatus.REVIEWING,
        reviewer=reviewer,
    )
    return chapter


@transaction.atomic
def approve_chapter_review(chapter, reviewer=None):
    if chapter.audit_status not in REVIEWABLE_AUDIT_STATUSES:
        raise ValidationError({"audit_status": ["Only pending or reviewing chapters can be approved."]})
    _ensure_can_review_chapter(chapter, reviewer)

    from_status = chapter.audit_status
    chapter.audit_status = Chapter.AuditStatus.APPROVED
    chapter.status = Chapter.Status.PUBLISHED
    if chapter.reviewer_id is None and reviewer is not None:
        chapter.reviewer = reviewer
    chapter.reviewed_at = timezone.now()
    if chapter.published_at is None:
        chapter.published_at = timezone.now()
    chapter.save(update_fields=["audit_status", "reviewer", "reviewed_at", "status", "published_at", "updated_at"])
    recalculate_novel_chapter_stats(chapter.novel_id)
    _create_chapter_audit_log(
        chapter=chapter,
        action=AuditLog.Action.APPROVE,
        from_status=from_status,
        to_status=Chapter.AuditStatus.APPROVED,
        reviewer=reviewer,
    )
    return chapter


@transaction.atomic
def reject_chapter_review(chapter, reviewer=None, reason="", require_reason=False):
    if require_reason and not (reason or "").strip():
        raise ValidationError({"reason": ["Reject reason is required."]})
    if chapter.audit_status not in REVIEWABLE_AUDIT_STATUSES:
        raise ValidationError({"audit_status": ["Only pending or reviewing chapters can be rejected."]})
    _ensure_can_review_chapter(chapter, reviewer)

    from_status = chapter.audit_status
    chapter.audit_status = Chapter.AuditStatus.REJECTED
    chapter.status = Chapter.Status.DRAFT
    if chapter.reviewer_id is None and reviewer is not None:
        chapter.reviewer = reviewer
    chapter.reviewed_at = timezone.now()
    chapter.save(update_fields=["audit_status", "reviewer", "reviewed_at", "status", "updated_at"])
    recalculate_novel_chapter_stats(chapter.novel_id)
    _create_chapter_audit_log(
        chapter=chapter,
        action=AuditLog.Action.REJECT,
        from_status=from_status,
        to_status=Chapter.AuditStatus.REJECTED,
        reviewer=reviewer,
        reason=reason,
    )
    return chapter
