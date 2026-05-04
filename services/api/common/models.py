from django.conf import settings
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AuditLog(models.Model):
    class ContentType(models.TextChoices):
        NOVEL = "novel", "小说"
        CHAPTER = "chapter", "章节"

    class Action(models.TextChoices):
        SUBMIT = "submit", "提交审核"
        CLAIM = "claim", "领取审核"
        APPROVE = "approve", "审核通过"
        REJECT = "reject", "审核驳回"

    content_type = models.CharField("审核对象类型", max_length=20, choices=ContentType.choices, db_index=True)
    object_id = models.PositiveBigIntegerField("审核对象 ID", db_index=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="审核员",
        null=True,
        blank=True,
        related_name="audit_logs",
        on_delete=models.SET_NULL,
    )
    action = models.CharField("操作类型", max_length=20, choices=Action.choices, db_index=True)
    from_status = models.CharField("原审核状态", max_length=20, blank=True)
    to_status = models.CharField("新审核状态", max_length=20, blank=True)
    reason = models.TextField("审核意见", blank=True)
    created_at = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "审核记录"
        verbose_name_plural = "审核记录管理"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["content_type", "object_id", "created_at"]),
            models.Index(fields=["reviewer", "action", "created_at"]),
            models.Index(fields=["action", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_content_type_display()} #{self.object_id} {self.get_action_display()}"
