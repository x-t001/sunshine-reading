from django.contrib.auth.models import AbstractUser
from django.db import models

from common.models import TimeStampedModel


class User(AbstractUser, TimeStampedModel):
    class Role(models.TextChoices):
        READER = "reader", "Reader"
        AUTHOR = "author", "Author"
        ADMIN = "admin", "Admin"

    nickname = models.CharField(max_length=64, blank=True)
    avatar = models.URLField(max_length=500, blank=True)
    bio = models.TextField(blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.READER,
        db_index=True,
    )
    phone = models.CharField(max_length=32, blank=True, db_index=True)
    is_banned = models.BooleanField(default=False, db_index=True)

    class Meta:
        indexes = [
            models.Index(fields=["role", "is_banned"]),
            models.Index(fields=["nickname"]),
        ]

    def __str__(self):
        return self.nickname or self.username
