from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from common.models import AuditLog
from common.services import create_operation_audit_log

from .models import User


@transaction.atomic
def update_user_role(actor, target_user, role):
    if target_user.is_superuser and not actor.is_superuser:
        raise PermissionDenied("不能修改超级管理员的角色。")

    if actor.id == target_user.id and role != User.Role.ADMIN:
        raise ValidationError({"role": ["不能把自己的角色降级为非管理员。"]})

    old_role = target_user.role
    if old_role != role:
        target_user.role = role
        target_user.save(update_fields=["role", "updated_at"])
        create_operation_audit_log(
            content_type=AuditLog.ContentType.USER,
            object_id=target_user.id,
            actor=actor,
            action=AuditLog.Action.ROLE_UPDATE,
            from_status=old_role,
            to_status=role,
        )
    return target_user


@transaction.atomic
def ban_user(actor, target_user, reason=""):
    if target_user.is_superuser:
        raise PermissionDenied("不能封禁超级管理员。")

    if actor.id == target_user.id:
        raise ValidationError({"user": ["不能封禁自己。"]})

    if not target_user.is_banned:
        target_user.is_banned = True
        target_user.save(update_fields=["is_banned", "updated_at"])
        create_operation_audit_log(
            content_type=AuditLog.ContentType.USER,
            object_id=target_user.id,
            actor=actor,
            action=AuditLog.Action.BAN,
            from_status="active",
            to_status="banned",
            reason=reason,
        )
    return target_user


@transaction.atomic
def unban_user(actor, target_user):
    if target_user.is_banned:
        target_user.is_banned = False
        target_user.save(update_fields=["is_banned", "updated_at"])
        create_operation_audit_log(
            content_type=AuditLog.ContentType.USER,
            object_id=target_user.id,
            actor=actor,
            action=AuditLog.Action.UNBAN,
            from_status="banned",
            to_status="active",
        )
    return target_user
