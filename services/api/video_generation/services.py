import hashlib

from django.db import transaction
from rest_framework.exceptions import ValidationError

from common.models import AuditLog
from common.services import create_operation_audit_log

from .models import VideoProject


def _derive_title(title, input_text):
    normalized_title = (title or "").strip()
    if normalized_title:
        return normalized_title

    normalized_text = " ".join((input_text or "").split())
    if not normalized_text:
        return "Untitled video project"
    return normalized_text[:60]


def _hash_source_text(input_text):
    return hashlib.sha256((input_text or "").encode("utf-8")).hexdigest()


@transaction.atomic
def create_text_video_project(owner, data):
    if data["source_type"] != VideoProject.SourceType.TEXT:
        raise ValidationError({"source_type": ["Only pasted text projects are supported in this iteration."]})

    title = _derive_title(data.get("title"), data["input_text"])
    project = VideoProject.objects.create(
        owner=owner,
        source_type=VideoProject.SourceType.TEXT,
        source_title=title,
        source_excerpt_hash=_hash_source_text(data["input_text"]),
        input_text=data["input_text"],
        title=title,
        style_preset=data.get("style_preset", "cinematic_story"),
        duration_target=data.get("duration_target", 60),
        aspect_ratio=data.get("aspect_ratio", "9:16"),
        status=VideoProject.Status.DRAFT,
    )
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=project.id,
        actor=owner,
        action=AuditLog.Action.CREATE,
        to_status=project.status,
        reason={
            "source_type": project.source_type,
            "title": project.title,
        },
    )
    return project


@transaction.atomic
def soft_delete_video_project(project, actor=None):
    if project.deleted_at is not None:
        return project

    from_status = project.status
    project.mark_deleted()
    project.save(update_fields=["status", "deleted_at", "updated_at"])
    create_operation_audit_log(
        content_type=AuditLog.ContentType.VIDEO_PROJECT,
        object_id=project.id,
        actor=actor,
        action=AuditLog.Action.DELETE,
        from_status=from_status,
        to_status=project.status,
    )
    return project
