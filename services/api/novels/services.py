from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Avg, Count
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from common.models import AuditLog
from common.services import create_operation_audit_log
from users.permissions import is_admin_user

from .models import Category, Novel, NovelRating
from .selectors import get_public_novel_by_id, get_rating_for_user


REVIEWABLE_AUDIT_STATUSES = (Novel.AuditStatus.PENDING, Novel.AuditStatus.REVIEWING)


def _create_novel_audit_log(novel, action, from_status, to_status, reviewer=None, reason=""):
    AuditLog.objects.create(
        content_type=AuditLog.ContentType.NOVEL,
        object_id=novel.id,
        reviewer=reviewer,
        action=action,
        from_status=from_status or "",
        to_status=to_status or "",
        reason=reason or "",
    )


def _ensure_can_review_novel(novel, reviewer):
    if (
        reviewer
        and novel.audit_status == Novel.AuditStatus.REVIEWING
        and novel.reviewer_id
        and novel.reviewer_id != reviewer.id
        and not is_admin_user(reviewer)
    ):
        raise PermissionDenied("You can only review novels you claimed.")


def build_rating_summary(novel, user=None):
    return {
        "novel_id": novel.id,
        "rating_score": novel.rating_score,
        "rating_count": novel.rating_count,
        "my_rating": get_rating_for_user(novel.id, user),
    }


def _is_descendant(category, possible_ancestor):
    current = category
    while current is not None:
        if current.id == possible_ancestor.id:
            return True
        current = current.parent
    return False


def _validate_category_parent(category, parent):
    if parent is None:
        return
    if category is not None and parent.id == category.id:
        raise ValidationError({"parent_id": ["Category cannot use itself as parent."]})
    if category is not None and _is_descendant(parent, category):
        raise ValidationError({"parent_id": ["Category cannot use its descendant as parent."]})


def _collect_changed_fields(instance, data, fields):
    changes = {}
    for field in fields:
        if field not in data:
            continue
        old_value = getattr(instance, field)
        new_value = data[field]
        if old_value != new_value:
            changes[field] = {"from": str(old_value), "to": str(new_value)}
    return changes


@transaction.atomic
def create_admin_category(data, actor=None):
    parent = data.get("parent")
    _validate_category_parent(None, parent)
    category = Category.objects.create(
        name=data["name"],
        slug=data["slug"],
        parent=parent,
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", True),
    )
    create_operation_audit_log(
        content_type=AuditLog.ContentType.CATEGORY,
        object_id=category.id,
        actor=actor,
        action=AuditLog.Action.CREATE,
        to_status="active" if category.is_active else "inactive",
        reason={"name": category.name, "slug": category.slug},
    )
    return category


@transaction.atomic
def update_admin_category(category, data, actor=None):
    if "parent" in data:
        _validate_category_parent(category, data.get("parent"))

    changes = _collect_changed_fields(category, data, ("name", "slug", "parent", "sort_order", "is_active"))
    update_fields = []
    for field in ("name", "slug", "parent", "sort_order", "is_active"):
        if field not in data:
            continue
        setattr(category, field, data[field])
        update_fields.append(field)

    if update_fields:
        update_fields.append("updated_at")
        category.save(update_fields=update_fields)
        if changes:
            create_operation_audit_log(
                content_type=AuditLog.ContentType.CATEGORY,
                object_id=category.id,
                actor=actor,
                action=AuditLog.Action.UPDATE,
                from_status="",
                to_status="",
                reason={"changes": changes},
            )
    return category


@transaction.atomic
def update_admin_category_status(category, is_active, actor=None):
    old_status = "active" if category.is_active else "inactive"
    new_status = "active" if is_active else "inactive"
    if category.is_active != is_active:
        category.is_active = is_active
        category.save(update_fields=["is_active", "updated_at"])
        create_operation_audit_log(
            content_type=AuditLog.ContentType.CATEGORY,
            object_id=category.id,
            actor=actor,
            action=AuditLog.Action.STATUS_UPDATE,
            from_status=old_status,
            to_status=new_status,
        )
    return category


