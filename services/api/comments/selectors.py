from django.db import models
from django.db.models import Prefetch

from chapters.models import Chapter
from novels.models import Novel

from .models import Comment


def get_public_novel(novel_id):
    return (
        Novel.objects.filter(id=novel_id, audit_status=Novel.AuditStatus.APPROVED)
        .exclude(status=Novel.Status.REMOVED)
        .first()
    )


def get_chapter_for_novel(novel_id, chapter_id):
    return Chapter.objects.filter(id=chapter_id, novel_id=novel_id).first()


def get_normal_comment(comment_id):
    return (
        Comment.objects.select_related("user", "novel", "chapter", "parent")
        .prefetch_related(_normal_replies_prefetch())
        .filter(id=comment_id, status=Comment.Status.NORMAL)
        .first()
    )


def get_comment_for_update(comment_id):
    return Comment.objects.select_related("user", "novel").filter(id=comment_id).first()


def get_parent_comment(parent_id):
    return (
        Comment.objects.select_related("user", "novel", "chapter", "parent")
        .filter(id=parent_id, status=Comment.Status.NORMAL)
        .first()
    )


def get_novel_comments(novel_id):
    return (
        Comment.objects.filter(
            novel_id=novel_id,
            parent__isnull=True,
            status=Comment.Status.NORMAL,
        )
        .select_related("user", "novel", "chapter")
        .prefetch_related(_normal_replies_prefetch())
        .order_by("-created_at")
    )


def get_chapter_comments(chapter_id):
    return (
        Comment.objects.filter(
            chapter_id=chapter_id,
            status=Comment.Status.NORMAL,
        )
        .select_related("user", "novel", "chapter", "parent")
        .prefetch_related(_normal_replies_prefetch())
        .order_by("-created_at")
    )


def get_admin_comments(params):
    queryset = Comment.objects.select_related("user", "novel", "chapter", "parent")

    keyword = params.get("keyword")
    if keyword:
        queryset = queryset.filter(
            models.Q(content__icontains=keyword)
            | models.Q(user__username__icontains=keyword)
            | models.Q(user__nickname__icontains=keyword)
            | models.Q(novel__title__icontains=keyword)
            | models.Q(chapter__title__icontains=keyword)
        )

    user_id = params.get("user_id")
    if user_id:
        queryset = queryset.filter(user_id=user_id)

    novel_id = params.get("novel_id")
    if novel_id:
        queryset = queryset.filter(novel_id=novel_id)

    chapter_id = params.get("chapter_id")
    if chapter_id:
        queryset = queryset.filter(chapter_id=chapter_id)

    status = params.get("status")
    if status:
        queryset = queryset.filter(status=status)

    return queryset.order_by("-created_at", "-id")


def get_admin_comment_by_id(comment_id):
    return (
        Comment.objects.select_related("user", "novel", "chapter", "parent")
        .filter(id=comment_id)
        .first()
    )


def _normal_replies_prefetch():
    return Prefetch(
        "replies",
        queryset=(
            Comment.objects.filter(status=Comment.Status.NORMAL)
            .select_related("user", "novel", "chapter", "parent")
            .order_by("created_at")
        ),
        to_attr="normal_replies",
    )
