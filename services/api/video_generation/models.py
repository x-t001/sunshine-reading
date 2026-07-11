from django.conf import settings
from django.db import models
from django.utils import timezone

from common.models import TimeStampedModel


class VideoProject(TimeStampedModel):
    class SourceType(models.TextChoices):
        TEXT = "text", "Text"
        CHAPTER = "chapter", "Chapter"
        NOVEL = "novel", "Novel"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        ANALYZING = "analyzing", "Analyzing"
        STORYBOARD_READY = "storyboard_ready", "Storyboard ready"
        ASSET_GENERATING = "asset_generating", "Asset generating"
        RENDERING = "rendering", "Rendering"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Owner",
        related_name="video_projects",
        on_delete=models.CASCADE,
    )
    source_type = models.CharField(
        "Source type",
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.TEXT,
        db_index=True,
    )
    source_novel = models.ForeignKey(
        "novels.Novel",
        verbose_name="Source novel",
        null=True,
        blank=True,
        related_name="video_projects",
        on_delete=models.SET_NULL,
    )
    source_chapter = models.ForeignKey(
        "chapters.Chapter",
        verbose_name="Source chapter",
        null=True,
        blank=True,
        related_name="video_projects",
        on_delete=models.SET_NULL,
    )
    source_title = models.CharField("Source title", max_length=255, blank=True)
    source_excerpt_hash = models.CharField("Source excerpt hash", max_length=64, blank=True, db_index=True)
    input_text = models.TextField("Input text", blank=True)
    title = models.CharField("Project title", max_length=255, db_index=True)
    summary = models.TextField("Summary", blank=True)
    style_preset = models.CharField("Style preset", max_length=64, default="cinematic_story")
    duration_target = models.PositiveSmallIntegerField("Duration target seconds", default=60)
    aspect_ratio = models.CharField("Aspect ratio", max_length=20, default="9:16")
    status = models.CharField("Status", max_length=30, choices=Status.choices, default=Status.DRAFT, db_index=True)
    failure_reason = models.TextField("Failure reason", blank=True)
    deleted_at = models.DateTimeField("Deleted at", null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = "Video project"
        verbose_name_plural = "Video projects"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(duration_target__gte=30) & models.Q(duration_target__lte=90),
                name="video_project_duration_target_range",
            ),
        ]
        indexes = [
            models.Index(fields=["owner", "status"]),
            models.Index(fields=["owner", "created_at"]),
            models.Index(fields=["source_type", "created_at"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["deleted_at", "created_at"]),
        ]

    def __str__(self):
        return self.title

    @property
    def is_deleted(self):
        return self.deleted_at is not None

    def mark_deleted(self):
        self.status = self.Status.CANCELED
        self.deleted_at = timezone.now()


class VideoScene(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    project = models.ForeignKey(
        VideoProject,
        verbose_name="Video project",
        related_name="scenes",
        on_delete=models.CASCADE,
    )
    scene_no = models.PositiveSmallIntegerField("Scene number")
    title = models.CharField("Scene title", max_length=255, blank=True)
    visual_prompt = models.TextField("Visual prompt", blank=True)
    narration_text = models.TextField("Narration text", blank=True)
    subtitle_text = models.TextField("Subtitle text", blank=True)
    duration_seconds = models.PositiveSmallIntegerField("Duration seconds", default=8)
    camera_direction = models.CharField("Camera direction", max_length=200, blank=True)
    mood = models.CharField("Mood", max_length=100, blank=True)
    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    failure_reason = models.TextField("Failure reason", blank=True)

    class Meta:
        verbose_name = "Video scene"
        verbose_name_plural = "Video scenes"
        ordering = ["project_id", "scene_no"]
        constraints = [
            models.UniqueConstraint(fields=["project", "scene_no"], name="unique_video_scene_no_per_project"),
            models.CheckConstraint(condition=models.Q(duration_seconds__gt=0), name="video_scene_duration_positive"),
        ]
        indexes = [
            models.Index(fields=["project", "scene_no"]),
            models.Index(fields=["project", "status"]),
        ]

    def __str__(self):
        return f"{self.project_id} #{self.scene_no} {self.title}".strip()
