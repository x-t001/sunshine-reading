from django.contrib.auth.models import AbstractUser
from django.db import models

from common.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    class Role(models.TextChoices):
        READER = "reader", "读者"
        AUTHOR = "author", "作者"
        REVIEWER = "reviewer", "审核员"
        ADMIN = "admin", "管理员"

    nickname = models.CharField("昵称", max_length=64, blank=True)
    avatar = models.URLField("头像", max_length=500, blank=True)
    bio = models.TextField("个人简介", blank=True)
    role = models.CharField(
        "用户角色",
        max_length=20,
        choices=Role.choices,
        default=Role.READER,
        db_index=True,
    )
    phone = models.CharField("手机号", max_length=32, blank=True, db_index=True)
    is_banned = models.BooleanField("是否封禁", default=False, db_index=True)

    class Meta:
        verbose_name = "用户"
        verbose_name_plural = "用户管理"
        indexes = [
            models.Index(fields=["role", "is_banned"]),
            models.Index(fields=["nickname"]),
        ]

    def __str__(self):
        return self.nickname or self.username
