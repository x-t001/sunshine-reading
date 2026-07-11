from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from common.models import AuditLog
from common.services import create_operation_audit_log
from novels.models import Novel

from .models import Comment
from .selectors import (
    get_chapter_for_novel,
    get_comment_for_update,
    get_parent_comment,
    get_public_novel,
)


@transaction.atomic
def create_comment(user, novel_id, content, parent_id=None, chapter_id=None):
    novel = get_public_novel(novel_id)
    if novel is None:
        raise ValidationError({"novel_id": ["Novel not found or unavailable."]})

    parent = None
    if parent_id:
        parent = get_parent_comment(parent_id)
        if parent is None or parent.novel_id != novel.id:
            raise ValidationError({"parent_id": ["Parent comment does not belong to this novel."]})

    chapter = None
    if chapter_id:
        chapter = get_chapter_for_novel(novel.id, chapter_id)
        if chapter is None:
            raise ValidationError({"chapter_id": ["Chapter does not belong to this novel."]})

    comment = Comment.objects.create(
        user=user,
        novel=novel,
        chapter=chapter,
        parent=parent,
        content=content,
        status=Comment.Status.NORMAL,
    )
    Novel.objects.filter(id=novel.id).update(comment_count=F("comment_count") + 1)
    return (
        Comment.objects.select_related("user", "novel", "chapter", "parent")
        .filter(id=comment.id)
        .first()
    )


@transaction.atomic
def delete_comment(user, comment_id):
    comment = get_comment_for_update(comment_id)
    if comment is None:
        raise NotFound("Comment not found.")

    is_admin = bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False) or getattr(user, "role", "") == "admin")
    if comment.user_id != user.id and not is_admin:
        raise PermissionDenied("You can only delete your own comment.")

    if comment.status == Comment.Status.DELETED:
        return

    comment.status = Comment.Status.DELETED
    comment.save(update_fields=["status", "updated_at"])

    Novel.objects.filter(id=comment.novel_id, comment_count__gt=0).update(
        comment_count=F("comment_count") - 1,
    )


@transaction.atomic
def update_admin_comment_status(comment, status, actor=None):
    old_status = comment.status
    if old_status == status:
        return comment

    comment.status = status
    comment.save(update_fields=["status", "updated_at"])

    if old_status == Comment.Status.NORMAL and status != Comment.Status.NORMAL:
        Novel.objects.filter(id=comment.novel_id, comment_count__gt=0).update(
            comment_count=F("comment_count") - 1,
        )
    elif old_status != Comment.Status.NORMAL and status == Comment.Status.NORMAL:
        Novel.objects.filter(id=comment.novel_id).update(comment_count=F("comment_count") + 1)

    create_operation_audit_log(
        content_type=AuditLog.ContentType.COMMENT,
        object_id=comment.id,
        actor=actor,
        action=AuditLog.Action.STATUS_UPDATE,
        from_status=old_status,
        to_status=status,
    )
    return comment
