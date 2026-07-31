from django.conf import settings
from django.core.exceptions import ValidationError
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
    agent_workflow = models.JSONField("Agent workflow", default=dict, blank=True)
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
    agent_metadata = models.JSONField("Agent metadata", default=dict, blank=True)
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


class VideoAsset(TimeStampedModel):
    class AssetType(models.TextChoices):
        IMAGE = "image", "Image"
        VIDEO = "video", "Video"
        AUDIO = "audio", "Audio"
        SUBTITLE = "subtitle", "Subtitle"
        FINAL_VIDEO = "final_video", "Final video"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        READY = "ready", "Ready"
        STALE = "stale", "Stale"
        FAILED = "failed", "Failed"

    project = models.ForeignKey(
        VideoProject,
        verbose_name="Video project",
        related_name="assets",
        on_delete=models.CASCADE,
    )
    scene = models.ForeignKey(
        VideoScene,
        verbose_name="Video scene",
        related_name="assets",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    asset_type = models.CharField("Asset type", max_length=20, choices=AssetType.choices, db_index=True)
    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True)
    storage_path = models.CharField("Storage path", max_length=500, blank=True)
    file_name = models.CharField("File name", max_length=255, blank=True)
    mime_type = models.CharField("MIME type", max_length=100, blank=True)
    file_size = models.PositiveBigIntegerField("File size", default=0)
    provider = models.CharField("Provider", max_length=50, blank=True)
    provider_asset_id = models.CharField("Provider asset ID", max_length=255, blank=True)
    metadata = models.JSONField("Metadata", default=dict, blank=True)
    failure_reason = models.TextField("Failure reason", blank=True)

    class Meta:
        verbose_name = "Video asset"
        verbose_name_plural = "Video assets"
        ordering = ["project_id", "asset_type", "scene_id", "id"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(asset_type__in=("subtitle", "final_video"), scene__isnull=True)
                    | models.Q(asset_type__in=("image", "video", "audio"), scene__isnull=False)
                ),
                name="video_asset_scope_matches_type",
            ),
            models.UniqueConstraint(
                fields=["project", "scene", "asset_type"],
                condition=models.Q(scene__isnull=False),
                name="unique_video_scene_asset_type",
            ),
            models.UniqueConstraint(
                fields=["project", "asset_type"],
                condition=models.Q(scene__isnull=True),
                name="unique_video_project_asset_type",
            ),
        ]
        indexes = [
            models.Index(fields=["project", "asset_type", "status"]),
            models.Index(fields=["scene", "asset_type"]),
        ]

    def __str__(self):
        scope = f"scene {self.scene_id}" if self.scene_id else "project"
        return f"{self.project_id} {scope} {self.asset_type} ({self.status})"

    def clean(self):
        super().clean()
        if self.scene_id and self.project_id and self.scene.project_id != self.project_id:
            raise ValidationError({"scene": "Video asset scene must belong to the same project."})


class VideoGenerationJob(TimeStampedModel):
    RESUMABLE_PROVIDER_ERROR_MARKERS = (
        "等待超时",
        "异步结果查询已达到等待上限",
        "结果查询服务连接超时",
        "无法连接短视频画面结果查询服务",
        "短视频画面文件下载超时",
        "无法连接短视频画面文件下载服务",
        "短视频画面文件下载失败，HTTP 5",
    )

    class JobType(models.TextChoices):
        AI_STORYBOARD = "ai_storyboard", "AI storyboard"
        IMAGE_ASSETS = "image_assets", "Image assets"
        VIDEO_CLIPS = "video_clips", "Video clips"
        NARRATION_AUDIO = "narration_audio", "Narration audio"
        RENDER = "render", "Render"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        CANCELED = "canceled", "Canceled"

    project = models.ForeignKey(
        VideoProject,
        verbose_name="Video project",
        related_name="generation_jobs",
        on_delete=models.CASCADE,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Requested by",
        related_name="video_generation_jobs",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    job_type = models.CharField("Job type", max_length=30, choices=JobType.choices, default=JobType.AI_STORYBOARD, db_index=True)
    status = models.CharField("Status", max_length=20, choices=Status.choices, default=Status.QUEUED, db_index=True)
    provider = models.CharField("Provider", max_length=50, default="openai_compatible")
    model_name = models.CharField("Model name", max_length=120, blank=True)
    request_payload = models.JSONField("Request payload", default=dict, blank=True)
    attempt_count = models.PositiveSmallIntegerField("Attempt count", default=0)
    max_attempts = models.PositiveSmallIntegerField("Max attempts", default=3)
    error_message = models.TextField("Error message", blank=True)
    started_at = models.DateTimeField("Started at", null=True, blank=True)
    finished_at = models.DateTimeField("Finished at", null=True, blank=True)

    @property
    def can_resume_provider_task(self):
        payload = self.request_payload if isinstance(self.request_payload, dict) else {}
        return (
            self.job_type == self.JobType.VIDEO_CLIPS
            and self.status == self.Status.FAILED
            and payload.get("provider_resume_available") is True
            and any(marker in (self.error_message or "") for marker in self.RESUMABLE_PROVIDER_ERROR_MARKERS)
        )

    class Meta:
        verbose_name = "Video generation job"
        verbose_name_plural = "Video generation jobs"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(max_attempts__gte=1) & models.Q(max_attempts__lte=5),
                name="video_job_max_attempts_range",
            ),
            models.CheckConstraint(
                condition=models.Q(attempt_count__lte=models.F("max_attempts")),
                name="video_job_attempt_within_limit",
            ),
            models.UniqueConstraint(
                fields=["project", "job_type"],
                condition=models.Q(status__in=("queued", "running")),
                name="unique_active_video_job_per_project_type",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["project", "status"]),
            models.Index(fields=["job_type", "status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_job_type_display()} #{self.id} ({self.status})"