@transaction.atomic
def submit_or_update_rating(user, novel_id, score, comment=""):
    novel = get_public_novel_by_id(novel_id)
    if novel is None:
        raise ValidationError({"novel_id": ["Novel not found or unavailable."]})

    NovelRating.objects.update_or_create(
        user=user,
        novel=novel,
        defaults={
            "score": score,
            "comment": comment or "",
        },
    )
    novel = recalculate_novel_rating(novel.id)
    return build_rating_summary(novel, user)


@transaction.atomic
def delete_rating(user, novel_id):
    novel = get_public_novel_by_id(novel_id)
    if novel is None:
        raise ValidationError({"novel_id": ["Novel not found or unavailable."]})

    deleted_count, _ = NovelRating.objects.filter(user=user, novel=novel).delete()
    if deleted_count == 0:
        raise NotFound("Rating not found.")

    novel = recalculate_novel_rating(novel.id)
    return build_rating_summary(novel, user)


def recalculate_novel_rating(novel_id):
    stats = NovelRating.objects.filter(novel_id=novel_id).aggregate(
        score_avg=Avg("score"),
        score_count=Count("id"),
    )
    count = stats["score_count"] or 0
    if count == 0:
        score = Decimal("0.00")
    else:
        score = Decimal(str(stats["score_avg"])).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    Novel.objects.filter(id=novel_id).update(
        rating_score=score,
        rating_count=count,
    )
    return Novel.objects.get(id=novel_id)


@transaction.atomic
def create_author_novel(user, data):
    return Novel.objects.create(
        author=user,
        title=data["title"],
        category=data["category"],
        cover=data.get("cover", ""),
        description=data.get("description", ""),
        status=data.get("status", Novel.Status.SERIALIZING),
        audit_status=Novel.AuditStatus.DRAFT,
    )


@transaction.atomic
def update_author_novel(novel, data):
    review_sensitive_fields = {"title", "category", "cover", "description"}
    changed_review_sensitive_field = False

    for field in ("title", "category", "cover", "description", "status"):
        if field not in data:
            continue

        new_value = data[field]
        if getattr(novel, field) != new_value and field in review_sensitive_fields:
            changed_review_sensitive_field = True
        setattr(novel, field, new_value)

    if novel.audit_status == Novel.AuditStatus.APPROVED and changed_review_sensitive_field:
        novel.audit_status = Novel.AuditStatus.PENDING

    novel.save(update_fields=["title", "category", "cover", "description", "status", "audit_status", "updated_at"])
    return novel


@transaction.atomic
def update_admin_novel_status(novel, status, actor=None):
    old_status = novel.status
    if old_status != status:
        novel.status = status
        novel.save(update_fields=["status", "updated_at"])
        create_operation_audit_log(
            content_type=AuditLog.ContentType.NOVEL,
            object_id=novel.id,
            actor=actor,
            action=AuditLog.Action.STATUS_UPDATE,
            from_status=old_status,
            to_status=status,
        )
    return novel


@transaction.atomic
def update_admin_novel_featured(novel, is_featured, actor=None):
    old_status = "featured" if novel.is_featured else "normal"
    new_status = "featured" if is_featured else "normal"
    if novel.is_featured != is_featured:
        novel.is_featured = is_featured
        novel.save(update_fields=["is_featured", "updated_at"])
        create_operation_audit_log(
            content_type=AuditLog.ContentType.NOVEL,
            object_id=novel.id,
            actor=actor,
            action=AuditLog.Action.FEATURE_UPDATE,
            from_status=old_status,
            to_status=new_status,
        )
    return novel


