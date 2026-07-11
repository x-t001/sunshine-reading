from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from common.models import AuditLog
from common.services import create_operation_audit_log

from .models import RankingItem, RankingType


def _validate_ranking_item_uniqueness(item, ranking_type, novel, rank, calculated_at):
    novel_queryset = RankingItem.objects.filter(
        ranking_type=ranking_type,
        novel=novel,
        calculated_at=calculated_at,
    )
    rank_queryset = RankingItem.objects.filter(
        ranking_type=ranking_type,
        rank=rank,
        calculated_at=calculated_at,
    )
    if item is not None:
        novel_queryset = novel_queryset.exclude(id=item.id)
        rank_queryset = rank_queryset.exclude(id=item.id)

    errors = {}
    if novel_queryset.exists():
        errors["novel_id"] = ["This novel already exists in the ranking snapshot."]
    if rank_queryset.exists():
        errors["rank"] = ["This rank already exists in the ranking snapshot."]
    if errors:
        raise ValidationError(errors)


@transaction.atomic
def create_admin_ranking_type(data, actor=None):
    ranking_type = RankingType.objects.create(
        name=data["name"],
        code=data["code"],
        description=data.get("description", ""),
        is_active=data.get("is_active", True),
    )
    create_operation_audit_log(
        content_type=AuditLog.ContentType.RANKING_TYPE,
        object_id=ranking_type.id,
        actor=actor,
        action=AuditLog.Action.CREATE,
        to_status="active" if ranking_type.is_active else "inactive",
        reason={"name": ranking_type.name, "code": ranking_type.code},
    )
    return ranking_type


@transaction.atomic
def update_admin_ranking_type(ranking_type, data, actor=None):
    changes = {}
    update_fields = []
    for field in ("name", "code", "description", "is_active"):
        if field not in data:
            continue
        old_value = getattr(ranking_type, field)
        if old_value != data[field]:
            changes[field] = {"from": str(old_value), "to": str(data[field])}
        setattr(ranking_type, field, data[field])
        update_fields.append(field)

    if update_fields:
        update_fields.append("updated_at")
        ranking_type.save(update_fields=update_fields)
        if changes:
            create_operation_audit_log(
                content_type=AuditLog.ContentType.RANKING_TYPE,
                object_id=ranking_type.id,
                actor=actor,
                action=AuditLog.Action.UPDATE,
                reason={"changes": changes},
            )
    return ranking_type


@transaction.atomic
def update_admin_ranking_type_status(ranking_type, is_active, actor=None):
    old_status = "active" if ranking_type.is_active else "inactive"
    new_status = "active" if is_active else "inactive"
    if ranking_type.is_active != is_active:
        ranking_type.is_active = is_active
        ranking_type.save(update_fields=["is_active", "updated_at"])
        create_operation_audit_log(
            content_type=AuditLog.ContentType.RANKING_TYPE,
            object_id=ranking_type.id,
            actor=actor,
            action=AuditLog.Action.STATUS_UPDATE,
            from_status=old_status,
            to_status=new_status,
        )
    return ranking_type


@transaction.atomic
def create_admin_ranking_item(data, actor=None):
    calculated_at = data.get("calculated_at") or timezone.now()
    ranking_type = data["ranking_type"]
    novel = data["novel"]
    rank = data["rank"]
    _validate_ranking_item_uniqueness(
        item=None,
        ranking_type=ranking_type,
        novel=novel,
        rank=rank,
        calculated_at=calculated_at,
    )
    item = RankingItem.objects.create(
        ranking_type=ranking_type,
        novel=novel,
        score=data["score"],
        rank=rank,
        calculated_at=calculated_at,
    )
    create_operation_audit_log(
        content_type=AuditLog.ContentType.RANKING_ITEM,
        object_id=item.id,
        actor=actor,
        action=AuditLog.Action.CREATE,
        reason={
            "ranking_type_id": ranking_type.id,
            "novel_id": novel.id,
            "rank": rank,
            "score": str(item.score),
        },
    )
    return item


@transaction.atomic
def update_admin_ranking_item(item, data, actor=None):
    ranking_type = data.get("ranking_type", item.ranking_type)
    novel = data.get("novel", item.novel)
    rank = data.get("rank", item.rank)
    calculated_at = data.get("calculated_at", item.calculated_at)
    _validate_ranking_item_uniqueness(
        item=item,
        ranking_type=ranking_type,
        novel=novel,
        rank=rank,
        calculated_at=calculated_at,
    )

    changes = {}
    update_fields = []
    for field in ("ranking_type", "novel", "score", "rank", "calculated_at"):
        if field not in data:
            continue
        old_value = getattr(item, field)
        if old_value != data[field]:
            changes[field] = {"from": str(old_value), "to": str(data[field])}
        setattr(item, field, data[field])
        update_fields.append(field)

    if update_fields:
        update_fields.append("updated_at")
        item.save(update_fields=update_fields)
        if changes:
            create_operation_audit_log(
                content_type=AuditLog.ContentType.RANKING_ITEM,
                object_id=item.id,
                actor=actor,
                action=AuditLog.Action.UPDATE,
                reason={"changes": changes},
            )
    return item