@transaction.atomic
def submit_novel_review(novel):
    missing_fields = []
    if not novel.title:
        missing_fields.append("title")
    if not novel.description:
        missing_fields.append("description")
    if not novel.category_id:
        missing_fields.append("category_id")
    if missing_fields:
        raise ValidationError({"fields": [f"Missing required fields: {', '.join(missing_fields)}."]})

    if novel.audit_status not in (Novel.AuditStatus.DRAFT, Novel.AuditStatus.REJECTED):
        if novel.audit_status == Novel.AuditStatus.PENDING:
            raise ValidationError({"audit_status": ["Novel is already pending review."]})
        if novel.audit_status == Novel.AuditStatus.REVIEWING:
            raise ValidationError({"audit_status": ["Novel is already under review."]})
        if novel.audit_status == Novel.AuditStatus.APPROVED:
            raise ValidationError({"audit_status": ["Novel is already approved."]})
        raise ValidationError({"audit_status": ["Novel cannot be submitted from current audit status."]})

    from_status = novel.audit_status
    novel.audit_status = Novel.AuditStatus.PENDING
    novel.reviewer = None
    novel.reviewed_at = None
    novel.save(update_fields=["audit_status", "reviewer", "reviewed_at", "updated_at"])
    _create_novel_audit_log(
        novel=novel,
        action=AuditLog.Action.SUBMIT,
        from_status=from_status,
        to_status=Novel.AuditStatus.PENDING,
    )
    return novel


@transaction.atomic
def claim_novel_review(novel, reviewer):
    if novel.audit_status != Novel.AuditStatus.PENDING:
        raise ValidationError({"audit_status": ["Only pending novels can be claimed."]})

    from_status = novel.audit_status
    novel.audit_status = Novel.AuditStatus.REVIEWING
    novel.reviewer = reviewer
    novel.reviewed_at = None
    novel.save(update_fields=["audit_status", "reviewer", "reviewed_at", "updated_at"])
    _create_novel_audit_log(
        novel=novel,
        action=AuditLog.Action.CLAIM,
        from_status=from_status,
        to_status=Novel.AuditStatus.REVIEWING,
        reviewer=reviewer,
    )
    return novel


@transaction.atomic
def approve_novel_review(novel, reviewer=None):
    if novel.status == Novel.Status.REMOVED:
        raise ValidationError({"status": ["Removed novels cannot be approved."]})
    if novel.audit_status not in REVIEWABLE_AUDIT_STATUSES:
        raise ValidationError({"audit_status": ["Only pending or reviewing novels can be approved."]})
    _ensure_can_review_novel(novel, reviewer)

    from_status = novel.audit_status
    novel.audit_status = Novel.AuditStatus.APPROVED
    if novel.reviewer_id is None and reviewer is not None:
        novel.reviewer = reviewer
    novel.reviewed_at = timezone.now()
    novel.save(update_fields=["audit_status", "reviewer", "reviewed_at", "updated_at"])
    _create_novel_audit_log(
        novel=novel,
        action=AuditLog.Action.APPROVE,
        from_status=from_status,
        to_status=Novel.AuditStatus.APPROVED,
        reviewer=reviewer,
    )
    return novel


@transaction.atomic
def reject_novel_review(novel, reviewer=None, reason="", require_reason=False):
    if require_reason and not (reason or "").strip():
        raise ValidationError({"reason": ["Reject reason is required."]})
    if novel.audit_status not in REVIEWABLE_AUDIT_STATUSES:
        raise ValidationError({"audit_status": ["Only pending or reviewing novels can be rejected."]})
    _ensure_can_review_novel(novel, reviewer)

    from_status = novel.audit_status
    novel.audit_status = Novel.AuditStatus.REJECTED
    if novel.reviewer_id is None and reviewer is not None:
        novel.reviewer = reviewer
    novel.reviewed_at = timezone.now()
    novel.save(update_fields=["audit_status", "reviewer", "reviewed_at", "updated_at"])
    _create_novel_audit_log(
        novel=novel,
        action=AuditLog.Action.REJECT,
        from_status=from_status,
        to_status=Novel.AuditStatus.REJECTED,
        reviewer=reviewer,
        reason=reason,
    )
    return novel
